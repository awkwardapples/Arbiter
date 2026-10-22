"""P2-T15: provider resolution order, explicit overrides, offline, and the 60 s cache."""

from __future__ import annotations

from typing import Any

import pytest
from app.llm.providers.base import DiscoveryResult

from app.config import Settings
from app.errors import ConfigError, OfflineProvider
from app.llm import generator, resolve

pytestmark = pytest.mark.p2b

ONLINE = DiscoveryResult(
    status="online", base_url="http://127.0.0.1:8088/v1", models_seen=["meterless/fast"], detail="ok"
)
OFFLINE = DiscoveryResult(status="offline", detail="connection refused")


def _settings(**kw: Any) -> Settings:
    return Settings(_env_file=None, **kw)


class DiscoverySpy:
    def __init__(self, result: DiscoveryResult) -> None:
        self.result = result
        self.calls = 0

    def __call__(self, settings: Settings, **_kw: Any) -> DiscoveryResult:
        self.calls += 1
        return self.result


@pytest.fixture
def spy(monkeypatch: pytest.MonkeyPatch) -> Any:
    def install(result: DiscoveryResult) -> DiscoverySpy:
        s = DiscoverySpy(result)
        monkeypatch.setattr(resolve, "discover_from_settings", s)
        return s

    return install


def test_p2_t15_auto_prefers_meterless_online(spy: Any, meterless_token: str, nvidia_key: str) -> None:
    spy(ONLINE)
    p = resolve.resolve(_settings(METERLESS_RUNTIME_TOKEN=meterless_token, NVIDIA_API_KEY=nvidia_key))
    assert p.name == "meterless"
    assert p.model_for("fast") == "meterless/fast"


def test_p2_t15_auto_falls_back_to_nvidia(spy: Any, meterless_token: str, nvidia_key: str) -> None:
    spy(OFFLINE)
    p = resolve.resolve(_settings(METERLESS_RUNTIME_TOKEN=meterless_token, NVIDIA_API_KEY=nvidia_key))
    assert p.name == "nvidia"
    assert p.model_for("deep") == "nvidia/nemotron-3-super-120b-a12b"


def test_p2_t15_auto_unauthorized_falls_back_to_nvidia(spy: Any, nvidia_key: str) -> None:
    spy(DiscoveryResult(status="unauthorized", base_url="http://127.0.0.1:8088/v1", detail="HTTP 401"))
    assert resolve.resolve(_settings(NVIDIA_API_KEY=nvidia_key)).name == "nvidia"


def test_p2_t15_auto_nothing_gives_offline(spy: Any) -> None:
    spy(OFFLINE)
    p = resolve.resolve(_settings())
    assert p.name == "offline"
    with pytest.raises(OfflineProvider):
        p.chat([{"role": "user", "content": "x"}], model="offline", temperature=0.0, max_tokens=8)


def test_p2_t15_explicit_nvidia_overrides_online_meterless(spy: Any, nvidia_key: str) -> None:
    s = spy(ONLINE)
    assert resolve.resolve(_settings(LLM_PROVIDER="nvidia", NVIDIA_API_KEY=nvidia_key)).name == "nvidia"
    assert s.calls == 0


def test_p2_t15_explicit_nvidia_without_key_raises(spy: Any) -> None:
    spy(ONLINE)
    with pytest.raises(ConfigError) as exc_info:
        resolve.resolve(_settings(LLM_PROVIDER="nvidia"))
    assert "NVIDIA_API_KEY" in exc_info.value.message


def test_p2_t15_explicit_meterless_never_switches_to_nvidia(
    spy: Any, meterless_token: str, nvidia_key: str
) -> None:
    spy(OFFLINE)
    p = resolve.resolve(
        _settings(
            LLM_PROVIDER="meterless", METERLESS_RUNTIME_TOKEN=meterless_token, NVIDIA_API_KEY=nvidia_key
        )
    )
    assert p.name == "offline"


def test_p2_t15_explicit_offline(spy: Any, meterless_token: str, nvidia_key: str) -> None:
    s = spy(ONLINE)
    p = resolve.resolve(
        _settings(LLM_PROVIDER="offline", METERLESS_RUNTIME_TOKEN=meterless_token, NVIDIA_API_KEY=nvidia_key)
    )
    assert p.name == "offline"
    assert s.calls == 0


def test_p2_t15_generate_offline_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    with pytest.raises(OfflineProvider):
        generator.generate("anything", purpose="extract")


def test_p2_t15_cache_60s(spy: Any, monkeypatch: pytest.MonkeyPatch, meterless_token: str) -> None:
    s = spy(ONLINE)
    now = [1000.0]
    monkeypatch.setattr(resolve, "_now", lambda: now[0])
    settings = _settings(METERLESS_RUNTIME_TOKEN=meterless_token)
    resolve.resolve(settings)
    now[0] += 59.0
    resolve.resolve(settings)
    assert s.calls == 1
    now[0] += 2.0
    resolve.resolve(settings)
    assert s.calls == 2


def test_p2_t15_cache_keyed_on_provider_setting(spy: Any, meterless_token: str, nvidia_key: str) -> None:
    spy(ONLINE)
    assert resolve.resolve(_settings(METERLESS_RUNTIME_TOKEN=meterless_token)).name == "meterless"
    assert resolve.resolve(_settings(LLM_PROVIDER="offline")).name == "offline"
    assert resolve.resolve(_settings(LLM_PROVIDER="nvidia", NVIDIA_API_KEY=nvidia_key)).name == "nvidia"
