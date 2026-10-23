"""P2-T34: one counterfactual per control, with unresolved contradictions merged in."""

from __future__ import annotations

import pytest

from app.policy.counterfactuals import fragile_controls
from app.policy.engine import decide
from app.policy.loader import load_default
from tests.unit.policy.support import contradiction, facts_from, make_fact, policy_inputs, profile

pytestmark = pytest.mark.p2c


def test_p2_t34_counterfactuals_match_policy() -> None:
    """P2-T34: failing controls and unresolved contradictions share one row per control."""
    policy, calibration = load_default()
    facts = facts_from(
        {
            "mfa.admin_enforced": (False, "FALSE"),
            "access.review_interval_days": None,
            "breach.notify_hours": None,
            "breach.notify_hours_claimed": (24, "TRUE"),
            "vendor.data_categories": (["personal"], "TRUE"),
        }
    )
    contradictions = [
        contradiction("residency.regions", severity="material", resolved=False, claim_id="CL-open"),
        contradiction(
            "subprocessors.disclosed",
            severity="minor",
            resolved=False,
            control_id="C10",
            claim_id="CL-minor",
        ),
        contradiction(
            "incidents.vendor_reported_24m",
            severity="material",
            resolved=True,
            control_id="C06",
            claim_id="CL-done",
        ),
    ]
    record = decide(
        policy_inputs(
            facts,
            contradictions=contradictions,
            tier_profile=profile(contract_status="draft"),
        ),
        policy,
        calibration,
    )
    by_control = {control.id: control for control in policy.controls}
    ids = [row.control_id for row in record.counterfactuals]
    assert len(ids) == len(set(ids))
    by_id = {row.control_id: row for row in record.counterfactuals}

    c01 = by_id["C01"]
    assert c01.from_state == "FALSE"
    assert c01.to_state == "TRUE"
    assert c01.evidence_required == by_control["C01"].evidence_required
    assert c01.question_ids == by_control["C01"].question_ids
    c03 = by_id["C03"]
    assert c03.from_state == "UNKNOWN"
    assert c03.evidence_required == by_control["C03"].evidence_required
    assert c03.question_ids == ["Q04"]
    assert "C07" not in by_id

    c09 = by_id["C09"]
    assert c09.evidence_required == [
        *by_control["C09"].evidence_required,
        "resolve contradiction on residency.regions",
    ]
    assert c09.question_ids == by_control["C09"].question_ids
    c10 = by_id["C10"]
    assert c10.evidence_required == [
        *by_control["C10"].evidence_required,
        "resolve contradiction on subprocessors.disclosed",
    ]
    assert c10.question_ids == by_control["C10"].question_ids
    assert "resolve contradiction on incidents.vendor_reported_24m" not in {
        item for row in record.counterfactuals for item in row.evidence_required
    }


def test_p2_t34_fragile_controls_are_single_vendor_claims() -> None:
    """P2-T34: a TRUE control backed by one vendor claim is fragile."""
    from app.schemas.decision import ControlResult

    vendor = make_fact(
        "mfa.admin_enforced",
        True,
        "TRUE",
        fact_id="F-vendor",
        control_id="C01",
        claim_ids=["CL-1"],
        kind="vendor_answer",
    )
    remote = make_fact(
        "mfa.remote_enforced",
        True,
        "TRUE",
        fact_id="F-remote",
        control_id="C01",
        claim_ids=["CL-1"],
        kind="vendor_document",
    )
    sor = make_fact("crypto.at_rest", True, "TRUE", fact_id="F-sor", control_id="C04")
    controls = [
        ControlResult(
            control_id="C01",
            title="MFA",
            required=True,
            state="TRUE",
            fact_ids=["F-vendor", "F-remote"],
            rule_id="C01",
            weight=3,
        ),
        ControlResult(
            control_id="C04",
            title="Crypto",
            required=True,
            state="TRUE",
            fact_ids=["F-sor"],
            rule_id="C04",
            weight=2,
        ),
    ]
    assert fragile_controls(controls, [vendor, remote, sor]) == ["C01"]
