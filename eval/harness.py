"""Run labelled cases and write the result directory. Offline DuckDB only."""

from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.agents.challenger import ChallengerAgent
from app.agents.evaluator import EvaluatorAgent
from app.agents.evidence import EvidenceAgent
from app.agents.planner import PlannerAgent
from app.agents.reporter import ReporterAgent
from app.config import Settings, get_settings
from app.llm.resolve import reset_cache
from app.orchestrator import Deps, RunOptions
from app.orchestrator import run as run_case
from app.schemas.decision import DecisionRecord
from app.store import Store
from app.tracing import Tracer
from eval.baseline import run_baseline
from eval.corpus import ROOT, cases_for, labels, split_document, truth_facts
from eval.metrics import OUTCOMES, score_rows
from eval.report import render_summary_md

_SYSTEMS = frozenset({"arbiter", "baseline", "arbiter_offline"})


def describe_run(paths: list[Path]) -> dict[str, Any]:
    """Model ids and the offline flag, read only from trace events."""
    models: list[str] = []
    offline = False
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            model = event.get("model")
            if isinstance(model, str) and model and model not in models:
                models.append(model)
            if event.get("provider") == "offline":
                offline = True
    return {"model_ids": models, "offline": offline}


def force_offline() -> Settings:
    """DuckDB mirror and the offline generator. No Nightshift and no Zetaris."""
    os.environ["SAMPLE_MODE"] = "true"
    os.environ["LLM_PROVIDER"] = "offline"
    os.environ["ARBITER_MEMORY"] = "off"
    get_settings.cache_clear()
    reset_cache()
    return Settings()


def run(
    systems: list[str],
    splits: list[str],
    *,
    consistency: tuple[int, int] | None = None,
    concurrency: int = 1,
    llm: str = "offline",
    sample_mode: bool | None = True,
    results_root: Path | None = None,
) -> Path:
    """Run each case with a fresh var directory. Always the offline DuckDB mirror."""
    del llm, sample_mode
    if concurrency > 2:
        concurrency = 2
    del concurrency  # DuckDB's shared connection is not safe to share across threads.
    unknown = [name for name in systems if name not in _SYSTEMS]
    if unknown:
        raise ValueError(f"unknown systems: {unknown}")
    settings = force_offline()
    root = results_root or _default_root()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    out = root / stamp
    out.mkdir(parents=True, exist_ok=True)
    (out / "traces").mkdir()
    catalogue = labels()
    truth = truth_facts()
    document = split_document()
    refs = cases_for(splits)
    jobs = _jobs(refs, consistency)
    grouped: dict[str, list[dict[str, Any]]] = {name: [] for name in systems}
    decisions: list[dict[str, Any]] = []
    for system in systems:
        for case_ref, repeat in jobs:
            row, record, trace = _one(
                system,
                case_ref,
                repeat,
                label=catalogue[case_ref],
                settings=settings,
                out=out,
            )
            grouped[system].append(row)
            if record is not None:
                decisions.append(
                    {
                        "case_ref": case_ref,
                        "system": system,
                        "tier": record.tier,
                        "expected_outcome": catalogue[case_ref]["expected_outcome"],
                        "policy_inputs": record.policy_inputs.model_dump(mode="json"),
                    }
                )
            if trace is not None:
                row["trace_path"] = str(trace)
    _write_cases(out / "cases.jsonl", [row for rows in grouped.values() for row in rows])
    _write_jsonl(out / "decisions.jsonl", decisions)
    summary = _summary(grouped, splits=splits, truth=truth, out=out, document=document)
    (out / "summary.json").write_text(_dump(summary), encoding="utf-8")
    (out / "summary.md").write_text(render_summary_md(summary), encoding="utf-8")
    for system, rows in grouped.items():
        _confusion(out / f"confusion_{system}.csv", rows)
    _env(out, splits=splits, document=document)
    return out


def _default_root() -> Path:
    override = os.environ.get("ARBITER_EVAL_ROOT")
    if override:
        return Path(override)
    return ROOT / "eval" / "results"


def _jobs(refs: list[str], consistency: tuple[int, int] | None) -> list[tuple[str, int]]:
    jobs = [(ref, 0) for ref in refs]
    if consistency is None:
        return jobs
    width, repeats = consistency
    extra = [(ref, repeat) for ref in refs[:width] for repeat in range(1, repeats)]
    return jobs + extra


