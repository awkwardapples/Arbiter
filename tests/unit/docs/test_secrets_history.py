"""P6-T5: the full git history is free of secret patterns."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.p6

ROOT = Path(__file__).resolve().parents[3]


def test_p6_t5_history_clean() -> None:
    """P6-T5: scan_secrets.py --history exits 0."""
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "scan_secrets.py"), str(ROOT), "--history"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
