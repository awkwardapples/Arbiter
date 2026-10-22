"""LLM provider status (lane P2-B implements)."""


def check() -> dict[str, object]:
    from app.config import get_settings

    return {"provider_resolved": get_settings().LLM_PROVIDER, "status": "stub"}
