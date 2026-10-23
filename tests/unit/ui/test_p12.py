"""P12 evaluation layout and sidebar logo."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.ui.conftest import FakeArbiterClient
from tests.unit.ui.test_pages_smoke import _run_page

pytestmark = pytest.mark.p5a

ROOT = Path(__file__).resolve().parents[3]
LOGO = ROOT / "docs" / "img" / "arbiter_logo.png"
SUMMARY = ROOT / "eval/results/20261022T080517661769Z/summary.md"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_PAGE_CAPTION = (
    "Two views: the offline benchmark measures the decision pipeline on a fixed labelled set. "
    "The live section shows this instance's activity."
)
_OFFLINE_CAPTION = "Fixed labelled set, no live services. Method: docs/EVALUATION.md."
_LIVE_CAPTION = "Cases, backend, and provider on this API."
_README_LOGO = """<p align="center">
  <img src="docs/img/arbiter_logo.png" alt="Arbiter" width="360">
</p>"""


def _text(elements) -> str:
    return " ".join(getattr(item, "value", "") or "" for item in elements)


def _evaluation(fake_client: FakeArbiterClient, monkeypatch: pytest.MonkeyPatch):
    import ui.screens as screens

    monkeypatch.setattr(screens, "EVAL_SUMMARY_PATH", SUMMARY, raising=False)
    fake_client.eval_latest_404 = True
    at = _run_page("Evaluation", "pages/evaluation.py", client=fake_client)
    assert not at.exception
    return at


def test_p12_strip_leading_h1() -> None:
    """P12-T1: only a leading run of '# ' lines is removed."""
    from ui.components import strip_leading_h1

    assert strip_leading_h1("# Evaluation\n\nSynthetic data") == "\nSynthetic data"
    body = "Synthetic data\n\n# Later heading\n"
    assert strip_leading_h1(body) == body
    assert strip_leading_h1("## Not an h1\n") == "## Not an h1\n"
    assert strip_leading_h1("") == ""
    assert strip_leading_h1("# One\n# Two\nKept\n") == "Kept\n"


def test_p12_eval_title_once(fake_client: FakeArbiterClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """P12-T2: the page title is the only Evaluation heading."""
    at = _evaluation(fake_client, monkeypatch)
    assert [item.value for item in at.title] == ["Evaluation"]
    assert "# Evaluation" not in _text(at.markdown)
    assert not list(at.header)


def test_p12_eval_sections(fake_client: FakeArbiterClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """P12-T3: one subheader level, with the approved captions."""
    at = _evaluation(fake_client, monkeypatch)
    assert [item.value for item in at.subheader] == [
        "Offline benchmark",
        "Live runs on this instance",
    ]
    captions = _text(at.caption)
    assert _PAGE_CAPTION in captions
    assert _OFFLINE_CAPTION in captions
    assert _LIVE_CAPTION in captions
    assert "Synthetic data" in _text(at.markdown)


def test_p12_live_metrics_row(fake_client: FakeArbiterClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """P12-T4: four metrics in one row, and no Cases link."""
    at = _evaluation(fake_client, monkeypatch)
    assert [(item.label, item.value) for item in at.metric] == [
        ("Cases", "1"),
        ("Data backend", "duckdb"),
        ("LLM provider", "offline"),
        ("Most recent", "2026-10-22T07:52:41.907214+00:00"),
    ]
    assert not any(item.value == "Cases" for item in at.subheader)
    assert not any(item.value == "Cases" for item in at.page_link)


def test_p12_logo_asset() -> None:
    """P12-T5: the committed logo is a PNG and still has palette transparency."""
    data = LOGO.read_bytes()
    assert data.startswith(_PNG_MAGIC)
    assert b"tRNS" in data


def test_p12_logo_call_site() -> None:
    """P12-T6: the logo is installed once, before navigation, on the app entrypoint."""
    from ui.app import _streamlit_supports_logo

    source = (ROOT / "ui" / "app.py").read_text(encoding="utf-8")
    logo_at = source.index("arbiter_logo.png")
    nav_at = source.index("st.navigation")
    assert logo_at < nav_at
    assert _streamlit_supports_logo() is True
    # Streamlit 1.66 size="large" is a 32px cap. The wordmark is the sidebar image.
    assert "st.sidebar.image" in source
    assert "width=200" in source
    assert "st.logo(" not in source


def test_p12_readme_logo() -> None:
    """P12-T7: GitHub landing order is H1, badges, centered logo, opening paragraph."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    h1 = readme.index("# Arbiter")
    badge = readme.index("Track: Reasoning Architecture")
    logo = readme.index(_README_LOGO)
    paragraph = readme.index("Auditable reasoning for third-party vendor onboarding")
    assert h1 < badge < logo < paragraph
