"""Health, vendor picker and audit-chain verification (lane P4-B)."""

from __future__ import annotations

import importlib
import sqlite3
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import Settings
from app.data.duckdb_backend import DuckDBBackend
from app.data.factory import get_backend
from app.data.status import check as data_check
from app.llm.status import check as provider_check
from app.schemas.api import HealthResponse
from app.tracing import Tracer

router = APIRouter(tags=["meta"])

_AUDIT_DB = Path("var/audit.db")


class AuditVerifyResponse(BaseModel):
    ok: bool
    first_bad_seq: int | None


class AuditEvent(BaseModel):
    seq: int
    timestamp: str
    case_id: str
    event_type: str


def _audit_length() -> int:
    if not _AUDIT_DB.is_file():
        return 0
    with sqlite3.connect(_AUDIT_DB) as conn:
        row = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()
    return int(row[0]) if row else 0


def _hmem_count() -> int | None:
    try:
        keeper = importlib.import_module("app.memory.keeper")
    except ImportError:
        return None
    count = getattr(keeper, "count", None)
    if not callable(count):
        return None
    return int(count())


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = Settings()
    return HealthResponse(
        mode=settings.mode(),
        data=data_check(settings),
        provider=provider_check(),
        hmem_records=_hmem_count(),
        audit_chain_length=_audit_length(),
    )


@router.get("/vendors")
def vendors() -> list[dict[str, object]]:
    settings = Settings()
    if settings.SAMPLE_MODE:
        result = DuckDBBackend().run("Q_VENDOR_LIST", {})
    else:
        tracer = Tracer("vendors", mode=settings.mode())
        try:
            result = get_backend(settings, tracer).run("Q_VENDOR_LIST", {})
        finally:
            tracer.close()
    return result.rows


@router.get("/audit/recent", response_model=list[AuditEvent])
def audit_recent(limit: int = 20) -> list[AuditEvent]:
    """Additive read-only route. File owner is P4-B; approved under P11.

    Rows are sequence, timestamp, case id, and event type. Payload stays in the database.
    """
    size = min(max(limit, 1), 100)
    if not _AUDIT_DB.is_file():
        return []
    with sqlite3.connect(_AUDIT_DB) as conn:
        rows = conn.execute(
            """
            SELECT seq, ts, case_id, event_type
            FROM audit_log
            ORDER BY seq DESC
            LIMIT ?
            """,
            (size,),
        ).fetchall()
    return [
        AuditEvent(seq=int(seq), timestamp=str(ts), case_id=str(case_id), event_type=str(event_type))
        for seq, ts, case_id, event_type in rows
    ]


@router.get("/audit/verify")
def audit_verify() -> AuditVerifyResponse:
    from app.audit.chain import AuditChain

    ok, seq = AuditChain().verify()
    return AuditVerifyResponse(ok=ok, first_bad_seq=seq)
