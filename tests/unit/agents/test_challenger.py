"""P3-T7: the Challenger can never upgrade an outcome; invalid challenges are rejected."""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given, seed, settings
from hypothesis import strategies as st

from app.agents.challenger import apply_challenge, validate_challenge
from app.agents.llm_schemas import ChallengeOut
from app.state import ChallengeResult
from tests.unit.agents.support import baseline_facts, record_for

pytestmark = pytest.mark.p3

RANK = {"APPROVE": 0, "APPROVE_WITH_CONDITIONS": 1, "REQUEST_INFO": 2, "ESCALATE": 3, "DECLINE": 4}
BASE = record_for(baseline_facts())
KNOWN_FACTS = {f.fact_id for f in BASE.facts}
ALLOWED_QUERIES = {"Q_SUBMISSION_DOCUMENTS", "Q_VENDOR_CONTRACT", "Q_VENDOR_INCIDENTS"}

challenges = st.builds(
    ChallengeOut,
    action=st.sampled_from(["accept", "re_plan", "escalate"]),
    category=st.sampled_from(
        ["uncorroborated_claim", "stale_evidence", "precedent_mismatch", "scope_gap", "other"]
    ),
    cited_fact_ids=st.lists(st.sampled_from(sorted(KNOWN_FACTS) + ["F-C99-9", "F-X-1"]), max_size=3),
    suggested_query_ids=st.lists(st.sampled_from(sorted(ALLOWED_QUERIES) + ["Q_NOPE", "DROP"]), max_size=3),
    rationale=st.text(max_size=80),
)


@seed(20261022)
@settings(max_examples=300, deadline=None)
@given(
    outcome=st.sampled_from(sorted(RANK)), out=challenges, loops_left=st.integers(min_value=0, max_value=1)
)
def test_p3_t7_challenger_cannot_upgrade(outcome: str, out: ChallengeOut, loops_left: int) -> None:
    candidate = BASE.model_copy(update={"outcome": outcome})
    result = validate_challenge(
        out, candidate, known_fact_ids=KNOWN_FACTS, allowed_query_ids=ALLOWED_QUERIES, loops_left=loops_left
    )
    final = apply_challenge(candidate, result)
    assert RANK[final.outcome] >= RANK[candidate.outcome]
    if result.action == "re_plan":
        assert loops_left == 1
        assert result.suggested_query_ids and set(result.suggested_query_ids) <= ALLOWED_QUERIES


def _validate(**fields: Any) -> ChallengeResult:
    out = ChallengeOut(
        **{
            "action": "escalate",
            "category": "uncorroborated_claim",
            "cited_fact_ids": ["F-C01-1"],
            "suggested_query_ids": [],
            "rationale": "MFA rests on one answer.",
            **fields,
        }
    )
    return validate_challenge(
        out, BASE, known_fact_ids=KNOWN_FACTS, allowed_query_ids=ALLOWED_QUERIES, loops_left=1
    )


def test_p3_t7_unknown_cited_fact_is_rejected() -> None:
    result = _validate(cited_fact_ids=["F-C01-1", "F-C99-9"])
    assert "unknown_fact_id" in result.rejected
    assert result.action == "accept"
    assert apply_challenge(BASE, result).outcome == BASE.outcome


def test_p3_t7_other_category_can_only_accept() -> None:
    result = _validate(category="other")
    assert result.action == "accept"
    assert "other_must_accept" in result.rejected


def test_p3_t7_valid_escalation_goes_through_force_escalate() -> None:
    result = _validate()
    assert result.action == "escalate" and not result.rejected
    final = apply_challenge(BASE, result)
    assert final.outcome == "ESCALATE"
    assert final.escalation_reasons[-1].startswith("CHALLENGE_")
    assert final.record_sha256 != BASE.record_sha256


def test_p3_t7_replan_needs_new_valid_ids() -> None:
    assert _validate(action="re_plan", suggested_query_ids=["Q_NOPE"]).action != "re_plan"
    ok = _validate(action="re_plan", suggested_query_ids=["Q_SUBMISSION_DOCUMENTS", "Q_NOPE"])
    assert ok.action == "re_plan" and ok.suggested_query_ids == ["Q_SUBMISSION_DOCUMENTS"]
