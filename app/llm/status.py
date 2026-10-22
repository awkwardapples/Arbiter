"""LLM provider status for `/health` and `preflight`. Contains no secret values."""

from __future__ import annotations

from app.config import get_settings
from app.errors import ConfigError
from app.llm.providers.meterless import discover_from_settings
from app.llm.resolve import resolve_detail


def check() -> dict[str, object]:
    s = get_settings()
    try:
        resolution = resolve_detail(s)
        provider_resolved = resolution.provider.name
        reason = resolution.reason
        found = resolution.meterless
    except ConfigError as exc:
        provider_resolved = "error"
        reason = exc.message
        found = None
    if found is None or found.status == "not_checked":
        found = discover_from_settings(s)
    return {
        "provider_resolved": provider_resolved,
        "llm_provider_setting": s.LLM_PROVIDER,
        "reason": reason,
        "meterless": {
            "status": found.status,
            "base_url": found.base_url,
            "models_seen": found.models_seen,
            "fast_model": s.METERLESS_MODEL_FAST,
            "deep_model": s.METERLESS_MODEL_DEEP,
            "detail": found.detail,
        },
        "nvidia": {
            "configured": s.NVIDIA_API_KEY is not None,
            "base_url": s.NVIDIA_BASE_URL,
            "fast_model": s.NVIDIA_MODEL_FAST,
            "deep_model": s.NVIDIA_MODEL_DEEP,
        },
    }
