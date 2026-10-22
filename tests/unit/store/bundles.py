"""Builders for P4-B store and API tests. Not a production path."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from app.actions.contracts import issue
from app.agents.reporter import template_report
from app.policy.loader import load_default
from app.schemas.case import CaseInput
from app.schemas.common import Outcome
from app.schemas.contract import ExecutionContract
from app.schemas.decision import DecisionRecord
from app.store import CaseBundle


def make_bundle(
    case_id: str,
    *,
    residual_risk: int = 10,
    created_at: datetime | None = None,
    outcome: Outcome = "ESCALATE",
    legal_name: str = "Queue Vendor Ltd",
) -> CaseBundle:
    created_at = created_at or datetime(2026, 10, 1, tzinfo=UTC)
    record = DecisionRecord.safe_escalation(
        case_id=case_id,
        run_id=f"run-{case_id}",
        as_of=date(2026, 10, 22),
        reason="TEST",
        policy_version="1.0.0",
        policy_sha256="abc",
        calibration_version="cal-initial",
    )
    record = record.model_copy(update={"outcome": outcome, "residual_risk": residual_risk, "tier": "T2"})
    return CaseBundle(
        case_id=case_id,
        run_id=record.run_id,
        created_at=created_at,
        status="success",
        mode={"data": "duckdb", "llm": "offline"},
        input=CaseInput(vendor_id="VND-0001"),
        vendor_ref="VND-0001",
        legal_name=legal_name,
        decision=record,
        first_decision=record,
        report=template_report(record),
        contract_ids=[],
        artifacts=["var/outbox/procurement/placeholder.json"],
        log_file=f"logs/trace-{case_id}.jsonl",
        limitations=["synthetic"],
    )


def issued_decline(case_id: str, *, now: datetime | None = None) -> ExecutionContract:
    """A signed DECLINE contract that still needs tprm_lead. Expires seven days after `now`."""
    issued_at = now or datetime.now(UTC)
    record = DecisionRecord.safe_escalation(
        case_id=case_id,
        run_id=f"run-{case_id}",
        as_of=date(2026, 10, 22),
        reason="TEST",
        policy_version="1.0.0",
        policy_sha256="abc",
        calibration_version="cal-initial",
    ).model_copy(update={"outcome": "DECLINE", "case_id": case_id})
    policy, _calibration = load_default()
    return issue(
        record,
        template_report(record),
        capabilities_map={},
        policy=policy,
        trace_id="trace-test",
        registry_version=1,
        now=issued_at,
    )


def approval_body(*, role: str, decision: str = "approve", rationale: str | None = None) -> dict[str, str]:
    return {
        "by": "reviewer",
        "role": role,
        "decision": decision,
        "rationale": rationale
        or "Recorded after a full reading of the decision record and the cited controls.",
    }


def days(n: int) -> timedelta:
    return timedelta(days=n)
