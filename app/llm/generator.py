"""The single LLM seam. Every model call in Arbiter goes through `generate()`."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from app.errors import ArbiterError, ConfigError, ParseFailure
from app.llm import jsonparse, prompts
from app.llm.providers.base import ChatResult, Provider
from app.llm.resolve import resolve
from app.tracing import Tracer

logger = logging.getLogger("arbiter.llm")

# purpose -> (temperature, max_tokens). Nemotron reasoning tokens count against max_tokens, so
# budgets are generous: a live `{"ok": true}` reply used 179 completion tokens, and 64 returned empty.
PURPOSES: dict[str, tuple[float, int]] = {
    "plan": (0.0, 2048),
    "extract": (0.0, 4096),
    "critique": (0.0, 2048),
    "challenge": (0.0, 2048),
    "report": (0.2, 4096),
    "guard_classify": (0.0, 1024),
    "repair": (0.0, 4096),
    "ping": (0.0, 1024),
}
DEFAULT_PURPOSE: tuple[float, int] = (0.0, 2048)


class GenerationResult(BaseModel):
    text: str
    parsed: BaseModel | None = None
    provider: str
    route: str
    model: str | None = None
    latency_ms: int
    tokens_in: int | None = None
    tokens_out: int | None = None
    repaired: bool = False


@dataclass
class _Call:
    """One generate() invocation: the provider plus everything a trace event needs (no text)."""

    provider: Provider
    model: str
    route: str
    response: str
    purpose: str
    temperature: float
    max_tokens: int
    timeout_s: float | None
    tracer: Tracer | None
    agent_name: str

    def chat(self, attempt: int, messages: list[dict[str, str]]) -> ChatResult:
        if self.tracer is not None:
            self.tracer.event(
                self.agent_name,
                "model_request",
                input_summary=(
                    f"purpose={self.purpose} route={self.route} attempt={attempt} "
                    f"prompt_chars={sum(len(m['content']) for m in messages)}"
                ),
                output_summary=f"sent to {self.provider.name}",
                status="success",
                provider=self.provider.name,
                route=self.route,
                purpose=self.purpose,
            )
        start = time.monotonic()
        try:
            return self.provider.chat(
                messages,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout_s,
            )
        except ArbiterError as exc:
            latency = int((time.monotonic() - start) * 1000)
            self.trace("fallback", attempt, messages, f"{exc.type}: {exc.message}", latency_ms=latency)
            raise

    def trace(
        self,
        status: str,
        attempt: int,
        messages: list[dict[str, str]],
        output_summary: str,
        *,
        chat: ChatResult | None = None,
        latency_ms: int | None = None,
    ) -> None:
        logger.debug(
            "model_call agent=%s provider=%s route=%s purpose=%s attempt=%d status=%s",
            self.agent_name,
            self.provider.name,
            self.route,
            self.purpose,
            attempt,
            status,
        )
        if self.tracer is None:
            return
        self.tracer.event(
            self.agent_name,
            "model_call",
            input_summary=(
                f"purpose={self.purpose} route={self.route} response={self.response} "
                f"attempt={attempt} prompt_chars={sum(len(m['content']) for m in messages)}"
            ),
            output_summary=output_summary,
            status=status,
            retry_count=attempt - 1,
            provider=self.provider.name,
            route=self.route,
            model=chat.model if chat else None,
            latency_ms=chat.latency_ms if chat else latency_ms,
            tokens_in=chat.tokens_in if chat else None,
            tokens_out=chat.tokens_out if chat else None,
            purpose=self.purpose,
            provider_meta={"requested_model": self.model, **(chat.provider_meta if chat else {})},
        )

    def result(self, chat: ChatResult, *, parsed: BaseModel | None, repaired: bool) -> GenerationResult:
        return GenerationResult(
            text=chat.text,
            parsed=parsed,
            provider=self.provider.name,
            route=self.route,
            model=chat.model,
            latency_ms=chat.latency_ms,
            tokens_in=chat.tokens_in,
            tokens_out=chat.tokens_out,
            repaired=repaired,
        )


def _errors(exc: ParseFailure) -> list[str]:
    return list(getattr(exc, "errors", None) or [exc.message])


def generate(
    prompt: str,
    *,
    system: str | None = None,
    route: Literal["fast", "deep"] = "fast",
    response: Literal["text", "json"] = "text",
    schema: type[BaseModel] | None = None,
    timeout_s: float | None = None,
    purpose: str,
    tracer: Tracer | None = None,
    agent_name: str = "unknown",
) -> GenerationResult:
    """Call the resolved provider. JSON responses get exactly one repair attempt.

    Raises `OfflineProvider` (no provider), `UpstreamTimeout` / `UpstreamError` / `Unauthorized`
    (provider failed) or `ParseFailure` (two invalid JSON answers); callers then fall back.
    Traces carry metadata only, never prompt or response text.
    """
    if response == "json" and schema is None:
        raise ConfigError("generate(response='json') requires a schema")
    provider = resolve()
    temperature, max_tokens = PURPOSES.get(purpose, DEFAULT_PURPOSE)
    call = _Call(
        provider=provider,
        model=provider.model_for(route),
        route=route,
        response=response,
        purpose=purpose,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout_s=timeout_s,
        tracer=tracer,
        agent_name=agent_name,
    )
    messages = [{"role": "system", "content": system}] if system else []
    messages.append({"role": "user", "content": prompt})

    chat = call.chat(1, messages)
    if response == "text":
        call.trace("success", 1, messages, f"text chars={len(chat.text)}", chat=chat)
        return call.result(chat, parsed=None, repaired=False)

    assert schema is not None
    try:
        parsed, _raw = jsonparse.parse(chat.text, schema)
    except ParseFailure as first:
        errors = _errors(first)
        call.trace(
            "retrying", 1, messages, f"ParseFailure ({len(errors)} errors); one repair call", chat=chat
        )
    else:
        call.trace("success", 1, messages, f"json valid ({schema.__name__})", chat=chat)
        return call.result(chat, parsed=parsed, repaired=False)

    repair = prompts.render(
        "repair",
        error="; ".join(errors),
        schema_json=json.dumps(schema.model_json_schema(), sort_keys=True),
        bad_output=chat.text,
    )
    repair_messages = [*messages[:-1], {"role": "user", "content": repair}]
    chat = call.chat(2, repair_messages)
    try:
        parsed, _raw = jsonparse.parse(chat.text, schema)
    except ParseFailure as second:
        n = len(_errors(second))
        call.trace("fallback", 2, repair_messages, f"ParseFailure after repair ({n} errors)", chat=chat)
        raise
    call.trace("success", 2, repair_messages, f"json valid after repair ({schema.__name__})", chat=chat)
    return call.result(chat, parsed=parsed, repaired=True)
