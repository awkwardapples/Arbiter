"""P14A-T1, T2, T3, T4: reasons, coverage, counterfactuals, calibration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.confidence import compute
from app.policy.engine import decide
from app.policy.loader import load_default
from app.schemas.case import CaseInput
from app.state import new_state
from tests.e2e.test_label_oracle import _inputs, _truth
from tests.unit.agents.support import AS_OF, baseline_facts
from tests.unit.policy.support import contradiction, facts_from, policy_inputs, profile

pytestmark = pytest.mark.p14a

ROOT = Path(__file__).resolve().parents[3]
_ALWAYS = "ALL_REQUIRED_CONTROLS_MET"


def _assert_always_reason(outcome: str, reasons: list[str]) -> None:
    if _ALWAYS not in reasons:
        return
    assert outcome == "APPROVE"
    assert reasons == [_ALWAYS]


def test_p14a_t1_label_oracle_omits_always_unless_it_decided() -> None:
    """P14A-T1: the 32 label-oracle cases list ALL_REQUIRED_CONTROLS_MET only when it decided."""
    policy, calibration = load_default()
    rows = _truth()
    assert len(rows) >= 32
    records = [decide(_inputs(row), policy, calibration) for row in rows]
    for record in records:
        _assert_always_reason(record.outcome, record.outcome_reasons)
    assert getattr(records[0], "policy_engine_version", None) == "1.1"


def _case(facts: list) -> object:
    state = new_state(
        CaseInput(vendor_id="VND-0099"),
        run_id="p14a-coverage",
        as_of=AS_OF,
        mode={"data": "duckdb", "llm": "offline"},
        budget_deadline=float("inf"),
    )
    state.facts = facts
    return state


def test_p14a_t2_unknown_control_is_not_covered() -> None:
    """P14A-T2: C01 UNKNOWN lowers coverage and is named; a verified case is fully covered."""
    policy, calibration = load_default()
    partial = [fact for fact in baseline_facts() if fact.key != "mfa.remote_enforced"]
    unknown = compute(_case(partial), policy, calibration, tier="T3")
    assert unknown.signals["coverage"] < 1
    assert "C01" in unknown.unknown_controls

    full = compute(_case(baseline_facts()), policy, calibration, tier="T3")
    assert full.signals["coverage"] == 1.0
    assert full.unknown_controls == []


def test_p14a_t3_one_counterfactual_per_control() -> None:
    """P14A-T3: contradiction text is merged into that control's single counterfactual."""
    policy, calibration = load_default()
    facts = facts_from(
        {
            "mfa.admin_enforced": (False, "FALSE"),
            "access.review_interval_days": None,
            "breach.notify_hours": None,
            "breach.notify_hours_claimed": (24, "TRUE"),
            "vendor.data_categories": (["personal"], "TRUE"),
            "residency.regions": (["US"], "TRUE"),
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
        policy_inputs(facts, contradictions=contradictions, tier_profile=profile(contract_status="draft")),
        policy,
        calibration,
    )
    ids = [row.control_id for row in record.counterfactuals]
    assert len(ids) == len(set(ids))
    by_id = {row.control_id: row for row in record.counterfactuals}
    c09 = by_id["C09"]
    assert "CLM hosting clause UK/EU" in c09.evidence_required
    assert "resolve contradiction on residency.regions" in c09.evidence_required
    assert c09.question_ids == ["Q10", "Q11"]
    c10 = by_id["C10"]
    assert "resolve contradiction on subprocessors.disclosed" in c10.evidence_required
    assert c10.question_ids == ["Q12"]
    merged = {item for row in record.counterfactuals for item in row.evidence_required}
    assert "resolve contradiction on incidents.vendor_reported_24m" not in merged


def test_p14a_t4_calibration_has_zero_unsafe_approvals() -> None:
    """P14A-T4: the active calibration records zero unsafe approvals."""
    active = (ROOT / "policy" / "calibration" / "ACTIVE").read_text(encoding="utf-8").strip()
    payload = json.loads((ROOT / "policy" / "calibration" / f"{active}.json").read_text(encoding="utf-8"))
    assert payload["calibration_results"]["unsafe_approvals"] == 0
