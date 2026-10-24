"""Label oracle: the policy engine's control evaluation on truth facts (same construction as P3-T16)."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.policy.engine import decide
from app.policy.loader import load_default
from app.schemas.common import Provenance
from app.schemas.decision import ConfidenceBreakdown, DecisionRecord, PolicyInputs, TierProfile
from app.schemas.evidence import Contradiction, Fact, GuardFlag


def truth_record(row: dict[str, Any], *, as_of: date) -> DecisionRecord:
    """Decide on a truth row with full confidence, so only facts and contradictions drive controls."""
    policy, calibration = load_default()
    facts = [
        Fact(
            fact_id=f"F-T-{i}",
            control_id="TRUTH",
            key=key,
            value=spec["value"],
            state=spec["state"],
            provenance=[Provenance(kind=spec["source"])],
        )
        for i, (key, spec) in enumerate(sorted(row["facts"].items()), start=1)
    ]
    contradictions = [
        Contradiction(
            key=c["key"],
            control_id=c["control_id"],
            claim_id=f"CL-T-{i}",
            claim_value=None,
            sor_value=None,
            sor_provenance=Provenance(kind="system_of_record"),
            severity=c["severity"],
        )
        for i, c in enumerate(row["contradictions"], start=1)
    ]
    flags = (
        [GuardFlag(kind="injection", score=1.0, level="block", segment_id="truth")]
        if row["guard_blocked"]
        else []
    )
    inputs = PolicyInputs(
        case_id=row["case_ref"],
        run_id="oracle",
        as_of=as_of,
        profile=TierProfile(**row["profile"]),
        facts=facts,
        contradictions=contradictions,
        guard_flags=flags,
        confidence=ConfidenceBreakdown(value=1.0, gate=0.0, abstained=False, signals={}),
    )
    return decide(inputs, policy, calibration)


def expected_controls(row: dict[str, Any], *, as_of: date) -> dict[str, list[str]]:
    record = truth_record(row, as_of=as_of)
    failing = [
        c.control_id for c in record.controls if c.required and c.state == "FALSE" and not c.exception_applied
    ]
    unknown = [c.control_id for c in record.controls if c.required and c.state == "UNKNOWN"]
    return {
        "expected_failing_controls": sorted(failing),
        "expected_unknown_controls": sorted(unknown),
        "expected_contradiction_keys": sorted({c["key"] for c in row["contradictions"]}),
    }
