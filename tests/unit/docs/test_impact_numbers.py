"""P19-T1: the Zetaris time in IMPACT is recomputed from the committed live trace."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.p19

ROOT = Path(__file__).resolve().parents[3]
TRACE = ROOT / "logs" / "examples" / "live" / "trace-run-83de5da137c0.jsonl"


def test_p19_t1_impact_zetaris_time() -> None:
    """Each query is logged twice; only the query_zetaris events carry the Zetaris latency."""
    events = [json.loads(line) for line in TRACE.read_text(encoding="utf-8").splitlines() if line.strip()]
    queries = [event for event in events if event.get("action") == "query_zetaris"]
    assert len(queries) == 12
    seconds = sum(int(event["latency_ms"]) for event in queries) / 1000
    impact = (ROOT / "docs" / "IMPACT.md").read_text(encoding="utf-8")
    assert f"{seconds:.1f} s of Zetaris time" in impact
    assert "33 s" not in impact
