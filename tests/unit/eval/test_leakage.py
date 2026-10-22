"""P5-T6: app/ does not read labels, splits, output examples, or expected.json."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.p5b

ROOT = Path(__file__).resolve().parents[3]


def test_p5_t6_repo_scan_is_clean() -> None:
    """P5-T6: check_hardcoding passes on this repo."""
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_hardcoding.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_p5_t6_scanner_flags_a_planted_label_read(tmp_path: Path) -> None:
    """P5-T6: a module under app/ that mentions labels.jsonl is reported."""
    from scripts.check_hardcoding import scan_path

    app = tmp_path / "app"
    app.mkdir()
    (app / "leak.py").write_text("path = 'labels.jsonl'\n", encoding="utf-8")
    findings = scan_path(app)
    assert any("labels.jsonl" in item for item in findings)