def _one(
    system: str,
    case_ref: str,
    repeat: int,
    *,
    label: dict[str, Any],
    settings: Settings,
    out: Path,
) -> tuple[dict[str, Any], DecisionRecord | None, Path | None]:
    from eval.corpus import case_input

    case = case_input(case_ref)
    with tempfile.TemporaryDirectory(prefix="arbiter-eval-") as tmp:
        work = Path(tmp)
        tracer_box: dict[str, Tracer] = {}

        def factory(run_id: str, mode: dict[str, str]) -> Tracer:
            tracer_box["tracer"] = Tracer(run_id, mode=mode, log_dir=str(work / "logs"))
            return tracer_box["tracer"]

        if system == "baseline":
            tracer = Tracer(f"baseline-{case_ref}-{repeat}", mode=settings.mode(), log_dir=str(work / "logs"))
            started = datetime.now(UTC)
            result = run_baseline(case, settings=settings, tracer=tracer)
            tracer.close()
            elapsed = (datetime.now(UTC) - started).total_seconds()
            trace = _copy_trace(work / "logs", out)
            row = _base_row(case_ref, repeat, label, trace)
            row.update(
                predicted_outcome=result.outcome,
                reasons=result.reasons,
                predicted_failing_controls=result.failing_controls,
                cited_fields=result.cited_fields,
                evidence_fields=result.evidence_fields,
                queries=result.queries,
                latency_ms=int(elapsed * 1000),
            )
            if trace is not None:
                row.update(_from_trace(trace))
                row["queries"] = max(int(row["queries"]), result.queries)
            return row, None, trace

        counter = _CountingEvaluator()
        response = run_case(
            case,
            options=RunOptions(sample_mode=True, llm="offline"),
            deps=Deps(
                var_dir=work / "var",
                agents={
                    "planner": PlannerAgent(),
                    "evidence": EvidenceAgent(),
                    "evaluator": counter,
                    "challenger": ChallengerAgent(),
                    "reporter": ReporterAgent(),
                },
                tracer_factory=factory,
            ),
        )
        tracer = tracer_box.get("tracer")
        if tracer is not None:
            tracer.close()
        record = None
        if response.output is not None:
            store = Store(work / "var")
            try:
                record = store.get(response.output.case_id).decision
            finally:
                store._conn.close()
        trace = _copy_trace(work / "logs", out)
        row = _base_row(case_ref, repeat, label, trace)
        row["latency_ms"] = int(response.execution_time_seconds * 1000)
        row["claims_extracted"] = counter.extracted
        row["claims_grounded"] = counter.grounded
        if trace is not None:
            row.update(_from_trace(trace))
        if record is None:
            row["predicted_outcome"] = "ESCALATE"
            row["reasons"] = ["SYSTEM_NoDecision"]
            row["safe_escalate"] = True
            return row, None, trace
        row["predicted_outcome"] = record.outcome
        row["reasons"] = list(record.outcome_reasons) + list(record.escalation_reasons)
        row["safe_escalate"] = bool(record.escalation_reasons)
        row["predicted_failing_controls"] = [
            item.control_id for item in record.controls if item.state == "FALSE"
        ]
        row["predicted_contradiction_keys"] = [item.key for item in record.contradictions]
        row["guard_block"] = any(flag.level == "block" for flag in record.policy_inputs.guard_flags)
        row["facts"] = [
            {"key": item.key, "state": item.state, "value": item.value, "control_id": item.control_id}
            for item in record.facts
        ]
        return row, record, trace


class _CountingEvaluator:
    name = "EvaluatorAgent"
    role = EvaluatorAgent.role

    def __init__(self) -> None:
        self._inner = EvaluatorAgent()
        self.extracted = 0
        self.grounded = 0

    def __call__(self, state: Any, ctx: Any) -> Any:
        updated = self._inner(state, ctx)
        self.extracted = len(updated.claims)
        self.grounded = sum(1 for claim in updated.claims if claim.grounded is True)
        return updated


