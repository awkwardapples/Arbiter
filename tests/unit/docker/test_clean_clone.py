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
    if os.environ.get("ARBITER_DOCKER_TESTS") != "1" or shutil.which("docker") is None:
        pytest.skip("clean-clone is opt-in: set ARBITER_DOCKER_TESTS=1 with a running Docker daemon")
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


@pytest.mark.p20
def test_p20_history_scan_follows_deleted_files(tmp_path: Path) -> None:
    """A deleted file's diff ends in '+++ /dev/null'; its lines belong to its '--- a/' path."""
    from scripts.clean_clone_check import _history_secrets

    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=example", "-c", "user.email=example@example.invalid", *args],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

    lookalike = "sk" + "-" + "x" * 24  # minified-bundle text that matches the key pattern
    (tmp_path / ".secrets-allowlist").write_text("bundle/*\n", encoding="utf-8")
    (tmp_path / "bundle").mkdir()
    (tmp_path / "bundle" / "app.js").write_text(f"var a='{lookalike}';\n", encoding="utf-8")
    (tmp_path / "a.txt").write_text("one\n", encoding="utf-8")
    git("init", "-q")
    git("add", ".")
    git("commit", "-q", "-m", "add")
    (tmp_path / "bundle" / "app.js").unlink()
    (tmp_path / "a.txt").write_text("two\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "delete the bundle")
    assert _history_secrets(tmp_path) == ""
