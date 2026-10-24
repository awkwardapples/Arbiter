"""P18A-T12, T15: model_request, contradiction_found and PolicyEngine decide events, from code that runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.api.main import app
from app.config import get_settings
from app.orchestrator import RunOptions, run
from scripts.check_trace import validate_file
from tests.e2e.support import EXAMPLES, load_example, offline_env, trace

pytestmark = pytest.mark.p18a
__all__ = ["offline_env"]

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
BASE = "http://127.0.0.1:8088/v1"


def _fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _fake_token() -> str:
    # Assembled at runtime so the secret scanner sees no literal credential.
    return "mlt-" + "".join(chr(ord("a") + (i * 7) % 26) for i in range(32))


def _assert_new_events(events: list[dict[str, Any]]) -> None:
    found = [e for e in events if e["action"] == "contradiction_found"]
    assert len(found) == 1
    item = found[0]
    assert item["agent_name"] == "EvaluatorAgent"
    assert item["status"] == "success"
    assert item["target_agent"] is None
    assert item["input_summary"].startswith("key=residency.regions control=")
    out = item["output_summary"]
    assert out.startswith("vendor=EU record=US system=")
    assert "record_key=" in out

    decides = [e for e in events if e["agent_name"] == "PolicyEngine" and e["action"] == "decide"]
    assert decides
    assert any(e["output_summary"].startswith("outcome=ESCALATE tier=") for e in decides)
    for event in decides:
        assert event["input_summary"].startswith("facts=")
        assert " contradictions=" in event["input_summary"] and " precedents=" in event["input_summary"]
        assert " failing=" in event["output_summary"] and " unknown=" in event["output_summary"]


def test_p18a_t12_offline_contradiction_and_decide(offline_env: Path) -> None:
    """P18A-T12 (offline): one residency contradiction EU vs US; a decide event reads ESCALATE."""
    del offline_env
    response = run(load_example("example_2.json"), options=RunOptions())
    assert response.output.decision == "ESCALATE"
    events = trace(response.log_file)
    _assert_new_events(events)
    assert not [e for e in events if e["action"] == "model_request"]
    redecide = next(i for i, e in enumerate(events) if e["action"] == "redecide")
    assert events[redecide - 1]["agent_name"] == "PolicyEngine"
    assert events[redecide - 1]["action"] == "decide"


def test_p18a_t12_model_request_precedes_every_model_call(
    offline_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P18A-T12 (mocked Nightshift): each model_call follows a model_request (same agent, purpose)."""
    del offline_env
    monkeypatch.setenv("LLM_PROVIDER", "meterless")
    monkeypatch.setenv("METERLESS_BASE_URL", BASE)
    monkeypatch.setenv("METERLESS_RUNTIME_TOKEN", _fake_token())
    monkeypatch.setenv("METERLESS_MODEL_FAST", "meterless/fast")
    monkeypatch.setenv("METERLESS_MODEL_DEEP", "meterless/deep")
    get_settings.cache_clear()
    models = _fixture("meterless_models.json")
    chat = _fixture("meterless_chat.json")

    def handler(request: httpx.Request) -> httpx.Response:
        lane = "deep" if json.loads(request.content)["model"].endswith("deep") else "fast"
        return httpx.Response(200, json=chat[lane]["body"])

    with respx.mock() as mock:
        mock.get(f"{BASE}/models").mock(return_value=httpx.Response(200, json=models["body"]))
        mock.post(f"{BASE}/chat/completions").mock(side_effect=handler)
        response = run(load_example("example_2.json"), options=RunOptions())

    events = trace(response.log_file)
    calls = [e for e in events if e["action"] == "model_call"]
    assert calls, "the mocked provider was never called"
    requests = [e for e in events if e["action"] == "model_request"]
    for evt in requests:
        assert evt["model"] is None
        assert evt["provider"] == "meterless"
        assert evt["output_summary"] == "sent to meterless"
        assert evt["input_summary"].startswith(f"purpose={evt['purpose']} route={evt['route']} attempt=")
    for agent in {e["agent_name"] for e in calls}:
        model_events = {"model_request", "model_call"}
        mine = [e for e in events if e["agent_name"] == agent and e["action"] in model_events]
        for i, evt in enumerate(mine):
            if evt["action"] != "model_call":
                continue
            assert i > 0, f"{agent}: model_call with no model_request before it"
            before = mine[i - 1]
            assert before["action"] == "model_request", f"{agent}: {before['action']} before model_call"
            assert before["purpose"] == evt["purpose"]
            assert before["route"] == evt["route"]
    assert len(requests) == len(calls)


def test_p18a_t15_check_trace_still_passes(offline_env: Path) -> None:
    """P18A-T15: a new sample-mode trace with the new events passes check_trace --require-collaboration."""
    body = json.loads((EXAMPLES / "example_2.json").read_text(encoding="utf-8"))
    response = TestClient(app).post("/run", json=body)
    assert response.status_code == 200
    path = offline_env / response.json()["log_file"]
    events = trace(str(path))
    _assert_new_events(events)
    assert validate_file(path, require_collaboration=True, require_live=False) == []
