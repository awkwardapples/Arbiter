"""P3-T11: POST /run accepts the bare and wrapped shapes and returns structured errors."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.schemas.api import RunResponse
from tests.e2e.support import offline_env

pytestmark = pytest.mark.p3
__all__ = ["offline_env"]


def _client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def test_p3_t11_bare_shape(offline_env: Path) -> None:
    resp = _client().post("/run", json={"vendor_id": "VND-0003"})
    assert resp.status_code == 200, resp.text
    body = RunResponse.model_validate(resp.json())
    assert body.output is not None and body.output.case_id
    assert body.execution_time_seconds > 0
    assert (offline_env / body.log_file).is_file()
    assert {a.name for a in body.agents} >= {"PlannerAgent", "EvidenceAgent", "EvaluatorAgent"}


def test_p3_t11_wrapped_shape_with_sample_mode_and_empty_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    for var in (
        "SAMPLE_MODE",
        "LLM_PROVIDER",
        "ARBITER_MEMORY",
        "METERLESS_BASE_URL",
        "NVIDIA_API_KEY",
        "MODEL_API_KEY",
        "ZETARIS_API_KEY",
        "METERLESS_RUNTIME_TOKEN",
        "ARBITER_SIGNING_KEY",
    ):
        monkeypatch.delenv(var, raising=False)
    payload = {"input": {"vendor_id": "VND-0019"}, "options": {"sample_mode": True, "llm": "offline"}}
    resp = _client().post("/run", json=payload)
    assert resp.status_code == 200, resp.text
    body = RunResponse.model_validate(resp.json())
    assert body.mode["data"] == "duckdb"
    assert body.output.decision == "DECLINE"
    assert body.execution_time_seconds > 0
    assert (tmp_path / body.log_file).is_file()


@pytest.mark.parametrize(
    "payload",
    [
        {"vendor_id": 123},
        {},
        {"vendor_id": "VND-0003", "submission": {"legal_name": "x"}},
        {"input": {"vendor_id": "VND-0003"}, "options": {"llm": "gpt-9"}},
    ],
)
def test_p3_t11_bad_body_is_structured_400(payload: dict, offline_env: Path) -> None:
    resp = _client().post("/run", json=payload)
    assert resp.status_code == 400
    body = resp.json()
    assert body["status"] == "error"
    assert body["error"]["type"] == "ValidationFailed"
    assert "Traceback" not in resp.text
