"""Write output examples from real offline orchestrator runs."""

from __future__ import annotations

import json
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.llm.resolve import reset_cache
from app.orchestrator import Deps, RunOptions, run
from app.schemas.case import CaseInput
from app.tracing import Tracer
from eval.corpus import ROOT
from eval.harness import force_offline

_NOTE = (
    "Offline sample-mode timings do not include a model call. "
    "p50 is recorded anyway and is not a live latency."
)


def write_offline_examples(
    *,
    out_dir: Path | None = None,
    logs_dir: Path | None = None,
    repeats: int = 3,
) -> list[Path]:
    """Run each input example `repeats` times and keep the last trace."""
    force_offline()
    destination = out_dir or (ROOT / "output_examples")
    traces = logs_dir or (ROOT / "logs" / "examples")
    destination.mkdir(parents=True, exist_ok=True)
    traces.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for path in sorted((ROOT / "input_examples").glob("example_*.json")):
        case = CaseInput.model_validate(json.loads(path.read_text(encoding="utf-8")))
        latencies: list[float] = []
        response: dict[str, Any] | None = None
        trace_bytes = b""
        run_id = ""
        mode: dict[str, str] = {}
        for _index in range(repeats):
            response, trace_bytes, run_id, mode, latency = _once(case)
            latencies.append(latency)
        assert response is not None and trace_bytes
        trace_dest = traces / f"trace-{run_id}.jsonl"
        trace_dest.write_bytes(trace_bytes)
        header = {
            "generated_by": "orchestrator.run offline gate (sample mode, DuckDB)",
            "run_id": run_id,
            "mode": mode,
            "provider": "offline",
            "git_sha": _git_sha(),
            "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "p50_ms": _median(latencies),
            "n_runs": repeats,
            "timing_note": _NOTE,
        }
        document = {"header": header, "response": response}
        target = destination / f"{path.stem}_output.json"
        target.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(target)
    return written


def _once(case: CaseInput) -> tuple[dict[str, Any], bytes, str, dict[str, str], float]:
    get_settings.cache_clear()
    reset_cache()
    settings = Settings()
    with tempfile.TemporaryDirectory(prefix="arbiter-example-") as tmp:
        work = Path(tmp)
        box: dict[str, Tracer] = {}

        def factory(run_id: str, mode: dict[str, str]) -> Tracer:
            box["tracer"] = Tracer(run_id, mode=mode, log_dir=str(work / "logs"))
            return box["tracer"]

        response = run(
            case,
            options=RunOptions(sample_mode=True, llm="offline"),
            deps=Deps(var_dir=work / "var", tracer_factory=factory),
        )
        tracer = box.get("tracer")
        if tracer is not None:
            tracer.close()
        found = sorted((work / "logs").glob("trace-*.jsonl"))
        if not found:
            raise RuntimeError(f"example run {response.run_id} wrote no trace")
        payload = response.model_dump(mode="json")
        latency_ms = response.execution_time_seconds * 1000
        return payload, found[-1].read_bytes(), response.run_id, settings.mode(), latency_ms


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 0:
        return (ordered[mid - 1] + ordered[mid]) / 2
    return float(ordered[mid])


def _git_sha() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip() or "unknown"
