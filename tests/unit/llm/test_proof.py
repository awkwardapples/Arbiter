"""P15-T1: `run.py llm proof` against a mocked Nightshift: fields, no secrets, clear failures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from app.config import get_settings

pytestmark = pytest.mark.p15

BASE = "http://127.0.0.1:8088/v1"
_LANE_FIELDS = (
    "route",
    "sent_model",
    "requested_model",
    "response_model",
    "routed_model",
    "provider_model",
    "winning_route_model",
    "mode_coerced",
    "requested_mode",
    "routed_mode",
    "receipt_id",
    "response_id",
    "latency_ms",
    "tokens_in",
    "tokens_out",
    "receipt",
)


@pytest.fixture
def nightshift_env(monkeypatch: pytest.MonkeyPatch, mtok: str) -> str:
    monkeypatch.setenv("LLM_PROVIDER", "meterless")
    monkeypatch.setenv("METERLESS_BASE_URL", BASE)
    monkeypatch.setenv("METERLESS_RUNTIME_TOKEN", mtok)
    monkeypatch.setenv("METERLESS_MODEL_FAST", "meterless/fast")
    monkeypatch.setenv("METERLESS_MODEL_DEEP", "meterless/deep")
    get_settings.cache_clear()
    yield mtok
    get_settings.cache_clear()


def _main(argv: list[str]) -> int:
    from run import main

    try:
        return int(main(argv) or 0)
    except SystemExit as exc:
        return int(exc.code or 0)


def _chat_router(chat_fixture: dict[str, Any]):
    def handler(request: httpx.Request) -> httpx.Response:
        sent = json.loads(request.content)["model"]
        lane = "deep" if sent.endswith("deep") else "fast"
        return httpx.Response(200, json=chat_fixture[lane]["body"])

    return handler


def test_p15_t1_proof_writes_every_field(
    nightshift_env: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    models_fixture: dict[str, Any],
    chat_fixture: dict[str, Any],
) -> None:
    out = tmp_path / "proof.json"
    with respx.mock(assert_all_called=True) as m:
        m.get(f"{BASE}/models").mock(return_value=httpx.Response(200, json=models_fixture["body"]))
        chat = m.post(f"{BASE}/chat/completions").mock(side_effect=_chat_router(chat_fixture))
        code = _main(["llm", "proof", "--out", str(out)])
    printed = capsys.readouterr().out
    assert code == 0, printed
    assert chat.call_count == 2
    sent = sorted(json.loads(call.request.content)["model"] for call in chat.calls)
    assert sent == ["meterless/deep", "meterless/fast"]

    doc = json.loads(out.read_text(encoding="utf-8"))
    assert set(doc) >= {"timestamp", "base_url", "fast", "deep", "deviations", "human_observations"}
    assert doc["human_observations"] == "docs/evidence/nightshift_deviations.md"
    for lane in ("fast", "deep"):
        block = doc[lane]
        for field in _LANE_FIELDS:
            assert field in block, (lane, field)
        body = chat_fixture[lane]["body"]
        assert block["route"] == lane
        assert block["sent_model"] == f"meterless/{lane}"
        assert block["response_model"] == body["model"]
        assert block["receipt_id"] == body["meterless"]["receipt_id"]
        assert block["routed_model"] == body["meterless"]["routed_model"]
        assert block["winning_route_model"] == body["meterless"]["winning_route"]["model"]
        assert block["mode_coerced"] is True
        assert block["tokens_in"] == body["usage"]["prompt_tokens"]
        assert block["receipt"]["receipt_id"] == block["receipt_id"]

    # The fixture coerced both lanes to auto and served the same model, so the derived
    # deviations quote those receipts. Nothing in this list is pre-written.
    kinds = {item["kind"] for item in doc["deviations"]}
    assert {"mode_coerced", "same_model_both_lanes"} <= kinds
    same = next(item for item in doc["deviations"] if item["kind"] == "same_model_both_lanes")
    assert same["model"] == chat_fixture["fast"]["body"]["model"]
    assert set(same["receipt_ids"]) == {doc["fast"]["receipt_id"], doc["deep"]["receipt_id"]}

    for text in (out.read_text(encoding="utf-8"), printed):
        assert nightshift_env not in text
        assert "authorization" not in text.lower()
        assert "bearer" not in text.lower()
    assert "fast" in printed and "deep" in printed and doc["fast"]["receipt_id"] in printed


def test_p15_t1_proof_is_idempotent(
    nightshift_env: str, tmp_path: Path, models_fixture: dict[str, Any], chat_fixture: dict[str, Any]
) -> None:
    out = tmp_path / "proof.json"
    out.write_text("stale", encoding="utf-8")
    for _ in range(2):
        with respx.mock() as m:
            m.get(f"{BASE}/models").mock(return_value=httpx.Response(200, json=models_fixture["body"]))
            m.post(f"{BASE}/chat/completions").mock(side_effect=_chat_router(chat_fixture))
            assert _main(["llm", "proof", "--out", str(out)]) == 0
        assert json.loads(out.read_text(encoding="utf-8"))["fast"]["receipt_id"]


def test_p15_t1_no_deviation_when_lanes_differ(
    nightshift_env: str, tmp_path: Path, models_fixture: dict[str, Any], chat_fixture: dict[str, Any]
) -> None:
    deep = json.loads(json.dumps(chat_fixture["deep"]["body"]))
    deep["model"] = "nvidia/nemotron-3.5-super-vl-120b-a12b"
    deep["meterless"]["routed_model"] = deep["model"]
    deep["meterless"]["winning_route"]["model"] = deep["model"]
    for policy in (deep["meterless"]["receipt"]["app_policy"],):
        policy["mode_coerced"] = False
        policy["routed_mode"] = "deep"
    fast = json.loads(json.dumps(chat_fixture["fast"]["body"]))
    fast["meterless"]["receipt"]["app_policy"]["mode_coerced"] = False

    def handler(request: httpx.Request) -> httpx.Response:
        sent = json.loads(request.content)["model"]
        return httpx.Response(200, json=deep if sent.endswith("deep") else fast)

    out = tmp_path / "proof.json"
    with respx.mock() as m:
        m.get(f"{BASE}/models").mock(return_value=httpx.Response(200, json=models_fixture["body"]))
        m.post(f"{BASE}/chat/completions").mock(side_effect=handler)
        assert _main(["llm", "proof", "--out", str(out)]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["deviations"] == []


def test_p15_t1_unreachable_is_clear(
    nightshift_env: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "proof.json"
    with respx.mock() as m:
        m.get(f"{BASE}/models").mock(side_effect=httpx.ConnectError("refused"))
        code = _main(["llm", "proof", "--out", str(out)])
    printed = capsys.readouterr()
    assert code != 0
    assert "Nightshift not reachable" in printed.out + printed.err
    assert not out.exists()


def test_p15_t1_offline_provider_is_clear(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    get_settings.cache_clear()
    out = tmp_path / "proof.json"
    code = _main(["llm", "proof", "--out", str(out)])
    printed = capsys.readouterr()
    assert code != 0
    assert "Nightshift not reachable" in printed.out + printed.err
    assert not out.exists()
    get_settings.cache_clear()


def test_p15_t1_http_error_prints_status_and_body(
    nightshift_env: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    models_fixture: dict[str, Any],
) -> None:
    out = tmp_path / "proof.json"
    error = {"error": {"code": "function_not_found", "type": "upstream_error"}}
    with respx.mock() as m:
        m.get(f"{BASE}/models").mock(return_value=httpx.Response(200, json=models_fixture["body"]))
        m.post(f"{BASE}/chat/completions").mock(return_value=httpx.Response(404, json=error))
        code = _main(["llm", "proof", "--out", str(out)])
    printed = capsys.readouterr()
    text = printed.out + printed.err
    assert code != 0
    assert "HTTP 404" in text
    assert "function_not_found" in text
    assert nightshift_env not in text
    assert not out.exists()
