"""P2-T33: a precedent exception needs all six criteria."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.policy.engine import decide
from app.policy.loader import load_default
from tests.unit.policy.support import AS_OF, c05_false_facts, facts_from, policy_inputs, precedent

pytestmark = pytest.mark.p2c


@pytest.fixture(scope="module")
def bundle():
    return load_default()


def _record(bundle, *, facts_spec=None, candidate=None):
    policy, calibration = bundle
    facts = facts_from(facts_spec if facts_spec is not None else c05_false_facts())
    candidates = [] if candidate is None else [candidate]
    return decide(policy_inputs(facts, precedents=candidates), policy, calibration)


def _ref(record, precedent_id: str = "P-0001"):
    return next(item for item in record.precedents_considered if item.precedent_id == precedent_id)


def test_p2_t33_qualifying_precedent_applies(bundle) -> None:
    """P2-T33: all six criteria apply the C05 exception."""
    record = _record(bundle, candidate=precedent())
    ref = _ref(record)
    control = next(item for item in record.controls if item.control_id == "C05")
    assert ref.applied is True
    assert ref.failed_criteria == []
    assert control.state == "TRUE"
    assert control.conditional is True
    assert control.exception_applied == "P-0001"
    assert record.outcome == "APPROVE_WITH_CONDITIONS"
    assert record.exceptions_applied == ["P-0001"]


@pytest.mark.parametrize(
    ("label", "facts_spec", "candidate", "code"),
    [
        ("allowed", c05_false_facts(), precedent(control_id="C01"), "exception_not_allowed"),
        (
            "mitigation",
            {**c05_false_facts(), "assurance.bridge_letter_current": (False, "FALSE")},
            precedent(),
            "mitigation_fact",
        ),
        ("reviewer", c05_false_facts(), precedent(reviewer_role="tprm_analyst"), "reviewer_authority"),
        (
            "age",
            c05_false_facts(),
            precedent(created_as_of=AS_OF - timedelta(days=366)),
            "precedent_age",
        ),
        ("retrieval", c05_false_facts(), precedent(hmem_confidence=0.69), "retrieval_quality"),
        ("tier", c05_false_facts(), precedent(tier="T3"), "tier_risk"),
    ],
)
def test_p2_t33_each_criterion_blocks(bundle, label: str, facts_spec, candidate, code: str) -> None:
    """P2-T33: mutating each of the six criteria blocks the exception."""
    record = _record(bundle, facts_spec=facts_spec, candidate=candidate)
    ref = _ref(record)
    assert ref.applied is False, label
    assert code in ref.failed_criteria
    assert record.exceptions_applied == []
    assert record.outcome != "APPROVE_WITH_CONDITIONS"
