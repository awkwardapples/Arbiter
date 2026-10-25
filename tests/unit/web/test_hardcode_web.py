"""P18B-T10: the hardcode check scans the web console's sources."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.p18b

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "check_hardcoding.py"
WEB_SRC = ROOT / "web" / "src"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=ROOT, capture_output=True, text=True, check=False
    )


def test_p18b_t10_web_src_in_default_scan() -> None:
    """P18B-T10: web/src is scanned by default and the real tree passes."""
    from scripts import check_hardcoding

    assert "web/src" in check_hardcoding.SCAN_DIRS
    proc = _run()
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_p18b_t10_vendor_literal_fails() -> None:
    """P18B-T10: a temporary web/src file holding a vendor id literal fails the check."""
    canary = WEB_SRC / "__p18b_canary.ts"
    try:
        canary.write_text('export const pick = "VND-0007";\n', encoding="utf-8")
        proc = _run()
    finally:
        canary.unlink(missing_ok=True)
    assert proc.returncode != 0
    assert "__p18b_canary.ts" in proc.stdout
    assert "VND-0007" in proc.stdout


@pytest.mark.parametrize(
    ("body", "needle"),
    [
        ('export const c = "CASE-0007";\n', "CASE-0007"),
        ('export const s = "S04";\n', "scenario"),
        ('export const p = "output_examples/x.json";\n', "output_examples"),
    ],
)
def test_p18b_t10_other_literals_fail(tmp_path: Path, body: str, needle: str) -> None:
    """P18B-T10: case ids, scenario codes and forbidden strings fail in .ts/.tsx under web/src."""
    src = tmp_path / "web" / "src"
    src.mkdir(parents=True)
    (src / "page.tsx").write_text(body, encoding="utf-8")
    proc = _run(str(src))
    assert proc.returncode != 0
    assert needle in proc.stdout


def test_p18b_t10_tests_folder_exempt(tmp_path: Path) -> None:
    """P18B-T10: only web/src/**/__tests__/** is exempt."""
    src = tmp_path / "web" / "src"
    (src / "run" / "__tests__").mkdir(parents=True)
    (src / "run" / "__tests__" / "x.test.ts").write_text('const v = "VND-0007";\n', encoding="utf-8")
    assert _run(str(src)).returncode == 0
    (src / "run" / "x.ts").write_text('const v = "VND-0007";\n', encoding="utf-8")
    assert _run(str(src)).returncode != 0
