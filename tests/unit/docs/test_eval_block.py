"""P6-T6: the README eval block is the rendered latest summary, and the markers are mandatory."""

from __future__ import annotations

from pathlib import Path

import pytest

from eval.report import latest_summary, render_summary_md

pytestmark = pytest.mark.p6

ROOT = Path(__file__).resolve().parents[3]
_START = "<!-- EVAL:START -->"
_END = "<!-- EVAL:END -->"


def test_p6_t6_readme_eval_block_matches_latest_summary() -> None:
    """P6-T6: markers exist and the block equals render(latest summary.json)."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert _START in text and _END in text
    start = text.index(_START) + len(_START)
    end = text.index(_END)
    block = text[start:end].strip("\n")
    expected = render_summary_md(latest_summary(ROOT / "eval" / "results")).strip("\n")
    assert block == expected