def _base_row(case_ref: str, repeat: int, label: dict[str, Any], trace: Path | None) -> dict[str, Any]:
    return {
        "case_ref": case_ref,
        "repeat": repeat,
        "expected_outcome": label.get("expected_outcome"),
        "predicted_outcome": "ESCALATE",
        "reasons": [],
        "expected_failing_controls": list(label.get("expected_failing_controls") or []),
        "predicted_failing_controls": [],
        "expected_contradiction_keys": list(label.get("expected_contradiction_keys") or []),
        "predicted_contradiction_keys": [],
        "injection": bool(label.get("injection")),
        "guard_block": False,
        "safe_escalate": False,
        "facts": [],
        "claims_extracted": 0,
        "claims_grounded": 0,
        "cited_fields": [],
        "evidence_fields": [],
        "tokens_in": 0,
        "tokens_out": 0,
        "model_calls": 0,
        "queries": 0,
        "latency_ms": 0,
        "trace_steps": 0,
        "fallback_steps": 0,
        "trace_path": str(trace) if trace else "",
    }


def _from_trace(path: Path) -> dict[str, int]:
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {
        "tokens_in": sum(int(event.get("tokens_in") or 0) for event in events),
        "tokens_out": sum(int(event.get("tokens_out") or 0) for event in events),
        "model_calls": sum(1 for event in events if event.get("action") == "model_call"),
        "queries": sum(1 for event in events if event.get("query_id")),
        "trace_steps": len(events),
        "fallback_steps": sum(1 for event in events if event.get("status") == "fallback"),
    }


def _copy_trace(log_dir: Path, out: Path) -> Path | None:
    found = sorted(log_dir.glob("trace-*.jsonl"))
    if not found:
        return None
    dest = out / "traces" / found[-1].name
    shutil.copyfile(found[-1], dest)
    return dest


def _summary(
    grouped: dict[str, list[dict[str, Any]]],
    *,
    splits: list[str],
    truth: dict[str, dict[str, Any]],
    out: Path,
    document: dict[str, Any],
) -> dict[str, Any]:
    traces = list((out / "traces").glob("trace-*.jsonl"))
    described = describe_run(traces) if traces else {"model_ids": [], "offline": True}
    n = max((len(rows) for rows in grouped.values()), default=0)
    return {
        "splits": list(splits),
        "split_sha256": {name: (document.get("sha256") or {}).get(name) for name in splits},
        "n": n,
        "mode": {"data": "duckdb", "llm": "offline"},
        "offline": True,
        "provider": "offline",
        "model_ids": described["model_ids"],
        "synthetic": True,
        "git_sha": _git_sha(),
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "systems": {name: _score(rows, name, truth) for name, rows in sorted(grouped.items())},
    }


def _score(rows: list[dict[str, Any]], system: str, truth: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Headline metrics use the first run of each case. Consistency uses every repeat."""
    primary = [row for row in rows if int(row.get("repeat") or 0) == 0]
    scored = score_rows(primary or rows, system=system, truth_facts=truth)
    scored["consistency"] = score_rows(rows, system=system).get("consistency")
    return scored


def _env(out: Path, *, splits: list[str], document: dict[str, Any]) -> None:
    described = describe_run(list((out / "traces").glob("trace-*.jsonl")))
    payload = {
        "git_sha": _git_sha(),
        "mode": {"data": "duckdb", "llm": "offline"},
        "provider": "offline",
        "model_ids": described["model_ids"],
        "catalog_version": _catalog_version(),
        "split_sha256": {name: (document.get("sha256") or {}).get(name) for name in splits},
        "calibration_version": _active_calibration(),
    }
    (out / "env.json").write_text(_dump(payload), encoding="utf-8")


def _confusion(path: Path, rows: list[dict[str, Any]]) -> None:
    labels = [*OUTCOMES, "INVALID"]
    grid = {expected: {predicted: 0 for predicted in labels} for expected in labels}
    for row in rows:
        expected = row["expected_outcome"] if row["expected_outcome"] in grid else "INVALID"
        predicted = row["predicted_outcome"] if row["predicted_outcome"] in labels else "INVALID"
        grid[expected][predicted] += 1
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["expected", *labels])
        for expected in labels:
            writer.writerow([expected, *[grid[expected][predicted] for predicted in labels]])


def _write_cases(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_jsonl(path, rows)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [json.dumps(row, sort_keys=True, default=str) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n"


def _json_default(value: object) -> object:
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"not JSON serialisable: {type(value).__name__}")


def _active_calibration() -> str:
    path = ROOT / "policy" / "calibration" / "ACTIVE"
    return path.read_text(encoding="utf-8").strip()


def _git_sha() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return "unknown"
    return proc.stdout.strip() or "unknown"


def _catalog_version() -> str:
    payload = json.loads((ROOT / "data" / "kev" / "kev_snapshot.json").read_text(encoding="utf-8"))
    return str(payload.get("catalogVersion") or "")
