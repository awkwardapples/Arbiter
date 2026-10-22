"""P3-T14: run budget exceeded → SAFE_ESCALATE with a valid response, quickly."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

from app.data.factory import get_backend
from app.orchestrator import Deps, RunOptions, run
from app.schemas.api import RunResponse
from app.schemas.case import CaseInput
from app.store import Store

pytestmark = pytest.mark.p3


class FakeMonotonic:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class SlowBackend:
    """Each call costs 0.6 s of (injected) time; no real sleeping."""

    name = "slow"

    def __init__(self, inner: Any, clock: FakeMonotonic) -> None:
        self.inner = inner
        self.clock = clock

    def run(self, query_id: str, params: dict[str, object]) -> Any:
        self.clock.now += 0.6
        return self.inner.run(query_id, params)


def test_p3_t14_budget_exceeded_safe_escalates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SAMPLE_MODE", "true")
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    monkeypatch.setenv("ARBITER_MEMORY", "off")
    monkeypatch.setenv("RUN_BUDGET_SECONDS", "1")
    clock = FakeMonotonic()

    def factory(settings: Any, tracer: Any, submission: Any = None) -> Any:
        return SlowBackend(get_backend(settings, tracer, submission), clock)

    started = time.perf_counter()
    resp = run(
        CaseInput(vendor_id="VND-0007"),
        options=RunOptions(),
        deps=Deps(backend_factory=factory, monotonic=clock),
    )
    elapsed = time.perf_counter() - started

    assert elapsed < 5
    RunResponse.model_validate(resp.model_dump())
    assert resp.status in {"partial_success", "escalated"}
    assert resp.output is not None
    assert resp.output.decision == "ESCALATE"
    bundle = Store().get(resp.output.case_id)
    assert "SYSTEM_BudgetExceeded" in bundle.decision.escalation_reasons
    assert bundle.report.generator == "template:v1"
    assert Path(resp.log_file).is_file()
