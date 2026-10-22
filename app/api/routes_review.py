"""Review and memory routes (lane P4-A)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.actions.contracts import add_approval, issue
from app.actions.executor import execute
from app.agents.reporter import template_report
from app.audit.chain import AuditChain
from app.canon import sha256_hex
from app.errors import PolicyIneligible
from app.memory import precedents
from app.memory.keeper import shared_hmem
from app.orchestrator import _CAPABILITIES
from app.policy.loader import load_default
from app.schemas.api import ReviewRequest
from app.schemas.decision import PrecedentRef
from app.store import Store

router = APIRouter(tags=["review"])


class EligibilityOut(BaseModel):
    eligible: bool
    reasons: list[str] = Field(default_factory=list)


class ReviewResponse(BaseModel):
    review_id: str
    human_decision: dict[str, Any]
    contract: dict[str, Any]
    precedent: PrecedentRef | None = None
    eligibility: EligibilityOut


def _var_dir() -> Path:
    return Path("var")


def _audit() -> AuditChain:
    return AuditChain(_var_dir() / "audit.db")


def _clock() -> datetime:
    return datetime.now(UTC)


@router.post("/cases/{case_id}/review")
def submit_review(
    case_id: str,
    body: ReviewRequest,
    dry_run: bool = Query(default=False),
) -> ReviewResponse | EligibilityOut:
    policy, _cal = load_default()
    store = Store(_var_dir())
    bundle = store.get(case_id)
    eligible, reasons = precedents.check_eligibility(body, bundle, policy)
    if dry_run:
        return EligibilityOut(eligible=eligible, reasons=reasons)
    if body.create_precedent and not eligible:
        raise PolicyIneligible("precedent ineligible", reasons=reasons)

    review_id = f"rev-{uuid.uuid4().hex[:12]}"
    machine = bundle.decision
    human = machine.model_copy(
        update={
            "outcome": body.decision,
            "outcome_reasons": ["HUMAN_REVIEW"],
            "run_id": review_id,
            "created_at": _clock(),
        }
    )
    human = human.model_copy(
        update={"record_sha256": sha256_hex(human.model_dump(exclude={"record_sha256"}))}
    )
    store.put_human_decision(human)
    report = template_report(human)
    contract = issue(
        human,
        report,
        capabilities_map=_CAPABILITIES,
        policy=policy,
        trace_id=review_id,
        registry_version=1,
        now=_clock(),
    )
    contract = add_approval(
        contract,
        by=body.reviewer,
        role=body.role,
        decision="approve",
        rationale=body.rationale,
        now=_clock(),
        policy=policy,
    )
    store.put_contract(contract)
    result = execute(
        contract,
        now=_clock(),
        policy=policy,
        outbox_dir=_var_dir() / "outbox",
        payload={"review_id": review_id, "machine_run_id": machine.run_id},
    )
    store.put_contract(result.contract)

    hmem = shared_hmem(_var_dir(), _clock)
    audit = _audit()
    precedent_ref: PrecedentRef | None = None
    if body.create_precedent:
        precedent_ref = precedents.record_precedent(
            body,
            bundle,
            hmem=hmem,
            audit=audit,
            precedents_path=_var_dir() / "precedents.json",
            run_id=review_id,
            policy=policy,
        )

    for ref in machine.precedents_considered:
        if ref.precedent_id.startswith("P-"):
            kind = "helpful" if body.decision == machine.outcome else "wrong"
            precedents.feedback(
                ref.precedent_id,
                kind,
                hmem=hmem,
                audit=audit,
                precedents_path=_var_dir() / "precedents.json",
                case_id=case_id,
            )

    review_row = {
        "review_id": review_id,
        "case_id": case_id,
        "reviewer": body.reviewer,
        "role": body.role,
        "decision": body.decision,
        "rationale": body.rationale,
        "machine_run_id": machine.run_id,
        "human_run_id": review_id,
        "create_precedent": body.create_precedent,
    }
    store.put_review(review_row)
    audit.append("review_recorded", case_id, {"review_id": review_id, "decision": body.decision})
    audit.close()

    return ReviewResponse(
        review_id=review_id,
        human_decision=human.model_dump(mode="json"),
        contract=result.contract.model_dump(mode="json"),
        precedent=precedent_ref,
        eligibility=EligibilityOut(eligible=True, reasons=[]),
    )


@router.get("/memory/precedents")
def list_precedents() -> list[dict[str, Any]]:
    hmem = shared_hmem(_var_dir(), _clock)
    return precedents.list_precedents(hmem=hmem, precedents_path=_var_dir() / "precedents.json")
