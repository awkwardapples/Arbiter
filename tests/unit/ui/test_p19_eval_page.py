"""P19-T3: the Streamlit Evaluation page shows the live table first, from /eval/latest."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.unit.ui.conftest import FakeArbiterClient
from tests.unit.ui.test_pages_smoke import _run_page

pytestmark = pytest.mark.p19

ROOT = Path(__file__).resolve().parents[3]


def _published(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """The real endpoint payload, read through the API from the committed results."""
    from app.api.main import app

    monkeypatch.chdir(ROOT)
    resp = TestClient(app).get("/eval/latest")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _text(elements) -> str:
    return " ".join(getattr(item, "value", "") or "" for item in elements)


def test_p19_t3_eval_page_live_first(fake_client: FakeArbiterClient, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _published(monkeypatch)
    fake_client.eval_latest = lambda: payload  # type: ignore[method-assign]
    at = _run_page("Evaluation", "pages/evaluation.py", client=fake_client)
    assert not at.exception
    subheaders = [item.value for item in at.subheader]
    assert subheaders.index("Live evaluation") < subheaders.index("Offline benchmark")
    blob = _text(at.markdown)
    # P20 (approved): the arbiter row of the latest committed live summary, not one run's figures.
    accuracy = payload["live"]["systems"]["arbiter"]["accuracy"]
    assert f"| arbiter | {accuracy['rate']:.3f} ({accuracy['correct']}/{accuracy['n']}) |" in blob
    assert "not published yet" not in _text(at.info).lower()


def test_p19_t3_eval_page_404(fake_client: FakeArbiterClient) -> None:
    fake_client.eval_latest_404 = True
    at = _run_page("Evaluation", "pages/evaluation.py", client=fake_client)
    assert not at.exception
    assert "Evaluation results are not published yet." in _text(at.info)


def test_p19_t3_no_hard_coded_summary_path() -> None:
    import ui.screens as screens

    assert not hasattr(screens, "EVAL_SUMMARY_PATH")
    assert "eval/results/" not in inspect.getsource(screens)
