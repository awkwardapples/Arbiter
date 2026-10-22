"""NVIDIA build.nvidia.com direct provider (fallback B): OpenAI-compatible chat, 90 s timeout."""

from __future__ import annotations

import httpx

from app.config import Settings
from app.errors import ConfigError
from app.llm.providers.base import ChatResult, Route, parse_chat_body, post_chat


class NvidiaProvider:
    name = "nvidia"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model_fast: str,
        model_deep: str,
        timeout_s: float = 90.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.strip().rstrip("/")
        self._api_key = api_key
        self.models = {"fast": model_fast, "deep": model_deep}
        self.timeout_s = timeout_s
        self._transport = transport

    @classmethod
    def from_settings(
        cls, settings: Settings, *, transport: httpx.BaseTransport | None = None
    ) -> NvidiaProvider:
        if settings.NVIDIA_API_KEY is None:
            raise ConfigError(
                "LLM_PROVIDER=nvidia but NVIDIA_API_KEY is not set. Add a build.nvidia.com key to .env, "
                "or set LLM_PROVIDER=auto to use Nightshift or the offline fallback."
            )
        credential = settings.NVIDIA_API_KEY.get_secret_value()
        return cls(
            base_url=settings.NVIDIA_BASE_URL,
            api_key=credential,
            model_fast=settings.NVIDIA_MODEL_FAST,
            model_deep=settings.NVIDIA_MODEL_DEEP,
            timeout_s=float(settings.NVIDIA_TIMEOUT_SECONDS),
            transport=transport,
        )

    def model_for(self, route: Route) -> str:
        return self.models[route]

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: float | None = None,
    ) -> ChatResult:
        timeout_s = min(timeout, self.timeout_s) if timeout else self.timeout_s
        body, _headers, latency_ms = post_chat(
            provider=self.name,
            url=f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}", "Accept": "application/json"},
            payload={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=httpx.Timeout(timeout_s),
            secrets=[self._api_key],
            transport=self._transport,
        )
        text, served, tokens_in, tokens_out = parse_chat_body(body, self.name)
        meta = {"id": str(body["id"])} if body.get("id") is not None else {}
        return ChatResult(
            text=text,
            model=served,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            provider_meta=meta,
        )
