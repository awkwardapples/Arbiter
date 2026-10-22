"""Provider contract and the shared OpenAI-compatible chat call."""

from __future__ import annotations

import time
from typing import Any, Literal, Protocol

import httpx
from pydantic import BaseModel, Field

from app.config import mask_secrets
from app.errors import Unauthorized, UpstreamError, UpstreamTimeout

Route = Literal["fast", "deep"]
DiscoveryStatus = Literal["online", "unauthorized", "offline", "config_error", "not_checked"]


class ChatResult(BaseModel):
    text: str
    model: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_ms: int
    provider_meta: dict[str, str] = Field(default_factory=dict)


class DiscoveryResult(BaseModel):
    status: DiscoveryStatus
    base_url: str | None = None
    models_seen: list[str] = Field(default_factory=list)
    detail: str = ""


class Provider(Protocol):
    name: str

    def model_for(self, route: Route) -> str: ...

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: float | None = None,
    ) -> ChatResult: ...


def scrub(text: str, secrets: list[str]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return mask_secrets(text)


_CODE_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-/:")


def _error_detail(resp: httpx.Response) -> str:
    """Machine-readable error codes only; free-text messages may echo request content."""
    try:
        body = resp.json()
    except ValueError:
        return ""
    err = body.get("error") if isinstance(body, dict) else None
    if not isinstance(err, dict):
        return ""
    codes = [err.get(k) for k in ("code", "type", "meterless_detail")]
    safe = [c for c in codes if isinstance(c, str) and c and len(c) <= 120 and set(c) <= _CODE_CHARS]
    return " ".join(dict.fromkeys(safe))


def post_chat(
    *,
    provider: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: httpx.Timeout,
    secrets: list[str],
    transport: httpx.BaseTransport | None = None,
) -> tuple[dict[str, Any], httpx.Headers, int]:
    """POST an OpenAI-compatible chat request; map failures to typed, secret-free errors."""
    start = time.monotonic()
    try:
        with httpx.Client(transport=transport) as client:
            resp = client.post(url, headers=headers, json=payload, timeout=timeout)
    except httpx.TimeoutException as exc:
        raise UpstreamTimeout(
            f"{provider} timed out ({type(exc).__name__}, read timeout {timeout.read}s)", recoverable=True
        ) from None
    except httpx.HTTPError as exc:
        raise UpstreamError(f"{provider} request failed ({type(exc).__name__})", recoverable=True) from None
    latency_ms = int((time.monotonic() - start) * 1000)
    if resp.status_code in (401, 403):
        raise Unauthorized(f"{provider} rejected the credentials (HTTP {resp.status_code})")
    if resp.status_code >= 400:
        detail = scrub(_error_detail(resp), secrets)
        suffix = f": {detail}" if detail else ""
        raise UpstreamError(f"{provider} HTTP {resp.status_code}{suffix}", recoverable=True)
    try:
        body = resp.json()
    except ValueError:
        raise UpstreamError(f"{provider} returned a non-JSON body", recoverable=True) from None
    if not isinstance(body, dict):
        raise UpstreamError(f"{provider} returned an unexpected body", recoverable=True)
    return body, resp.headers, latency_ms


def parse_chat_body(body: dict[str, Any], provider: str) -> tuple[str, str | None, int | None, int | None]:
    """(text, model, tokens_in, tokens_out) from an OpenAI-compatible chat completion."""
    try:
        message = body["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        raise UpstreamError(f"{provider} response has no choices[0].message", recoverable=True) from None
    content = message.get("content") if isinstance(message, dict) else None
    text = content if isinstance(content, str) else ""
    usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
    model = body.get("model") if isinstance(body.get("model"), str) else None
    tokens_in = usage.get("prompt_tokens")
    tokens_out = usage.get("completion_tokens")
    return (
        text,
        model,
        tokens_in if isinstance(tokens_in, int) else None,
        tokens_out if isinstance(tokens_out, int) else None,
    )
