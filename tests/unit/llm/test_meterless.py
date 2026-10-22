"""P2-T12..P2-T16: Meterless Nightshift request shape, discovery, token rules, timeouts."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
import pytest
import respx

from app.config import Settings
from app.errors import ConfigError
from app.llm.providers import meterless
from app.llm.providers.meterless import MeterlessProvider, autodetect, discover, normalise_base_url
from app.llm.providers.nvidia import NvidiaProvider
from tests.unit.llm.conftest import RecordingTransport

pytestmark = pytest.mark.p2b

BASE = "http://127.0.0.1:8088/v1"
MSGS = [{"role": "user", "content": "hi"}]


def _settings(**kw: Any) -> Settings:
    return Settings(_env_file=None, **kw)


def _chat_kw(provider: Any, route: str = "fast") -> dict[str, Any]:
    return {"model": provider.model_for(route), "temperature": 0.0, "max_tokens": 64}


# ── P2-T12 request shape ────────────────────────────────────────────────


def test_p2_t12_headers_on_models_without_scope(meterless_token: str, models_fixture: dict[str, Any]) -> None:
    with respx.mock(assert_all_called=True) as m:
        route = m.get(f"{BASE}/models").mock(return_value=httpx.Response(200, json=models_fixture["body"]))
        discover(BASE, meterless_token, "arbiter")
    req = route.calls.last.request
    assert req.headers["authorization"] == f"Bearer {meterless_token}"
    assert req.headers["meterless-app"] == "arbiter"
    assert "meterless-scope" not in req.headers


def test_p2_t12_headers_and_model_on_chat(meterless_token: str, chat_fixture: dict[str, Any]) -> None:
    provider = MeterlessProvider(
        base_url=BASE,
        token=meterless_token,
        app_id="arbiter-test",
        model_fast="meterless/custom-fast",
        model_deep="meterless/custom-deep",
    )
    captured = chat_fixture["deep"]
    with respx.mock(assert_all_called=True) as m:
        route = m.post(f"{BASE}/chat/completions").mock(
            return_value=httpx.Response(200, json=captured["body"])
        )
        result = provider.chat(MSGS, **_chat_kw(provider, "deep"))
    req = route.calls.last.request
    assert req.headers["authorization"] == f"Bearer {meterless_token}"
    assert req.headers["meterless-app"] == "arbiter-test"
    assert req.headers["meterless-scope"] == "user"
    body = json.loads(req.content)
    assert body["model"] == "meterless/custom-deep"
    assert body["messages"] == MSGS
    assert result.model == captured["body"]["model"]
    assert result.text == captured["body"]["choices"][0]["message"]["content"]
    assert result.tokens_in == captured["body"]["usage"]["prompt_tokens"]
    assert result.tokens_out == captured["body"]["usage"]["completion_tokens"]
    receipt = captured["body"]["meterless"]
    assert result.provider_meta["routed_model"] == receipt["routed_model"]
    assert result.provider_meta["requested_model"] == receipt["requested_model"]
    assert result.provider_meta["receipt_id"] == receipt["receipt_id"]


def test_p2_t12_model_ids_come_from_config(meterless_token: str) -> None:
    s = _settings(
        METERLESS_RUNTIME_TOKEN=meterless_token,
        METERLESS_MODEL_FAST="meterless/text.fast",
        METERLESS_MODEL_DEEP="meterless/text.deep",
    )
    provider = MeterlessProvider.from_settings(s, base_url=BASE)
    assert provider.model_for("fast") == "meterless/text.fast"
    assert provider.model_for("deep") == "meterless/text.deep"


@pytest.mark.parametrize(
    ("pasted", "expected"),
    [
        ("http://127.0.0.1:8088", BASE),
        ("http://127.0.0.1:8088/", BASE),
        ("http://127.0.0.1:8088/v1", BASE),
        ("http://127.0.0.1:8088/v1/", BASE),
        ("http://127.0.0.1:8088/v1/models", BASE),
        ("http://127.0.0.1:8088/v1/chat/completions", BASE),
        ("http://127.0.0.1:8088/healthz", BASE),
        ("  http://127.0.0.1:8088/v1  ", BASE),
        ("localhost:8090", "http://localhost:8090/v1"),
        ("http://[::1]:8787/v1/models", "http://[::1]:8787/v1"),
        ("https://nightshift.internal:9443/v1/", "https://nightshift.internal:9443/v1"),
    ],
)
def test_p2_t12_url_normalisation(pasted: str, expected: str) -> None:
    assert normalise_base_url(pasted) == expected


# ── P2-T13 discovery ────────────────────────────────────────────────────


def _discover_with(response: httpx.Response | Exception, token: str) -> Any:
    with respx.mock(assert_all_called=False) as m:
        healthz = m.get(url__regex=r".*/healthz.*").mock(return_value=httpx.Response(200, text="ok"))
        route = m.get(f"{BASE}/models")
        if isinstance(response, Exception):
            route.mock(side_effect=response)
        else:
            route.mock(return_value=response)
        result = discover(BASE, token, "arbiter")
        assert not healthz.called, "/healthz must never be used as proof"
    return result


def test_p2_t13_online_with_meterless_ids(meterless_token: str, models_fixture: dict[str, Any]) -> None:
    result = _discover_with(httpx.Response(200, json=models_fixture["body"]), meterless_token)
    assert result.status == "online"
    assert result.base_url == BASE
    assert "meterless/fast" in result.models_seen
    assert "meterless/deep" in result.models_seen


def test_p2_t13_minimal_meterless_fast_is_online(meterless_token: str) -> None:
    body = {"object": "list", "data": [{"id": "meterless/fast", "object": "model"}]}
    assert _discover_with(httpx.Response(200, json=body), meterless_token).status == "online"


def test_p2_t13_no_meterless_ids_is_offline(meterless_token: str) -> None:
    body = {"object": "list", "data": [{"id": "gpt-x"}, {"id": "nvidia/nemotron-3-nano-30b-a3b"}]}
    result = _discover_with(httpx.Response(200, json=body), meterless_token)
    assert result.status == "offline"
    assert result.models_seen == ["gpt-x", "nvidia/nemotron-3-nano-30b-a3b"]


@pytest.mark.parametrize("code", [401, 403])
def test_p2_t13_unauthorized(meterless_token: str, code: int) -> None:
    assert (
        _discover_with(httpx.Response(code, json={"error": "nope"}), meterless_token).status == "unauthorized"
    )


@pytest.mark.parametrize(
    "response",
    [
        httpx.ConnectError("Connection refused"),
        httpx.ConnectTimeout("timed out"),
        httpx.Response(500, text="boom"),
        httpx.Response(404, text="not here"),
        httpx.Response(200, text="<html>not json</html>"),
        httpx.Response(200, json={"unexpected": True}),
    ],
)
def test_p2_t13_everything_else_is_offline(meterless_token: str, response: Any) -> None:
    assert _discover_with(response, meterless_token).status == "offline"


def test_p2_t13_source_never_mentions_healthz_as_a_request() -> None:
    from pathlib import Path

    src = Path(meterless.__file__).read_text(encoding="utf-8")
    for line in src.splitlines():
        if "healthz" in line:
            assert "get(" not in line and "request(" not in line


# ── P2-T14 token rules ──────────────────────────────────────────────────


def test_p2_t14_rt_local_raises_config_error() -> None:
    s = _settings(METERLESS_RUNTIME_TOKEN="rt-local", LLM_PROVIDER="meterless")
    with pytest.raises(ConfigError) as exc_info:
        meterless.token_from(s)
    msg = exc_info.value.message
    assert "METERLESS_RUNTIME_TOKEN" in msg
    assert "Nightshift" in msg


def test_p2_t14_rt_local_explicit_meterless_resolve_raises() -> None:
    from app.llm.resolve import resolve

    with respx.mock(assert_all_mocked=True, assert_all_called=False), pytest.raises(ConfigError):
        resolve(_settings(METERLESS_RUNTIME_TOKEN="rt-local", LLM_PROVIDER="meterless"))


def test_p2_t14_rt_local_under_auto_is_skipped(caplog: pytest.LogCaptureFixture) -> None:
    from app.llm.resolve import resolve

    caplog.set_level(logging.WARNING)
    s = _settings(METERLESS_RUNTIME_TOKEN="rt-local", LLM_PROVIDER="auto", METERLESS_BASE_URL=BASE)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as m:
        provider = resolve(s)
        assert m.calls.call_count == 0, "no request with the placeholder token"
    assert provider.name == "offline"
    assert meterless.discover_from_settings(s).status == "config_error"
    assert any("rt-local" in r.getMessage() for r in caplog.records)


def test_p2_t14_missing_token_is_offline_without_request() -> None:
    from app.llm.resolve import resolve

    s = _settings(LLM_PROVIDER="auto", METERLESS_BASE_URL=BASE)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as m:
        result = meterless.discover_from_settings(s)
        provider = resolve(s)
        assert m.calls.call_count == 0
    assert result.status == "offline"
    assert "METERLESS_RUNTIME_TOKEN" in result.detail
    assert provider.name == "offline"


# ── P2-T16 timeouts and auto-detect ─────────────────────────────────────


def _ok_models(_req: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"object": "list", "data": [{"id": "meterless/fast"}]})


def test_p2_t16_meterless_chat_uses_180s(meterless_token: str, chat_fixture: dict[str, Any]) -> None:
    rt = RecordingTransport(lambda _r: httpx.Response(200, json=chat_fixture["fast"]["body"]))
    provider = MeterlessProvider(
        base_url=BASE,
        token=meterless_token,
        app_id="arbiter",
        model_fast="meterless/fast",
        model_deep="meterless/deep",
        transport=rt,
    )
    provider.chat(MSGS, **_chat_kw(provider))
    provider.chat(MSGS, **_chat_kw(provider), timeout=5.0)
    assert [t["read"] for t in rt.timeouts] == [180.0, 180.0], (
        "short overrides must not shorten Meterless calls"
    )


def test_p2_t16_discovery_connect_timeout_2s(meterless_token: str) -> None:
    rt = RecordingTransport(_ok_models)
    discover(BASE, meterless_token, "arbiter", transport=rt)
    assert rt.timeouts[0]["connect"] == 2.0
    assert rt.timeouts[0]["read"] == 180.0


def test_p2_t16_nvidia_uses_90s(nvidia_key: str) -> None:
    body = {
        "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}}],
        "usage": {"prompt_tokens": 3, "completion_tokens": 1},
    }
    rt = RecordingTransport(lambda _r: httpx.Response(200, json=body))
    provider = NvidiaProvider(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=nvidia_key,
        model_fast="nvidia/nemotron-3.5-lightning-30b-a3b",
        model_deep="nvidia/nemotron-3-super-120b-a12b",
        transport=rt,
    )
    result = provider.chat(MSGS, **_chat_kw(provider, "deep"))
    assert rt.timeouts[0]["read"] == 90.0
    assert json.loads(rt.requests[0].content)["model"] == "nvidia/nemotron-3-super-120b-a12b"
    assert rt.requests[0].headers["authorization"] == f"Bearer {nvidia_key}"
    assert result.text == "ok" and result.tokens_out == 1


@pytest.mark.parametrize("suffix", ["/v1", "/v1/models", "/v1/chat/completions", "/healthz"])
def test_p2_t16_four_pasted_suffixes(suffix: str) -> None:
    assert normalise_base_url("http://localhost:8088" + suffix) == "http://localhost:8088/v1"


EXPECTED_PAIRS = [
    f"http://{h}:{p}/v1/models"
    for h in ("127.0.0.1", "localhost", "[::1]")
    for p in (8088, 8090, 8787, 11434)
]


def test_p2_t16_autodetect_probes_all_twelve(meterless_token: str) -> None:
    def refuse(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused", request=req)

    rt = RecordingTransport(refuse)
    result = autodetect(meterless_token, "arbiter", transport=rt)
    assert result.status == "offline"
    assert rt.urls == EXPECTED_PAIRS
    assert all(t["connect"] == 2.0 for t in rt.timeouts)


def test_p2_t16_autodetect_stops_at_first_online(meterless_token: str) -> None:
    fifth = EXPECTED_PAIRS[4]

    def handler(req: httpx.Request) -> httpx.Response:
        if str(req.url) == fifth:
            return _ok_models(req)
        raise httpx.ConnectError("Connection refused", request=req)

    rt = RecordingTransport(handler)
    result = autodetect(meterless_token, "arbiter", transport=rt)
    assert result.status == "online"
    assert rt.urls == EXPECTED_PAIRS[:5]
    assert result.base_url == fifth.removesuffix("/models")


def test_p2_t16_autodetect_used_when_base_url_unset(
    monkeypatch: pytest.MonkeyPatch, meterless_token: str
) -> None:
    seen: list[str] = []

    def fake_autodetect(token: str, app_id: str, **_kw: Any) -> Any:
        seen.append(app_id)
        return meterless.DiscoveryResult(status="offline", detail="none found")

    monkeypatch.setattr(meterless, "autodetect", fake_autodetect)
    meterless.discover_from_settings(_settings(METERLESS_RUNTIME_TOKEN=meterless_token))
    assert seen == ["arbiter"]
