"""Single LLM seam (implemented in lane P2-B)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.errors import OfflineProvider
from app.tracing import Tracer


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
    raise OfflineProvider(f"LLM not configured (purpose={purpose}, agent={agent_name})")
