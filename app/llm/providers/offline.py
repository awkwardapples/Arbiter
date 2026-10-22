"""Offline provider: every call raises `OfflineProvider` so callers use deterministic logic."""

from __future__ import annotations

from app.errors import OfflineProvider
from app.llm.providers.base import ChatResult, Route


class Offline:
    name = "offline"

    def __init__(self, reason: str) -> None:
        self.reason = reason

    def model_for(self, route: Route) -> str:
        return "offline"

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: float | None = None,
    ) -> ChatResult:
        raise OfflineProvider(f"no LLM provider available ({self.reason}); use the deterministic fallback")
