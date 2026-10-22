"""P5-T4: the eval session command passes the six offline demo-session steps."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.p5b

ROOT = Path(__file__).resolve().parents[2]


def test_p5_t4_session_offline(tmp_path: Path) -> None:
    """P5-T4: eval --session reuses demo-session and all six steps pass offline."""
    env = os.environ.copy()
    env["SAMPLE_MODE"] = "true"
    env["LLM_PROVIDER"] = "offline"
    env["ARBITER_MEMORY"] = "on"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "run.py"), "eval", "--session"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.count("| yes |") == 6
    assert "| NO |" not in proc.stdout
