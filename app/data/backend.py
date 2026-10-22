"""Data backend protocol and fallback wrapper."""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel

from app.errors import Unauthorized, UpstreamError, UpstreamTimeout
from app.tracing import Tracer


class QueryResult(BaseModel):
    query_id: str
    rows: list[dict[str, object]]
    columns: list[str]
    backend: Literal["zetaris", "duckdb", "inline"]
    request_id: str | None = None
    latency_ms: int
    fallback_from: str | None = None


class DataBackend(Protocol):
    name: str

    def run(self, query_id: str, params: dict[str, object]) -> QueryResult: ...


class FallbackBackend:
    name = "fallback"

    def __init__(self, primary: DataBackend, secondary: DataBackend, tracer: Tracer) -> None:
        self._primary = primary
        self._secondary = secondary
        self._tracer = tracer
        self._pin_secondary = False

    def run(self, query_id: str, params: dict[str, object]) -> QueryResult:
        if self._pin_secondary:
            return self._run_secondary(query_id, params, fallback_from=self._primary.name)
        try:
            return self._primary.run(query_id, params)
        except Unauthorized:
            self._pin_secondary = True
            self._emit_fallback(query_id, self._primary.name)
            return self._run_secondary(query_id, params, fallback_from=self._primary.name)
        except (UpstreamTimeout, UpstreamError):
            self._emit_fallback(query_id, self._primary.name)
            return self._run_secondary(query_id, params, fallback_from=self._primary.name)

    def _run_secondary(self, query_id: str, params: dict[str, object], *, fallback_from: str) -> QueryResult:
        result = self._secondary.run(query_id, params)
        return result.model_copy(update={"fallback_from": fallback_from})

    def _emit_fallback(self, query_id: str, primary_name: str) -> None:
        self._tracer.event(
            "data",
            "query_fallback",
            input_summary=f"query_id={query_id}",
            output_summary=f"primary={primary_name} secondary={self._secondary.name}",
            status="fallback",
        )


class FailingBackend:
    """Test double for primary backend failures."""

    name = "failing"

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def run(self, query_id: str, params: dict[str, object]) -> QueryResult:
        raise self._exc


class RecordingBackend:
    """Wraps a backend and counts calls."""

    name = "recording"

    def __init__(self, inner: DataBackend) -> None:
        self.inner = inner
        self.calls = 0

    def run(self, query_id: str, params: dict[str, object]) -> QueryResult:
        self.calls += 1
        return self.inner.run(query_id, params)
