"""assess prints the same RunResponse POST /run returns, from orchestrator.run."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.schemas.api import RunResponse

pytestmark = pytest.mark.p6

ROOT = Path(__file__).resolve().parents[3]


def test_assess_prints_run_response() -> None:
    """A sample/offline assess of example 1 exits 0 and validates as RunResponse."""
    env = os.environ.copy()
    env["SAMPLE_MODE"] = "true"
    env["LLM_PROVIDER"] = "offline"
    env["ARBITER_MEMORY"] = "off"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "run.py"), "assess", "--input", "input_examples/example_1.json"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    parsed = RunResponse.model_validate(json.loads(proc.stdout))
    expected = json.loads((ROOT / "input_examples" / "expected.json").read_text(encoding="utf-8"))
    assert parsed.output is not None
    assert parsed.output.decision == expected["example_1.json"]["outcome"]
    assert parsed.log_file.startswith("logs/trace-")
