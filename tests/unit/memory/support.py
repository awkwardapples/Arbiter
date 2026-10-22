"""Fixtures for P4-A memory unit tests."""

from __future__ import annotations

from datetime import UTC, datetime

from app.policy.loader import load_default
from app.schemas.api import ReviewRequest
from app.schemas.case import CaseInput
from app.schemas.decision import TierProfile
from app.store import CaseBundle
from tests.unit.policy.support import c05_false_facts, facts_from, policy_inputs


def s12_review() -> ReviewRequest:
    return ReviewRequest(
        reviewer="lead@example.com",
        role="tprm_lead",
        decision="APPROVE_WITH_CONDITIONS",
        rationale="Accept bridge letter as mitigation for missing SOC report.",
        mitigations=["bridge_letter"],
        create_precedent=True,
    )


def minimal_bundle(*, tier: str = "T2", category: str = "HR SaaS") -> CaseBundle:
    policy, calibration = load_default()
    facts = facts_from(c05_false_facts())
    inputs = policy_inputs(
        facts,
        tier_profile=TierProfile(
            data_categories=["personal"],
            criticality="low",
            annual_spend_gbp=45_000.0,
            contract_status="signed",
            vendor_category=category,
        ),
    )
    from app.policy.engine import decide

    record = decide(inputs, policy, calibration)
    record = record.model_copy(update={"tier": tier, "case_id": "CASE-0011", "run_id": "run-test-0011"})
    from app.schemas.report import Report

    report = Report(
        summary="test",
        rationale=[],
        recommended_actions=[],
        limitations=[],
        generator="template:v1",
    )
    return CaseBundle(
        case_id=record.case_id,
        run_id=record.run_id,
        created_at=datetime.now(UTC),
        status="success",
        mode={"data": "duckdb", "llm": "offline"},
        input=CaseInput(vendor_id="VND-0011"),
        vendor_ref="VND-0011",
        legal_name="Marrowgate Analytics Ltd",
        decision=record,
        report=report,
        log_file="logs/trace-test.jsonl",
    )
