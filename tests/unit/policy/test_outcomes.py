"""P2-T31 and P2-T32: outcome order and contract-stage approvals."""

from __future__ import annotations

import pytest

from app.policy.engine import decide, required_approvals
from tests.unit.policy.support import (
    block_flag,
    c05_false_facts,
    contradiction,
    facts_from,
    policy_inputs,
    precedent,
    profile,
)

pytestmark = pytest.mark.p2c

C07_TEXT = "Contract must include a breach-notification clause of 72 hours or less before go-live."
C08_TEXT = "Execute the Data Processing Agreement before any personal data is shared."


@pytest.fixture(scope="module")
def bundle():
    from app.policy.loader import load_default

    return load_default()


def _decide(bundle, facts, **kwargs):
    policy, calibration = bundle
    return decide(policy_inputs(facts, **kwargs), policy, calibration)


def test_p2_t31_outcome_rule_order(bundle) -> None:
    """P2-T31: decline beats injection, then contradiction, hard escalate, failure, unknown, confidence, conditional, approve."""
    policy, _calibration = bundle
    expected_order = [rule.reason for rule in policy.outcome_rules]

    decline = _decide(
        bundle,
        facts_from({"sanctions.watchlist_matches": (2, "TRUE")}),
        guard_flags=[block_flag()],
    )
    assert decline.outcome == "DECLINE"
    assert decline.outcome_reasons[0] == "HARD_GATE_DECLINE"

    injection = _decide(
        bundle,
        facts_from({}),
        guard_flags=[block_flag()],
        contradictions=[contradiction("residency.regions")],
    )
    assert injection.outcome == "ESCALATE"
    assert injection.outcome_reasons[0] == "UNTRUSTED_CONTENT_TAMPERING"

    contradicted = _decide(
        bundle,
        facts_from({"dpa.signed": (False, "FALSE"), "mfa.admin_enforced": (False, "FALSE")}),
        contradictions=[contradiction("residency.regions")],
    )
    assert contradicted.outcome == "ESCALATE"
    assert contradicted.outcome_reasons[0] == "CONTRADICTION"

    hard = _decide(
        bundle,
        facts_from({"dpa.signed": (False, "FALSE"), "mfa.admin_enforced": (False, "FALSE")}),
    )
    assert hard.outcome == "ESCALATE"
    assert hard.outcome_reasons[0] == "HARD_GATE_ESCALATE"

    failed = _decide(
        bundle,
        facts_from({"mfa.admin_enforced": (False, "FALSE"), "access.review_interval_days": None}),
    )
    assert failed.outcome == "ESCALATE"
    assert failed.outcome_reasons[0] == "CONTROL_FAILED"

    unknown = _decide(
        bundle,
        facts_from({"access.review_interval_days": None}),
        confidence_value=0.1,
    )
    assert unknown.outcome == "REQUEST_INFO"
    assert unknown.outcome_reasons[0] == "EVIDENCE_MISSING"

    low = _decide(
        bundle,
        facts_from(c05_false_facts()),
        confidence_value=0.1,
        precedents=[precedent()],
    )
    assert low.outcome == "ESCALATE"
    assert low.outcome_reasons[0] == "LOW_CONFIDENCE_ABSTAIN"
    assert low.confidence.abstained is True

    conditional = _decide(bundle, facts_from(c05_false_facts()), precedents=[precedent()])
    assert conditional.outcome == "APPROVE_WITH_CONDITIONS"
    assert conditional.outcome_reasons[0] == "CONDITIONS"

    approved = _decide(bundle, facts_from({}))
    assert approved.outcome == "APPROVE"
    assert approved.outcome_reasons == ["ALL_REQUIRED_CONTROLS_MET"]

    winners = [
        decline.outcome_reasons[0],
        injection.outcome_reasons[0],
        contradicted.outcome_reasons[0],
        hard.outcome_reasons[0],
        failed.outcome_reasons[0],
        unknown.outcome_reasons[0],
        low.outcome_reasons[0],
        conditional.outcome_reasons[0],
        approved.outcome_reasons[0],
    ]
    assert winners == expected_order


def test_p2_t32_contract_stage_conditions(bundle) -> None:
    """P2-T32: C07 and C08 contract-stage conditions approve with analyst approval."""
    facts = facts_from(
        {
            "breach.notify_hours": None,
            "breach.notify_hours_claimed": (48, "TRUE"),
            "dpa.signed": None,
            "dpa.vendor_commits": (True, "TRUE"),
        }
    )
    record = _decide(
        bundle,
        facts,
        tier_profile=profile(contract_status="draft"),
    )
    by_id = {control.control_id: control for control in record.controls}
    assert record.outcome == "APPROVE_WITH_CONDITIONS"
    assert by_id["C07"].conditional is True
    assert by_id["C07"].state == "TRUE"
    assert by_id["C07"].condition_text == C07_TEXT
    assert by_id["C08"].conditional is True
    assert by_id["C08"].condition_text == C08_TEXT
    assert C07_TEXT in record.conditions
    assert C08_TEXT in record.conditions
    policy, _calibration = bundle
    assert required_approvals(record, policy) == ["tprm_analyst"]
