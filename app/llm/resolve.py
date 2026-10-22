"""Provider resolution: Meterless Nightshift → NVIDIA direct → offline, cached for 60 s."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from app.config import Settings, get_settings
from app.llm.providers import meterless
from app.llm.providers.base import DiscoveryResult, Provider
from app.llm.providers.meterless import MeterlessProvider, discover_from_settings
from app.llm.providers.nvidia import NvidiaProvider
from app.llm.providers.offline import Offline

CACHE_TTL_S = 60.0
NOT_CHECKED = DiscoveryResult(status="not_checked", detail="not needed for this LLM_PROVIDER")


@dataclass(frozen=True)
class Resolution:
    provider: Provider
    meterless: DiscoveryResult
    reason: str


_lock = threading.Lock()
_cache: dict[tuple[object, ...], tuple[float, Resolution]] = {}


def _now() -> float:
    return time.monotonic()


def reset_cache() -> None:
    with _lock:
        _cache.clear()


def _cache_key(s: Settings) -> tuple[object, ...]:
    return (
        s.LLM_PROVIDER,
        s.METERLESS_BASE_URL,
        s.METERLESS_RUNTIME_TOKEN is not None,
        s.METERLESS_MODEL_FAST,
        s.METERLESS_MODEL_DEEP,
        s.NVIDIA_API_KEY is not None,
        s.NVIDIA_BASE_URL,
    )


def _meterless(s: Settings, found: DiscoveryResult) -> MeterlessProvider:
    return MeterlessProvider.from_settings(s, base_url=found.base_url or s.METERLESS_BASE_URL)


def _resolve(s: Settings) -> Resolution:
    choice = s.LLM_PROVIDER
    if choice == "offline":
        return Resolution(Offline("LLM_PROVIDER=offline"), NOT_CHECKED, "LLM_PROVIDER=offline")
    if choice == "nvidia":
        return Resolution(NvidiaProvider.from_settings(s), NOT_CHECKED, "LLM_PROVIDER=nvidia")
    if choice == "meterless":
        meterless.token_from(s)
        found = discover_from_settings(s)
        if found.status == "online":
            return Resolution(_meterless(s, found), found, "LLM_PROVIDER=meterless; Nightshift online")
        reason = f"LLM_PROVIDER=meterless but Nightshift is {found.status} ({found.detail})"
        return Resolution(Offline(reason), found, reason)
    found = discover_from_settings(s)
    if found.status == "online":
        return Resolution(_meterless(s, found), found, "auto: Nightshift online")
    if s.NVIDIA_API_KEY is not None:
        return Resolution(
            NvidiaProvider.from_settings(s), found, f"auto: Nightshift {found.status}; NVIDIA key set"
        )
    reason = f"auto: Nightshift {found.status}; no NVIDIA_API_KEY"
    return Resolution(Offline(reason), found, reason)


def resolve_detail(settings: Settings | None = None) -> Resolution:
    """Resolve the provider. Raises ConfigError only for an explicit, misconfigured LLM_PROVIDER."""
    s = settings or get_settings()
    key = _cache_key(s)
    now = _now()
    with _lock:
        hit = _cache.get(key)
        if hit is not None and now - hit[0] < CACHE_TTL_S:
            return hit[1]
    resolution = _resolve(s)
    with _lock:
        _cache[key] = (now, resolution)
    return resolution


def resolve(settings: Settings | None = None) -> Provider:
    return resolve_detail(settings).provider
