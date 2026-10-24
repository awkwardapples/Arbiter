"""Meterless Nightshift provider (POWER contract): discovery via /v1/models, OpenAI-compatible chat."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.config import Settings
from app.errors import ConfigError
from app.llm.providers.base import ChatResult, DiscoveryResult, Route, parse_chat_body, post_chat, scrub

logger = logging.getLogger("arbiter.llm.meterless")

AUTODETECT_HOSTS = ("127.0.0.1", "localhost", "[::1]")
AUTODETECT_PORTS = (8088, 8090, 8787, 11434)
CONNECT_TIMEOUT_S = 2.0
PLACEHOLDER_TOKEN = "rt-local"
NO_THINK_MESSAGE = {"role": "system", "content": "/no_think"}
# Pasted URLs may end in any of these; longest first so "/v1/models" is not read as "/v1".
_PASTED_SUFFIXES = ("/v1/chat/completions", "/v1/models", "/healthz", "/v1")
# Receipt fields copied from the response body's `meterless` object into the trace.
_RECEIPT_KEYS = (
    "schema",
    "receipt_id",
    "decision_id",
    "requested_model",
    "provider_model",
    "routed_model",
    "mode",
    "requires_review",
)
_ROUTE_KEYS = ("provider", "label", "kind", "tier", "model")
# Scalar fields of these receipt objects are flattened as `<object>.<field>`; nested objects
# other than `cost.baseline` are dropped. Phases, egress, lineage and cache never reach a trace.
_POLICY_KEYS = ("app", "has_rule", "bound_mode", "requested_mode", "routed_mode", "mode_coerced", "privacy")
_COST_KEYS = ("actual_usd", "naive_usd", "race_overhead_usd", "verifier_usd")
_BASELINE_KEYS = ("model", "label", "source")
_SAVINGS_KEYS = ("amount", "currency", "vs", "baseline_source")


def normalise_base_url(url: str) -> str:
    """`[scheme://]host[:port][/v1[/models|/chat/completions]|/healthz]` → `scheme://host[:port]/v1`."""
    raw = url.strip()
    if "://" not in raw:
        raw = "http://" + raw
    parts = urlsplit(raw)
    path = parts.path.rstrip("/")
    for suffix in _PASTED_SUFFIXES:
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break
    return f"{parts.scheme}://{parts.netloc}{path.rstrip('/')}/v1"


def candidate_base_urls() -> list[str]:
    return [f"http://{host}:{port}/v1" for host in AUTODETECT_HOSTS for port in AUTODETECT_PORTS]


def headers(token: str, app_id: str, *, chat: bool) -> dict[str, str]:
    out = {"Authorization": f"Bearer {token}", "meterless-app": app_id}
    if chat:
        out["meterless-scope"] = "user"
    return out


def token_from(settings: Settings) -> str | None:
    """The runtime token, or None when unset. The Console placeholder `rt-local` is a ConfigError."""
    configured = settings.METERLESS_RUNTIME_TOKEN
    if configured is None:
        return None
    value = configured.get_secret_value().strip()
    if value == PLACEHOLDER_TOKEN:
        raise ConfigError(
            "METERLESS_RUNTIME_TOKEN is the placeholder 'rt-local'. Copy the real runtime token from "
            "the Nightshift console (Runtime → token) into .env, or set LLM_PROVIDER=auto to fall back."
        )
    return value or None


def discover(
    base_url: str,
    token: str,
    app_id: str,
    *,
    timeout_s: float = 180.0,
    transport: httpx.BaseTransport | None = None,
) -> DiscoveryResult:
    """GET /v1/models. 200 with `meterless/*` ids → online; 401/403 → unauthorized; else offline."""
    base = normalise_base_url(base_url)
    timeout = httpx.Timeout(timeout_s, connect=CONNECT_TIMEOUT_S)
    try:
        with httpx.Client(transport=transport) as client:
            resp = client.get(f"{base}/models", headers=headers(token, app_id, chat=False), timeout=timeout)
    except httpx.HTTPError as exc:
        return DiscoveryResult(status="offline", base_url=base, detail=f"unreachable ({type(exc).__name__})")
    if resp.status_code in (401, 403):
        return DiscoveryResult(
            status="unauthorized", base_url=base, detail=f"HTTP {resp.status_code}: token rejected"
        )
    if resp.status_code != 200:
        return DiscoveryResult(status="offline", base_url=base, detail=f"HTTP {resp.status_code}")
    try:
        data = resp.json().get("data")
        ids = [str(m["id"]) for m in data]
    except (ValueError, AttributeError, KeyError, TypeError):
        return DiscoveryResult(status="offline", base_url=base, detail="unexpected /v1/models body")
    if not any(i.startswith("meterless/") for i in ids):
        return DiscoveryResult(
            status="offline", base_url=base, models_seen=ids, detail="no meterless/* model ids"
        )
    return DiscoveryResult(status="online", base_url=base, models_seen=ids, detail=f"{len(ids)} models")


def autodetect(
    token: str,
    app_id: str,
    *,
    timeout_s: float = 180.0,
    transport: httpx.BaseTransport | None = None,
) -> DiscoveryResult:
    """Probe the 12 local host:port pairs in order; stop at the first online one."""
    unauthorized: DiscoveryResult | None = None
    for base in candidate_base_urls():
        result = discover(base, token, app_id, timeout_s=timeout_s, transport=transport)
        if result.status == "online":
            return result
        if result.status == "unauthorized" and unauthorized is None:
            unauthorized = result
    if unauthorized is not None:
        return unauthorized
    return DiscoveryResult(status="offline", detail="no Nightshift found on 12 local host:port candidates")


def discover_from_settings(
    settings: Settings, *, transport: httpx.BaseTransport | None = None
) -> DiscoveryResult:
    """Discovery as configured. Never raises: `rt-local` is reported as `config_error`."""
    try:
        bearer = token_from(settings)
    except ConfigError as exc:
        logger.warning("Meterless skipped: %s", exc.message)
        return DiscoveryResult(status="config_error", detail=exc.message)
    if bearer is None:
        return DiscoveryResult(status="offline", detail="METERLESS_RUNTIME_TOKEN is not set")
    timeout_s = float(settings.METERLESS_TIMEOUT_SECONDS)
    if settings.METERLESS_BASE_URL:
        result = discover(
            settings.METERLESS_BASE_URL,
            bearer,
            settings.METERLESS_APP_ID,
            timeout_s=timeout_s,
            transport=transport,
        )
    else:
        result = autodetect(bearer, settings.METERLESS_APP_ID, timeout_s=timeout_s, transport=transport)
    return result.model_copy(update={"detail": scrub(result.detail, [bearer])})


def receipt_meta(body: dict[str, Any], resp_headers: httpx.Headers | None = None) -> dict[str, str]:
    """Route and receipt metadata: the body's `meterless` object plus any `meterless-*` headers."""
    meta: dict[str, str] = {}
    if isinstance(body.get("id"), str):
        meta["response_id"] = body["id"]
    receipt = body.get("meterless")
    if isinstance(receipt, dict):
        for key in _RECEIPT_KEYS:
            if receipt.get(key) is not None:
                meta[key] = str(receipt[key])
        inner = receipt.get("receipt")
        policy = receipt.get("app_policy")
        if not isinstance(policy, dict) and isinstance(inner, dict):
            policy = inner.get("app_policy")
        cost = receipt.get("cost")
        _flatten(meta, "winning_route", receipt.get("winning_route"), _ROUTE_KEYS)
        _flatten(meta, "app_policy", policy, _POLICY_KEYS)
        _flatten(meta, "cost", cost, _COST_KEYS)
        _flatten(
            meta, "cost.baseline", cost.get("baseline") if isinstance(cost, dict) else None, _BASELINE_KEYS
        )
        _flatten(meta, "savings", receipt.get("savings"), _SAVINGS_KEYS)
    for name, value in (resp_headers or {}).items():
        if name.lower().startswith("meterless-"):
            meta[f"header.{name.lower()}"] = value
    return meta


