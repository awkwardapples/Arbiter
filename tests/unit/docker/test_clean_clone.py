"""P4-T18: output_examples is required, and the opt-in local clean-clone run."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.p4b

ROOT = Path(__file__).resolve().parents[3]
_NEED = "output_examples/ needs at least 3 files"


def _classify():
    try:
        from scripts.clean_clone_check import classify_output_examples
    except ImportError as exc:
        pytest.fail(f"clean_clone_check is not implemented: {exc}")
    return classify_output_examples


def test_p4_t18_output_examples_rule(tmp_path: Path) -> None:
    """P4-T18: output_examples is required. Absent or short directories fail."""
    classify_output_examples = _classify()
    ok, message = classify_output_examples(tmp_path)
    assert ok is False
    assert message == _NEED

    present = tmp_path / "output_examples"
    present.mkdir()
    (present / "a.json").write_text("{}", encoding="utf-8")
    ok, message = classify_output_examples(tmp_path)
    assert ok is False
    assert message == _NEED

    (present / "b.json").write_text("{}", encoding="utf-8")
    (present / "c.json").write_text("{}", encoding="utf-8")
    ok, message = classify_output_examples(tmp_path)
    assert ok is True
    assert message == "ok"


def test_p4_t18_clean_clone_local() -> None:
    """P4-T18: clean_clone_check.py --local . passes steps 1-8 when docker is available."""
    if os.environ.get("DOCKER") == "0" or shutil.which("docker") is None:
        pytest.skip("clean-clone is opt-in; skip when DOCKER=0 or docker is not on PATH")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "clean_clone_check.py"), "--local", str(ROOT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = ROOT / "logs" / "clean-clone-report.md"
    assert report.is_file()
    text = report.read_text(encoding="utf-8")
    for step in range(1, 9):
        assert f"step {step}: pass" in text
