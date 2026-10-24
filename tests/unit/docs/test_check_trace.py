"""P17-T8: check_trace --require-live needs a successful Nightshift model call, not just a provider field."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.check_trace import validate_file

pytestmark = pytest.mark.p17

ROOT = Path(__file__).resolve().parents[3]
LIVE = ROOT / "logs" / "examples" / "live"
FAILED = ROOT / "logs" / "examples" / "live_failed"


def _is_successful_call(event: dict) -> bool:
    return (
        event.get("provider") == "meterless" and event.get("status") == "success" and bool(event.get("model"))
    )


def test_p17_t8_committed_live_traces_pass() -> None:
    """P17-T8: every trace in logs/examples/live/ still passes --require-live --require-collaboration."""
    traces = sorted(LIVE.glob("trace-*.jsonl"))
    assert traces
    for path in traces:
        assert validate_file(path, require_collaboration=True, require_live=True) == [], path


def test_p17_t8_failed_live_attempts_fail() -> None:
    """P17-T8: the example 3 attempts, whose only Meterless call fell back, fail --require-live."""
    traces = sorted(FAILED.glob("trace-*.jsonl"))
    assert traces
    for path in traces:
        errors = validate_file(path, require_collaboration=False, require_live=True)
        assert any("no successful provider=meterless model call" in e for e in errors), (path, errors)


def test_p17_t8_fallback_only_trace_fails(tmp_path: Path) -> None:
    """P17-T8: removing every successful model call from a passing live trace makes it fail."""
    source = sorted(LIVE.glob("trace-*.jsonl"))[0]
    kept = [
        line
        for line in source.read_text(encoding="utf-8").splitlines()
        if not _is_successful_call(json.loads(line))
    ]
    assert any(json.loads(line).get("provider") == "meterless" for line in kept), (
        "fixture needs a fallback event"
    )
    path = tmp_path / "trace-run-fallback.jsonl"
    path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    errors = validate_file(path, require_collaboration=False, require_live=True)
    assert errors == [f"{path}: no successful provider=meterless model call"]
    assert validate_file(path, require_collaboration=False, require_live=False) == []