def _flatten(meta: dict[str, str], prefix: str, source: object, keys: tuple[str, ...]) -> None:
    if not isinstance(source, dict):
        return
    for key in keys:
        value = source.get(key)
        if value is not None and not isinstance(value, (dict, list)):
            meta[f"{prefix}.{key}"] = str(value)


class MeterlessProvider:
    name = "meterless"

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        app_id: str,
        model_fast: str,
        model_deep: str,
        timeout_s: float = 180.0,
        no_think: bool = False,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = normalise_base_url(base_url)
        self.no_think = no_think
        self._token = token
        self.app_id = app_id
        self.models = {"fast": model_fast, "deep": model_deep}
        self.timeout_s = timeout_s
        self._transport = transport

    @classmethod
    def from_settings(
        cls, settings: Settings, *, base_url: str, transport: httpx.BaseTransport | None = None
    ) -> MeterlessProvider:
        bearer = token_from(settings)
        if bearer is None:
            raise ConfigError("METERLESS_RUNTIME_TOKEN is not set")
        return cls(
            base_url=base_url,
            token=bearer,
            app_id=settings.METERLESS_APP_ID,
            model_fast=settings.METERLESS_MODEL_FAST,
            model_deep=settings.METERLESS_MODEL_DEEP,
            timeout_s=float(settings.METERLESS_TIMEOUT_SECONDS),
            no_think=settings.METERLESS_NO_THINK,
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
        # `timeout` is deliberately ignored: the POWER contract fixes every Meterless call at 180 s
        # because a cold lane can take minutes and a shorter limit reads as a false outage.
        if self.no_think:
            messages = [dict(NO_THINK_MESSAGE), *messages]
        body, resp_headers, latency_ms = post_chat(
            provider=self.name,
            url=f"{self.base_url}/chat/completions",
            headers=headers(self._token, self.app_id, chat=True),
            payload={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=httpx.Timeout(self.timeout_s),
            secrets=[self._token],
            transport=self._transport,
        )
        text, served, tokens_in, tokens_out = parse_chat_body(body, self.name)
        meta = receipt_meta(body, resp_headers)
        if self.no_think:
            meta["no_think"] = "true"
        return ChatResult(
            text=text,
            model=served,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            provider_meta=meta,
        )
