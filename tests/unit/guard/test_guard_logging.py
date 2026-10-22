"""P2-T43: guard never logs segment text."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.guard.scout_guard import guard
from app.tracing import Tracer

pytestmark = pytest.mark.p2d

CANARY = "canary-segment-text-9f3a2b1c"


def test_p2_t43_no_segment_text_in_logs_or_trace(caplog: pytest.LogCaptureFixture, tmp_path: Path) -> None:
    caplog.set_level("INFO", logger="arbiter.guard")
    tracer = Tracer("run-canary", mode={"sample": "true"}, log_dir=str(tmp_path / "logs"))
    try:
        guard(
            f"Normal vendor answer with {CANARY} embedded.",
            surface="vendor_answer",
            capabilities=set(),
            segment_id="seg-canary",
            tracer=tracer,
            use_model=False,
        )
    finally:
        tracer.close()

    for record in caplog.records:
        assert CANARY not in record.getMessage()

    trace_path = tmp_path / "logs" / "trace-run-canary.jsonl"
    trace_blob = trace_path.read_text(encoding="utf-8")
    assert CANARY not in trace_blob
    for line in trace_blob.splitlines():
        if not line.strip():
            continue
        evt = json.loads(line)
        assert CANARY not in evt.get("input_summary", "")
        assert CANARY not in evt.get("output_summary", "")
