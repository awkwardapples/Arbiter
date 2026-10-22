"""P5-T11 / P5-T14: Streamlit page smoke tests with FakeArbiterClient."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from tests.unit.ui.conftest import FakeArbiterClient

pytestmark = pytest.mark.p5a

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "ui" / "app.py"

PAGES: list[tuple[str, str]] = [
    ("New assessment", "pages/new_assessment.py"),
    ("Queue", "pages/queue.py"),
    ("Case", "pages/case.py"),
    ("Review", "pages/review.py"),
    ("Memory", "pages/memory.py"),
    ("Audit", "pages/audit.py"),
    ("Evaluation", "pages/evaluation.py"),
]


def _run_page(title: str, page_file: str, *, client: FakeArbiterClient) -> AppTest:
    at = AppTest.from_file(str(APP))
    at.session_state["api_client"] = client
    at.run()
    if page_file != "pages/new_assessment.py":
        at.switch_page(page_file).run()
    if title == "Case":
        at.query_params["case_id"] = client.case_detail["case_id"]
        at.run()
    return at


@pytest.mark.parametrize(("title", "page_file"), PAGES)
def test_p5_t11_pages_smoke(title: str, page_file: str, fake_client: FakeArbiterClient) -> None:
    """P5-T11: each nav page runs without exception."""
    at = _run_page(title, page_file, client=fake_client)
    assert not at.exception


def test_p5_t11_case_page_shows_outcome_text(fake_client: FakeArbiterClient) -> None:
    """P5-T11: case page surfaces outcome as visible text."""
    at = _run_page("Case", "pages/case.py", client=fake_client)
    outcome = fake_client.case_detail["record"]["outcome"]
    blob = " ".join(getattr(m, "value", "") or "" for m in at.markdown)
    assert outcome in blob


def test_p5_t14_eval_not_published_on_404(fake_client: FakeArbiterClient) -> None:
    """P5-T14: Evaluation page shows fallback when /eval/latest is 404."""
    fake_client.eval_latest_404 = True
    at = _run_page("Evaluation", "pages/evaluation.py", client=fake_client)
    assert not at.exception
    text = " ".join(getattr(m, "value", "") or "" for m in at.info)
    assert "not published yet" in text.lower()
