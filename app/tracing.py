"""Agent trace JSONL and readable stdout lines."""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import mask_secrets
from app.schemas.trace import TraceEvent

logger = logging.getLogger("arbiter.trace")


class Tracer:
    def __init__(self, run_id: str, *, mode: dict[str, str], log_dir: str = "logs") -> None:
        self.run_id = run_id
        self.trace_id = run_id
        self.mode = mode
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._path = self._log_dir / f"trace-{run_id}.jsonl"
        self._lock = threading.Lock()
        self._file = self._path.open("a", encoding="utf-8")
        self._parent_span_id: str | None = None

    def event(
        self,
        agent_name: str,
        action: str,
        *,
        input_summary: str,
        output_summary: str,
        status: str = "success",
        target_agent: str | None = None,
        confidence: float | None = None,
        retry_count: int = 0,
        parent_span_id: str | None = None,
        **extras: Any,
    ) -> TraceEvent:
        span_id = uuid.uuid4().hex[:16]
        parent = parent_span_id if parent_span_id is not None else self._parent_span_id
        in_s = mask_secrets(input_summary)
        out_s = mask_secrets(output_summary)
        evt = TraceEvent(
            timestamp=datetime.now(UTC),
            run_id=self.run_id,
            trace_id=self.trace_id,
            span_id=span_id,
            parent_span_id=parent,
            agent_name=agent_name,
            action=action,
            input_summary=in_s,
            output_summary=out_s,
            target_agent=target_agent,
            confidence=confidence,
            retry_count=retry_count,
            status=status,  # type: ignore[arg-type]
            mode=self.mode,
            **extras,
        )
        line = evt.model_dump_json()
        with self._lock:
            self._file.write(line + "\n")
            self._file.flush()
        target = target_agent or "—"
        logger.info(
            "run_id=%s %s → %s: %s (%s)",
            self.run_id,
            agent_name,
            target,
            out_s,
            status,
        )
        return evt

    @contextmanager
    def span(
        self,
        agent_name: str,
        action: str,
        *,
        input_summary: str = "",
        target_agent: str | None = None,
    ) -> Iterator[TraceEvent]:
        parent_before = self._parent_span_id
        start = self.event(
            agent_name,
            action,
            input_summary=input_summary,
            output_summary="started",
            status="success",
            target_agent=target_agent,
        )
        self._parent_span_id = start.span_id
        try:
            yield start
        finally:
            self._parent_span_id = parent_before

    @property
    def path(self) -> Path:
        """The file this tracer writes, wherever its log directory is."""
        return self._path

    def close(self) -> None:
        with self._lock:
            self._file.flush()
            self._file.close()
