"""Data backend protocol (implemented in lane P1-A)."""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel


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
