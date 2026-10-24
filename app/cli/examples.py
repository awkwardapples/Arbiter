"""Generate output examples by running the real orchestrator."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.llm.resolve import reset_cache
from app.orchestrator import Deps, RunOptions, run
from app.schemas.case import CaseInput
from app.schemas.trace import TraceEvent
from app.tracing import Tracer

ROOT = Path(__file__).resolve().parents[2]
_OFFLINE_NOTE = (
    "Offline sample-mode timings do not include a model call. "
    "p50 is recorded anyway and is not a live latency."
)
_LIVE_NOTE = "p50 is the wall time of this one run, including provider calls."


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("examples", help="Generate output examples and traces")
    p.add_argument("--live", action="store_true")
    p.set_defaults(_handler=cmd_examples)


def example_dirs(*, live: bool) -> tuple[Path, Path]:
    """(outputs, traces). Live runs are the headline set; sample mode is what a keyless judge reproduces."""
    if live:
        return ROOT / "output_examples", ROOT / "logs" / "examples" / "live"
    return ROOT / "output_examples" / "sample_mode", ROOT / "logs" / "examples" / "sample_mode"


def cmd_examples(args: argparse.Namespace) -> None:
    _prepare(live=bool(args.live))
    out_dir, traces = example_dirs(live=bool(args.live))
    out_dir.mkdir(parents=True, exist_ok=True)
    traces.mkdir(parents=True, exist_ok=True)
    live_miss: list[str] = []
    for path in sorted((ROOT / "input_examples").glob("example_*.json")):
        case = CaseInput.model_validate(json.loads(path.read_text(encoding="utf-8")))
        response, trace_bytes, run_id, mode, latency_ms = _once(case, live=bool(args.live))
        if args.live and not _is_live(mode):
            live_miss.append(path.name)
            continue
        (traces / f"trace-{run_id}.jsonl").write_bytes(trace_bytes)
        header = example_header(
            run_id=run_id,
            mode=mode,
            provider="offline" if mode.get("llm") == "offline" else str(mode.get("llm") or "unrecorded"),
            git_sha=_git_sha(),
            generated_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            p50_ms=latency_ms,
            n_runs=1,
            timing_note=_OFFLINE_NOTE if mode.get("llm") == "offline" else _LIVE_NOTE,
        )
        write_example(out_dir / f"{path.stem}_output.json", header=header, response=response)
    export_trace_schema(ROOT / "docs" / "trace_schema.json")
    if live_miss:
        raise SystemExit(f"--live did not stay on Zetaris and Meterless: {', '.join(live_miss)}")


def example_header(
    *,
    run_id: str,
    mode: dict[str, str],
    provider: str,
    git_sha: str,
    generated_at: str,
    p50_ms: float,
    n_runs: int,
    timing_note: str,
) -> dict[str, object]:
    return {
        "generated_by": "python run.py examples",
        "run_id": run_id,
        "mode": mode,
        "provider": provider,
        "git_sha": git_sha,
        "generated_at": generated_at,
        "p50_ms": p50_ms,
        "n_runs": n_runs,
        "timing_note": timing_note,
    }


def write_example(path: Path, *, header: dict[str, object], response: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {"header": header, "response": response}
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def export_trace_schema(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    schema = TraceEvent.model_json_schema()
    path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _prepare(*, live: bool) -> None:
    os.environ["ARBITER_MEMORY"] = "off"
    if live:
        # Pinned to Nightshift: an outage fails the run instead of falling back to NVIDIA direct.
        os.environ["SAMPLE_MODE"] = "false"
        os.environ["LLM_PROVIDER"] = "meterless"
    else:
        os.environ["SAMPLE_MODE"] = "true"
        os.environ["LLM_PROVIDER"] = "offline"
    get_settings.cache_clear()
    reset_cache()


def _once(case: CaseInput, *, live: bool) -> tuple[dict[str, Any], bytes, str, dict[str, str], float]:
    get_settings.cache_clear()
    reset_cache()
    with tempfile.TemporaryDirectory(prefix="arbiter-example-") as tmp:
        work = Path(tmp)
        box: dict[str, Tracer] = {}

        def factory(run_id: str, mode: dict[str, str]) -> Tracer:
            box["tracer"] = Tracer(run_id, mode=mode, log_dir=str(work / "logs"))
            return box["tracer"]

        if live:
            options = RunOptions(sample_mode=False, llm="meterless")
        else:
            options = RunOptions(sample_mode=True, llm="offline")
        response = run(case, options=options, deps=Deps(var_dir=work / "var", tracer_factory=factory))
        tracer = box.get("tracer")
        if tracer is not None:
            tracer.close()
        found = sorted((work / "logs").glob("trace-*.jsonl"))
        if not found:
            raise RuntimeError(f"example run {response.run_id} wrote no trace")
        mode = {str(key): str(value) for key, value in response.mode.items()}
        return (
            response.model_dump(mode="json"),
            found[-1].read_bytes(),
            response.run_id,
            mode,
            response.execution_time_seconds * 1000,
        )


def _is_live(mode: dict[str, str]) -> bool:
    return mode.get("data") == "zetaris" and mode.get("llm") == "meterless"


def _git_sha() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip() or "unknown"
