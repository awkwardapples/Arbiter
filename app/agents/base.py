"""Agent protocol, shared context and the LLM-or-deterministic helper."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from app.agents.memory_port import MemoryPort
from app.config import Settings
from app.data.backend import DataBackend
from app.errors import OfflineProvider, ParseFailure, Unauthorized, UpstreamError, UpstreamTimeout
from app.policy.loader import Calibration, Policy
from app.state import CaseState
from app.tracing import Tracer

FALLBACK_ERRORS = (OfflineProvider, ParseFailure, UpstreamTimeout, UpstreamError, Unauthorized)
DEGRADING_ERRORS = (UpstreamTimeout, UpstreamError, Unauthorized)


class Agent(Protocol):
    name: str
    role: str

    def __call__(self, state: CaseState, ctx: AgentContext) -> CaseState: ...


def offline_generate(prompt: str, **_kwargs: Any) -> Any:
    """Generator used when the run is offline: no provider is resolved and nothing is called."""
    del prompt
    raise OfflineProvider("LLM offline for this run; deterministic logic used")


def _no_budget_check() -> None:
    return None


@dataclass
class AgentContext:
    tracer: Tracer
    backend: DataBackend
    generator: Callable[..., Any]
    policy: Policy
    calibration: Calibration
    memory: MemoryPort
    settings: Settings
    clock: Callable[[], datetime]
    degraded: bool = False
    offline: bool = False
    check_budget: Callable[[], None] = field(default=_no_budget_check)

    @property
    def use_model(self) -> bool:
        return not (self.offline or self.degraded)


def llm_or_fallback[T](
    ctx: AgentContext,
    fn_llm: Callable[[], T],
    fn_det: Callable[[], T],
    *,
    purpose: str,
    agent: str,
) -> tuple[T, str]:
    """Run the model-backed step, or its deterministic version. Returns (value, "llm"|"deterministic")."""
    if ctx.degraded:
        value = fn_det()
        ctx.tracer.event(
            agent,
            f"{purpose}_fallback",
            input_summary=f"purpose={purpose}",
            output_summary="provider degraded earlier in this run; deterministic logic used",
            status="fallback",
            provider="offline",
            purpose=purpose,
        )
        return value, "deterministic"
    try:
        return fn_llm(), "llm"
    except FALLBACK_ERRORS as exc:
        if isinstance(exc, DEGRADING_ERRORS):
            ctx.degraded = True
        value = fn_det()
        ctx.tracer.event(
            agent,
            f"{purpose}_fallback",
            input_summary=f"purpose={purpose}",
            output_summary=f"{type(exc).__name__}; deterministic logic used",
            status="fallback",
            provider="offline",
            purpose=purpose,
        )
        return value, "deterministic"
