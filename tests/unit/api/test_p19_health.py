"""P19-T5: the direct-NVIDIA deep model defaults to the entitled Nemotron model."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import app

pytestmark = pytest.mark.p19


def test_p19_t5_health_names_entitled_deep_model(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)  # no .env here, so the default applies
    monkeypatch.setenv("SAMPLE_MODE", "true")
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    monkeypatch.delenv("NVIDIA_MODEL_DEEP", raising=False)
    from app.config import get_settings
    from app.llm.resolve import reset_cache

    get_settings.cache_clear()
    reset_cache()
    resp = TestClient(app).get("/health")
    assert resp.status_code == 200
    assert resp.json()["provider"]["nvidia"]["deep_model"] == "nvidia/nemotron-3.5-super-vl-120b-a12b"
    assert "nemotron-3-super-120b-a12b" not in resp.text
    get_settings.cache_clear()
