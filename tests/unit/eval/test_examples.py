"""Offline examples: six real runs, traces, and a recorded p50 per example."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.check_trace import validate_file

pytestmark = pytest.mark.p5b

ROOT = Path(__file__).resolve().parents[3]


def test_offline_examples_have_traces_and_p50() -> None:
    """The offline gate writes one output per input example, with a trace and p50_ms."""
    out_dir = ROOT / "output_examples"
    files = sorted(out_dir.glob("example_*_output.json"))
    inputs = sorted((ROOT / "input_examples").glob("example_*.json"))
    assert len(inputs) == 6
    assert [path.name for path in files] == [f"{path.stem}_output.json" for path in inputs]
    for path in files:
        document = json.loads(path.read_text(encoding="utf-8"))
        header = document["header"]
        assert header["run_id"]
        assert "offline" in json.dumps(header["mode"]).lower() or header.get("provider") == "offline"
        assert isinstance(header["p50_ms"], (int, float))
        assert header["p50_ms"] >= 0
        assert header["n_runs"] >= 1
        assert "git_sha" in header
        trace = ROOT / "logs" / "examples" / f"trace-{header['run_id']}.jsonl"
        assert trace.is_file()
        assert validate_file(trace, require_collaboration=True, require_live=False) == []
        assert document["response"]["run_id"] == header["run_id"]
