"""P2-T34: counterfactuals are the failing required controls plus unresolved contradictions."""

from __future__ import annotations

import pytest

from app.policy.counterfactuals import fragile_controls
from app.policy.engine import decide
from app.policy.loader import load_default
from tests.unit.policy.support import contradiction, facts_from, make_fact, policy_inputs, profile

pytestmark = pytest.mark.p2c


def test_p2_t34_counterfactuals_match_policy() -> None:
    """P2-T34: non-TRUE required controls and unresolved contradictions, with policy evidence."""
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
    resolve = "resolve contradiction on "
    control_rows = [row for row in record.counterfactuals if not row.evidence_required[0].startswith(resolve)]
    contradiction_rows = [
        row for row in record.counterfactuals if row.evidence_required[0].startswith(resolve)
    ]

    assert [row.control_id for row in control_rows] == ["C01", "C03"]
    c01 = control_rows[0]
    assert c01.from_state == "FALSE"
    assert c01.to_state == "TRUE"
    assert c01.evidence_required == by_control["C01"].evidence_required
    assert c01.question_ids == by_control["C01"].question_ids
    c03 = control_rows[1]
    assert c03.from_state == "UNKNOWN"
    assert c03.evidence_required == by_control["C03"].evidence_required
    assert c03.question_ids == ["Q04"]
    assert all(row.control_id != "C07" for row in control_rows)

    assert [row.evidence_required for row in contradiction_rows] == [
        ["resolve contradiction on residency.regions"],
        ["resolve contradiction on subprocessors.disclosed"],
    ]
    assert contradiction_rows[0].question_ids == by_control["C09"].question_ids
    assert contradiction_rows[1].question_ids == by_control["C10"].question_ids
    assert "resolve contradiction on incidents.vendor_reported_24m" not in {
        row.evidence_required[0] for row in record.counterfactuals
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
