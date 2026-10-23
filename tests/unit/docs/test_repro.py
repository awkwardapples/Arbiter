"""P6-T4: output examples are required, and clean-clone does not post to a fixed host port."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.p6

ROOT = Path(__file__).resolve().parents[3]


def test_p6_t4_step1_files_present() -> None:
    """P6-T4: the repo has the files clean-clone step 1 requires, including three outputs."""
    for name in ("run.py", "README.md", ".env.example"):
        assert (ROOT / name).is_file()
    assert len(list((ROOT / "input_examples").glob("*.json"))) >= 3
    outputs = [path for path in (ROOT / "output_examples").iterdir() if path.is_file()]
    assert len(outputs) >= 3


def test_p6_t4_output_examples_are_required(tmp_path: Path) -> None:
    """P6-T4: a missing output_examples directory fails. The P6 waiver is closed."""
    from scripts.clean_clone_check import classify_output_examples

    ok, message = classify_output_examples(tmp_path)
    assert ok is False
    assert "waiver" not in message.lower()

    present = tmp_path / "output_examples"
    present.mkdir()
    (present / "a.json").write_text("{}", encoding="utf-8")
    (present / "b.json").write_text("{}", encoding="utf-8")
    ok, message = classify_output_examples(tmp_path)
    assert ok is False

    (present / "c.json").write_text("{}", encoding="utf-8")
    ok, message = classify_output_examples(tmp_path)
    assert ok is True


def test_p6_t4_clean_clone_does_not_post_to_fixed_port() -> None:
    """P6-T4: step 3 must not target host port 8000, which may be a dev server."""
    text = (ROOT / "scripts" / "clean_clone_check.py").read_text(encoding="utf-8")
    assert '"8000:8000"' not in text
    assert "127.0.0.1:8000" not in text


def test_p6_t4_public_clean_clone() -> None:
    """P6-T4: public clean-clone is opt-in. Docker sample smoke stays on P4-T17."""
    if os.environ.get("ARBITER_CLEAN_CLONE") != "1":
        pytest.skip("public clean-clone runs when ARBITER_CLEAN_CLONE=1")
    if shutil.which("docker") is None:
        pytest.skip("docker is not on PATH")
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "clean_clone_check.py"),
            "https://github.com/awkwardapples/Arbiter",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
