"""P20: the workload counts come from the file the tracer wrote, wherever the caller logs it."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import orchestrator
from app.orchestrator import Deps, RunOptions, run
from app.state import CaseState
from app.tracing import Tracer
from tests.e2e.support import load_example, offline_env  # noqa: F401

pytestmark = pytest.mark.p20


def _events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_p20_workload_reads_a_tracer_outside_logs(offline_env: Path, tmp_path: Path) -> None:  # noqa: F811
    elsewhere = tmp_path / "elsewhere"
    box: dict[str, Tracer] = {}

    def factory(run_id: str, mode: dict[str, str]) -> Tracer:
        box["tracer"] = Tracer(run_id, mode=mode, log_dir=str(elsewhere))
        return box["tracer"]

    response = run(
        load_example("example_2.json"),
        options=RunOptions(sample_mode=True, llm="offline"),
        deps=Deps(var_dir=tmp_path / "var", tracer_factory=factory),
    )
    box["tracer"].close()
    assert not (offline_env / "logs" / f"trace-{response.run_id}.jsonl").exists()
    events = _events(box["tracer"].path)
    workload = response.output.workload
    assert workload is not None
    assert workload.queries == sum(e.get("action") == "query_run" for e in events) > 0
    assert workload.model_calls == sum(e.get("action") == "model_call" for e in events)


def test_p20_workload_lists_served_models(tmp_path: Path) -> None:
    path = tmp_path / "trace-run-x.jsonl"
    lines = [
        {"action": "model_call", "model": "nvidia/nemotron-3.5-super-vl-120b-a12b", "status": "success"},
        {"action": "model_call", "model": "nvidia/nemotron-3.5-lightning-30b-a3b", "status": "success"},
        {"action": "model_call", "model": None, "status": "fallback"},
        {"action": "query_run", "backend": "zetaris"},
    ]
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    state = CaseState.model_construct(
        case_id="CASE-X",
        executed_queries={},
        segments=[],
        claims=[],
        contradictions=[],
        dq_flags=[],
        guard_flags=[],
    )
    workload = orchestrator._workload(state, path, 1.0)
    assert workload.models == [
        "nvidia/nemotron-3.5-lightning-30b-a3b",
        "nvidia/nemotron-3.5-super-vl-120b-a12b",
    ]
    assert workload.model_calls == 3
    assert workload.queries == 1
