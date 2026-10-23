"""P6-T3: generated examples keep the P5-B header shape and a real collaborative trace."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.check_trace import validate_file

pytestmark = pytest.mark.p6

ROOT = Path(__file__).resolve().parents[3]


def test_p6_t3_examples_match_traces() -> None:
    """P6-T3: each output header was written by run.py examples and its trace checks out."""
    inputs = sorted((ROOT / "input_examples").glob("example_*.json"))
    files = sorted((ROOT / "output_examples").glob("example_*_output.json"))
    assert len(inputs) == 6
    assert [path.name for path in files] == [f"{path.stem}_output.json" for path in inputs]
    for path in files:
        document = json.loads(path.read_text(encoding="utf-8"))
        header = document["header"]
        assert header["generated_by"] == "python run.py examples"
        assert isinstance(header["mode"], dict)
        assert isinstance(header["p50_ms"], (int, float))
        assert header["n_runs"] >= 1
        assert header["git_sha"]
        assert header["generated_at"]
        live = _says_live(header)
        if not live:
            assert header.get("provider") == "offline" or "offline" in json.dumps(header["mode"]).lower()
        trace = ROOT / "logs" / "examples" / f"trace-{header['run_id']}.jsonl"
        assert trace.is_file(), header["run_id"]
        errors = validate_file(trace, require_collaboration=True, require_live=live)
        assert errors == []
        assert document["response"]["run_id"] == header["run_id"]


def _says_live(header: dict) -> bool:
    mode = header.get("mode")
    if isinstance(mode, str):
        return mode == "live"
    if isinstance(mode, dict):
        return mode.get("llm") == "meterless" and mode.get("data") == "zetaris"
    return False
