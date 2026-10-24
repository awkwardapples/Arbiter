"""P15-T4: regression guard for B5/B6. The clean-clone script writes docs/ only with --evidence."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.p15

ROOT = Path(__file__).resolve().parents[3]
_RESULTS = [(n, True, "ok") for n in range(1, 9)]


def _write_report():
    from scripts.clean_clone_check import _write_report

    return _write_report


def test_p15_t4_report_without_evidence_skips_docs(tmp_path: Path) -> None:
    _write_report()(tmp_path, _RESULTS, evidence=False)
    assert (tmp_path / "logs" / "clean-clone-report.md").is_file()
    assert not (tmp_path / "docs").exists()


def test_p15_t4_report_with_evidence_writes_dated_file(tmp_path: Path) -> None:
    _write_report()(tmp_path, _RESULTS, evidence=True)
    dated = sorted((tmp_path / "docs" / "passes").glob("clean-clone-*.md"))
    assert len(dated) == 1
    assert "step 8: pass" in dated[0].read_text(encoding="utf-8")


def _docs_snapshot() -> dict[str, bytes]:
    return {str(p.relative_to(ROOT)): p.read_bytes() for p in (ROOT / "docs").rglob("*") if p.is_file()}


def test_p15_t4_docker_run_leaves_docs_untouched() -> None:
    """Opt-in: a full run without --evidence must not change anything under docs/."""
    if os.environ.get("ARBITER_DOCKER_TESTS") != "1" or shutil.which("docker") is None:
        pytest.skip("clean-clone is opt-in: set ARBITER_DOCKER_TESTS=1 with a running Docker daemon")
    before = _docs_snapshot()
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "clean_clone_check.py"), "--local", str(ROOT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert _docs_snapshot() == before
