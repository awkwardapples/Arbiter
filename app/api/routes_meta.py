"""Health, vendor picker and audit-chain verification (lane P4-B)."""

from __future__ import annotations

import importlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.catalogue import QUESTION_TEXTS
from app.config import Settings
from app.data.duckdb_backend import DuckDBBackend
from app.data.factory import get_backend
from app.data.status import check as data_check
from app.errors import NotFound
from app.llm.status import check as provider_check
from app.policy.loader import load_default
from app.schemas.api import HealthResponse, QuestionInfo
from app.tracing import Tracer

router = APIRouter(tags=["meta"])

_AUDIT_DB = Path("var/audit.db")
_EVAL_LIVE = Path("eval/results_live")
_EVAL_OFFLINE = Path("eval/results")


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


_YES_NO_LEADS = {"Is", "Have", "Do", "Will"}


@router.get("/questions", response_model=list[QuestionInfo])
def questions() -> list[QuestionInfo]:
    """The fixed questionnaire. Texts come from the catalogue, help from the policy control."""
    policy, _calibration = load_default()
    control_by_question = {}
    for control in policy.controls:
        for question_id in control.question_ids:
            control_by_question.setdefault(question_id, control)
    items: list[QuestionInfo] = []
    for question_id in sorted(QUESTION_TEXTS):
        text = QUESTION_TEXTS[question_id]
        control = control_by_question.get(question_id)
        yes_no = text.split(" ", 1)[0] in _YES_NO_LEADS
        items.append(
            QuestionInfo(
                question_id=question_id,
                question=text,
                help=f"Used to check: {control.title}." if control else "",
                type="yes_no" if yes_no else "text",
                options=["Yes", "No", "Not answered"] if yes_no else None,
            )
        )
    return items


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


def _latest_summary(root: Path) -> tuple[dict[str, Any] | None, str | None]:
    """The newest run directory by name with a summary.json. Reads summaries only, never labels."""
    if not root.is_dir():
        return None, None
    runs = sorted(path for path in root.iterdir() if (path / "summary.json").is_file())
    if not runs:
        return None, None
    latest = runs[-1]
    summary = json.loads((latest / "summary.json").read_text(encoding="utf-8"))
    markdown = latest / "summary.md"
    return summary, markdown.read_text(encoding="utf-8") if markdown.is_file() else None


@router.get("/eval/latest")
def eval_latest() -> dict[str, Any]:
    """The published live evaluation and the offline benchmark. 404 only if neither exists."""
    live, live_markdown = _latest_summary(_EVAL_LIVE)
    offline, offline_markdown = _latest_summary(_EVAL_OFFLINE)
    if live is None and offline is None:
        raise NotFound("evaluation results are not published")
    return {
        "live": live,
        "offline": offline,
        "live_markdown": live_markdown,
        "offline_markdown": offline_markdown,
    }
