"""Case queue, detail, trace and replay (lane P4-B)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Query
from fastapi.responses import Response
from pydantic import BaseModel

from app.audit.replay import ReplayResult, replay
from app.dossier import render
from app.errors import NotFound, ParseFailure
from app.schemas.contract import ExecutionContract
from app.schemas.decision import DecisionRecord
from app.schemas.report import Report
from app.store import Store

router = APIRouter(prefix="/cases", tags=["cases"])


class QueueItem(BaseModel):
    case_id: str
    vendor: str
    outcome: str
    tier: str
    residual_risk: int
    status: str
    created: datetime


class CaseDetail(BaseModel):
    case_id: str
    vendor: str
    status: str
    record: DecisionRecord
    report: Report
    contracts: list[ExecutionContract]
    reviews: list[dict]
    trace_path: str


def _store() -> Store:
    return Store()


@router.get("")
def list_cases() -> list[QueueItem]:
    bundles = sorted(
        _store().list(order="recent"),
        key=lambda bundle: (-bundle.decision.residual_risk, bundle.created_at, bundle.case_id),
    )
    return [
        QueueItem(
            case_id=bundle.case_id,
            vendor=bundle.legal_name,
            outcome=bundle.decision.outcome,
            tier=bundle.decision.tier,
            residual_risk=bundle.decision.residual_risk,
            status=bundle.status,
            created=bundle.created_at,
        )
        for bundle in bundles
    ]


@router.get("/{case_id}")
def get_case(case_id: str) -> CaseDetail:
    store = _store()
    bundle = store.get(case_id)
    return CaseDetail(
        case_id=bundle.case_id,
        vendor=bundle.legal_name,
        status=bundle.status,
        record=bundle.decision,
        report=bundle.report,
        contracts=store.contracts_for(case_id),
        reviews=store.reviews_for(case_id),
        trace_path=bundle.log_file,
    )


@router.get("/{case_id}/trace")
def get_trace(case_id: str) -> list[dict]:
    bundle = _store().get(case_id)
    path = Path(bundle.log_file)
    if not path.is_file():
        raise NotFound(f"trace for {case_id} not found")
    events: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ParseFailure(f"trace line is not JSON: {exc}") from exc
    return events


@router.post("/{case_id}/replay")
def replay_case(case_id: str) -> ReplayResult:
    return replay(case_id, store=_store())


@router.get("/{case_id}/dossier")
def get_dossier(
    case_id: str,
    dossier_format: Literal["md", "html"] = Query(default="md", alias="format"),
) -> Response:
    body = render(_store().get(case_id), dossier_format)
    media = "text/markdown" if dossier_format == "md" else "text/html"
    return Response(content=body, media_type=media)
