"""P15: `METERLESS_NO_THINK` prepends a `/no_think` system message on Nightshift calls and records it."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from app.config import Settings
from app.llm.providers.meterless import MeterlessProvider

pytestmark = pytest.mark.p15

BASE = "http://127.0.0.1:8088/v1"
MSGS = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]


def _provider(token: str, *, no_think: bool) -> MeterlessProvider:
    return MeterlessProvider(
        base_url=BASE,
        token=token,
        app_id="arbiter",
        model_fast="meterless/fast",
        model_deep="meterless/deep",
        no_think=no_think,
    )


def _call(provider: MeterlessProvider, body: dict[str, Any]) -> tuple[list[dict[str, str]], dict[str, str]]:
    with respx.mock(assert_all_called=True) as m:
        route = m.post(f"{BASE}/chat/completions").mock(return_value=httpx.Response(200, json=body))
        result = provider.chat(MSGS, model="meterless/deep", temperature=0.0, max_tokens=2048)
    return json.loads(route.calls.last.request.content)["messages"], result.provider_meta


def test_p15_no_think_off_by_default(mtok: str, chat_fixture: dict[str, Any]) -> None:
    assert Settings(_env_file=None).METERLESS_NO_THINK is False
    sent, meta = _call(_provider(mtok, no_think=False), chat_fixture["deep"]["body"])
    assert sent == MSGS
    assert "no_think" not in meta


def test_p15_no_think_prepends_system_message(mtok: str, chat_fixture: dict[str, Any]) -> None:
    sent, meta = _call(_provider(mtok, no_think=True), chat_fixture["deep"]["body"])
    assert sent == [{"role": "system", "content": "/no_think"}, *MSGS]
    assert meta["no_think"] == "true"
    assert meta["receipt_id"] == chat_fixture["deep"]["body"]["meterless"]["receipt_id"]


def test_p15_no_think_from_settings(mtok: str) -> None:
    on = Settings(_env_file=None, METERLESS_RUNTIME_TOKEN=mtok, METERLESS_NO_THINK="1")
    assert MeterlessProvider.from_settings(on, base_url=BASE).no_think is True
    off = Settings(_env_file=None, METERLESS_RUNTIME_TOKEN=mtok)
    assert MeterlessProvider.from_settings(off, base_url=BASE).no_think is False
