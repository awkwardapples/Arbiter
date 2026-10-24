"""P19-T3: GET /eval/latest serves the published live and offline summaries."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import app

pytestmark = pytest.mark.p19

ROOT = Path(__file__).resolve().parents[3]


def test_p19_t3_eval_latest_live_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    resp = TestClient(app).get("/eval/latest")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    live = body["live"]
    assert live["generated_at"].startswith("2026-10-24")
    assert live["offline"] is False
    assert sorted(live["systems"]) == ["arbiter", "arbiter_offline", "baseline"]
    assert live["systems"]["arbiter"]["accuracy"]["n"] == 5
    assert body["offline"] is not None
    assert "Synthetic data" in body["live_markdown"]
    assert "Synthetic data" in body["offline_markdown"]


def test_p19_t3_eval_latest_404_when_unpublished(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    resp = TestClient(app, raise_server_exceptions=False).get("/eval/latest")
    assert resp.status_code == 404
    assert resp.json()["error"]["type"]
