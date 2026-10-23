"""P2-T36: identical inputs hash identically, and escalation never undoes a decline."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.policy.engine import decide, force_escalate
from app.policy.loader import load_default
from tests.unit.policy.support import (
    AS_OF,
    block_flag,
    c05_false_facts,
    contradiction,
    facts_from,
    policy_inputs,
    precedent,
)

pytestmark = pytest.mark.p2c


def test_p2_t36_determinism_and_force_escalate() -> None:
    """P2-T36: hash ignores input order, created_at is as_of, reasons stay ordered, decline stays decline."""
    policy, calibration = load_default()
    spec = {
        "sanctions.watchlist_matches": (1, "TRUE"),
        "dpa.signed": (False, "FALSE"),
        "mfa.admin_enforced": (False, "FALSE"),
        "access.review_interval_days": None,
        **c05_false_facts(),
    }
    facts = facts_from(spec)
    contradictions = [contradiction("residency.regions", claim_id="CL-9")]
    flags = [block_flag()]
    candidates = [precedent()]
    first_inputs = policy_inputs(
        facts,
        confidence_value=0.1,
        contradictions=contradictions,
        guard_flags=flags,
        precedents=candidates,
    )
    shuffled = policy_inputs(
        list(reversed(facts)),
        confidence_value=0.1,
        contradictions=list(reversed(contradictions)),
        guard_flags=list(reversed(flags)),
        precedents=list(reversed(candidates)),
    )
    first = decide(first_inputs, policy, calibration)
    second = decide(shuffled, policy, calibration)
    assert first.record_sha256 == second.record_sha256
    assert first.created_at == datetime(AS_OF.year, AS_OF.month, AS_OF.day, tzinfo=UTC)
    assert first.outcome_reasons == [
        "HARD_GATE_DECLINE",
        "UNTRUSTED_CONTENT_TAMPERING",
        "CONTRADICTION",
        "HARD_GATE_ESCALATE",
        "CONTROL_FAILED",
        "EVIDENCE_MISSING",
        "LOW_CONFIDENCE_ABSTAIN",
        "CONDITIONS",
    ]
    assert first.outcome == "DECLINE"
    escalated = force_escalate(first, "challenger")
    assert escalated.outcome == "DECLINE"
    assert escalated.escalation_reasons == ["challenger"]
    assert escalated.record_sha256 != first.record_sha256
