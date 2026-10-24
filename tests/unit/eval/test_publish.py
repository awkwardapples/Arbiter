"""P5-T5 and P5-T8: README block matches a published summary; publish stays inside the markers."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.p5b

ROOT = Path(__file__).resolve().parents[3]


def test_p5_t5_readme_block_matches_latest() -> None:
    """P5-T5: once the README markers exist, the block equals render(latest summary.json).

    P17 retarget: the latest results are the live run in eval/results_live/.
    """
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8") if readme.is_file() else ""
    if "<!-- EVAL:START -->" not in text or "<!-- EVAL:END -->" not in text:
        pytest.skip("README eval markers are added in P6")
    from eval.report import latest_summary, render_summary_md

    rendered = render_summary_md(latest_summary(ROOT / "eval" / "results_live"))
    start = text.index("<!-- EVAL:START -->") + len("<!-- EVAL:START -->")
    end = text.index("<!-- EVAL:END -->")
    assert text[start:end].strip() == rendered.strip()


def test_p5_t8_publish_is_idempotent(tmp_path: Path) -> None:
    """P5-T8: publish rewrites only the docs file and the README block, and a second call is a no-op."""
    from eval.report import publish, render_summary_md

    summary = {
        "splits": ["test"],
        "n": 0,
        "mode": {"data": "duckdb", "llm": "offline"},
        "offline": True,
        "synthetic": True,
        "systems": {},
    }
    readme = tmp_path / "README.md"
    readme.write_text(
        "before\n<!-- EVAL:START -->\nold numbers\n<!-- EVAL:END -->\nafter sentinel\n",
        encoding="utf-8",
    )
    docs = tmp_path / "EVALUATION.md"
    publish(summary, docs_path=docs, readme_path=readme)
    first_docs = docs.read_text(encoding="utf-8")
    first_readme = readme.read_text(encoding="utf-8")
    assert first_docs == render_summary_md(summary)
    assert "old numbers" not in first_readme
    assert first_readme.startswith("before\n")
    assert "after sentinel" in first_readme
    assert "offline" in first_docs.lower()
    publish(summary, docs_path=docs, readme_path=readme)
    assert docs.read_bytes() == first_docs.encode("utf-8")
    assert readme.read_text(encoding="utf-8") == first_readme

    bare = tmp_path / "bare.md"
    bare.write_text("no markers\n", encoding="utf-8")
    publish(summary, docs_path=tmp_path / "other.md", readme_path=bare)
    assert bare.read_text(encoding="utf-8") == "no markers\n"
