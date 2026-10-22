from __future__ import annotations

from app.policy import load_default
from app.policy.engine import decide
from app.schemas.report import Report
from tests.unit.policy.support import facts_from, policy_inputs, profile

CAPABILITIES_MAP = {
    "APPROVE": ["procurement.approval.record"],
    "APPROVE_WITH_CONDITIONS": ["procurement.approval.record"],
    "REQUEST_INFO": ["outbox.email.draft"],
    "ESCALATE": ["itsm.ticket.create"],
    "DECLINE": ["procurement.decline.record"],
}


def sample_report() -> Report:
    return Report(
        summary="template:v1 summary",
        rationale=[],
        recommended_actions=[],
        limitations=[],
        generator="template:v1",
    )


def t1_approve_decision():
    policy, calibration = load_default()
    facts = facts_from({})
    inputs = policy_inputs(
        facts,
        tier_profile=profile(categories=["special_category"], criticality="high", spend=500_000.0),
        confidence_value=0.95,
    )
    return decide(inputs, policy, calibration), policy
