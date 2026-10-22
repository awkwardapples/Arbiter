from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class TraceEvent(BaseModel):
    timestamp: datetime
    run_id: str
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    agent_name: str
    action: str
    input_summary: str
    output_summary: str
    target_agent: str | None = None
    confidence: float | None = None
    retry_count: int = 0
    status: Literal[
        "success",
        "needs_revision",
        "retrying",
        "fallback",
        "blocked",
        "escalated",
        "partial_success",
        "error",
        "pending_approval",
    ]
    provider: str | None = None
    route: str | None = None
    model: str | None = None
    latency_ms: int | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    purpose: str | None = None
    provider_meta: dict[str, str] | None = None
    source_system: str | None = None
    query_id: str | None = None
    rows: int | None = None
    backend: str | None = None
    loop: str | None = None
    iteration: int | None = None
    mode: dict[str, str] | None = None
