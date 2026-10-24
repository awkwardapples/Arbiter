"""P15-T5: every committed live example trace is live and collaborative. Runs on committed files."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.check_trace import validate_file

pytestmark = pytest.mark.p15

ROOT = Path(__file__).resolve().parents[3]
LIVE = ROOT / "logs" / "examples" / "live"


def _traces() -> list[Path]:
    return sorted(LIVE.glob("trace-*.jsonl"))


def _events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_p15_t5_live_traces_exist_for_every_example() -> None:
    traces = _traces()
    assert len(traces) >= 6, "run `python run.py examples --live` against Zetaris and Nightshift"
    names = {path.name for path in traces}
    for path in sorted((ROOT / "output_examples").glob("example_*_output.json")):
        header = json.loads(path.read_text(encoding="utf-8"))["header"]
        assert header["mode"].get("llm") == "meterless", path.name
        assert header["mode"].get("data") == "zetaris", path.name
        assert f"trace-{header['run_id']}.jsonl" in names, path.name


def test_p15_t5_check_trace_live_and_collaboration() -> None:
    for path in _traces():
        assert validate_file(path, require_collaboration=True, require_live=True) == [], path.name


def test_p15_t5_trace_shows_zetaris_request_and_nemotron_receipt() -> None:
    for path in _traces():
        events = _events(path)
        zetaris = [e for e in events if e.get("backend") == "zetaris" and e.get("query_id")]
        assert any("zetaris_request_id=" in (e.get("output_summary") or "") for e in zetaris), path.name
        calls = [e for e in events if e.get("provider") == "meterless" and e.get("action") == "model_call"]
        assert calls, path.name
        assert any("nemotron" in (e.get("model") or "") for e in calls), path.name
        assert any((e.get("provider_meta") or {}).get("receipt_id", "").startswith("rcpt_") for e in calls)
