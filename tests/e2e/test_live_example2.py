"""P3-T15 (live): example 2 through Zetaris and Nightshift. Runs only with ARBITER_LIVE_TESTS=1."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.orchestrator import RunOptions, run
from scripts.check_trace import validate_file
from tests.e2e.support import load_example, trace

pytestmark = [pytest.mark.p3, pytest.mark.live]


@pytest.mark.skipif(os.environ.get("ARBITER_LIVE_TESTS") != "1", reason="live services required")
def test_p3_t15_example_2_live(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAMPLE_MODE", "false")
    monkeypatch.setenv("ARBITER_MEMORY", "off")
    resp = run(load_example("example_2.json"), options=RunOptions())
    assert validate_file(Path(resp.log_file), require_collaboration=True, require_live=True) == []
    assert resp.output.decision == "ESCALATE"
    rows = trace(resp.log_file)
    assert any("zetaris_request_id=" in r["output_summary"] for r in rows if r.get("backend") == "zetaris")
    assert any(r.get("provider") == "meterless" for r in rows if r["action"] == "model_call")
