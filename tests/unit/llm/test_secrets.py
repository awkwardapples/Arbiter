"""P2-T18: no credential reaches traces, logs or exception text, for every provider and path."""

from __future__ import annotations

import logging
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from app.errors import ArbiterError
from app.llm import generator, status
from app.tracing import Tracer

pytestmark = pytest.mark.p2b

METERLESS_BASE = "http://127.0.0.1:8088/v1"
NVIDIA_BASE = "https://integrate.api.nvidia.com/v1"
CHAT = "/chat/" + "completions"
MODELS_OK = {"object": "list", "data": [{"id": "meterless/fast"}, {"id": "meterless/deep"}]}


def _ok(_tok: str) -> Any:
    return httpx.Response(
        200,
        json={
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "fine"}}],
            "usage": {"prompt_tokens": 2, "completion_tokens": 1},
        },
    )


def _echo_500(tok: str) -> Any:
    return httpx.Response(
        500, json={"error": {"message": f"upstream rejected header Authorization: Bearer {tok}", "type": "x"}}
    )


def _echo_401(tok: str) -> Any:
    return httpx.Response(401, json={"error": {"message": f"invalid token {tok}"}})


def _timeout(_tok: str) -> Any:
    return httpx.ReadTimeout("read timed out")


def _refused(_tok: str) -> Any:
    return httpx.ConnectError("Connection refused")


SCENARIOS: dict[str, Callable[[str], Any]] = {
    "success": _ok,
    "http500_echo": _echo_500,
    "http401_echo": _echo_401,
    "timeout": _timeout,
    "connect_error": _refused,
}


def _mock(route: Any, outcome: Any) -> None:
    if isinstance(outcome, Exception):
        route.mock(side_effect=outcome)
    else:
        route.mock(return_value=outcome)


def _run_generate(tmp_path: Path) -> tuple[str, BaseException | None, Any]:
    tracer = Tracer("run-p2b-secrets", mode={"data": "duckdb", "llm": "auto"}, log_dir=str(tmp_path / "logs"))
    err: BaseException | None = None
    result = None
    try:
        result = generator.generate(
            "hello PROMPT-SENTINEL", purpose="extract", tracer=tracer, agent_name="T18"
        )
    except ArbiterError as exc:
        err = exc
    finally:
        tracer.close()
    trace_text = "\n".join(p.read_text(encoding="utf-8") for p in (tmp_path / "logs").glob("*.jsonl"))
    return trace_text, err, result


def _assert_clean(secrets: list[str], *texts: str) -> None:
    for text in texts:
        for secret in secrets:
            assert secret not in text


def _exc_texts(err: BaseException | None) -> list[str]:
    if err is None:
        return []
    return [str(err), repr(err), "".join(traceback.format_exception(err))]


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_p2_t18_meterless_paths(
    scenario: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    mtok: str,
    nkey: str,
) -> None:
    caplog.set_level(logging.DEBUG)
    monkeypatch.setenv("LLM_PROVIDER", "meterless")
    monkeypatch.setenv("METERLESS_BASE_URL", METERLESS_BASE)
    monkeypatch.setenv("METERLESS_RUNTIME_TOKEN", mtok)
    monkeypatch.setenv("NVIDIA_API_KEY", nkey)
    with respx.mock(assert_all_called=False) as m:
        m.get(f"{METERLESS_BASE}/models").mock(return_value=httpx.Response(200, json=MODELS_OK))
        _mock(m.post(f"{METERLESS_BASE}{CHAT}"), SCENARIOS[scenario](mtok))
        trace_text, err, result = _run_generate(tmp_path)
        st = status.check()
    assert (err is None) == (scenario == "success")
    if result is not None:
        assert result.provider == "meterless"
    _assert_clean([mtok, nkey], trace_text, caplog.text, str(st), *_exc_texts(err))
    assert "PROMPT-SENTINEL" not in trace_text


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_p2_t18_nvidia_paths(
    scenario: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    mtok: str,
    nkey: str,
) -> None:
    caplog.set_level(logging.DEBUG)
    monkeypatch.setenv("LLM_PROVIDER", "nvidia")
    monkeypatch.setenv("METERLESS_BASE_URL", METERLESS_BASE)
    monkeypatch.setenv("METERLESS_RUNTIME_TOKEN", mtok)
    monkeypatch.setenv("NVIDIA_API_KEY", nkey)
    with respx.mock(assert_all_called=False) as m:
        m.get(f"{METERLESS_BASE}/models").mock(return_value=httpx.Response(401, json={"error": mtok}))
        _mock(m.post(f"{NVIDIA_BASE}{CHAT}"), SCENARIOS[scenario](nkey))
        trace_text, err, result = _run_generate(tmp_path)
        st = status.check()
    assert (err is None) == (scenario == "success")
    if result is not None:
        assert result.provider == "nvidia"
    _assert_clean([mtok, nkey], trace_text, caplog.text, str(st), *_exc_texts(err))


def test_p2_t18_offline_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    mtok: str,
    nkey: str,
) -> None:
    caplog.set_level(logging.DEBUG)
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    monkeypatch.setenv("METERLESS_RUNTIME_TOKEN", mtok)
    monkeypatch.setenv("NVIDIA_API_KEY", nkey)
    with respx.mock(assert_all_called=False):
        trace_text, err, _ = _run_generate(tmp_path)
    assert err is not None and err.type == "OfflineProvider"
    _assert_clean([mtok, nkey], trace_text, caplog.text, *_exc_texts(err))


def test_p2_t18_discovery_error_detail_is_clean(mtok: str) -> None:
    from app.llm.providers.meterless import discover

    with respx.mock() as m:
        m.get(f"{METERLESS_BASE}/models").mock(
            return_value=httpx.Response(403, json={"error": f"bad bearer {mtok}"})
        )
        result = discover(METERLESS_BASE, mtok, "arbiter")
    assert result.status == "unauthorized"
    assert mtok not in result.model_dump_json()
