"""Decision confidence (master spec §8.6): weighted evidence-quality signals, computed before `decide`."""

from __future__ import annotations

from app.policy.dsl import evaluate, referenced_keys
from app.policy.loader import Calibration, Policy
from app.schemas.common import Tier
from app.schemas.decision import ConfidenceBreakdown
from app.schemas.evidence import Fact
from app.state import CaseState

_VERIFIED_KINDS = frozenset({"system_of_record", "public_feed"})
_CLAIM_KINDS = frozenset({"vendor_answer", "vendor_document"})


def _verified(fact: Fact, warned: set[str]) -> bool:
    if fact.state == "UNKNOWN" or fact.dq_flags:
        return False
    for prov in fact.provenance:
        if prov.kind in _VERIFIED_KINDS:
            return True
        if prov.kind in _CLAIM_KINDS and (prov.answer_ref is None or prov.answer_ref not in warned):
            return True
    return False


def compute(
    state: CaseState,
    policy: Policy,
    calibration: Calibration,
    *,
    tier: Tier,
    precedent_alignment: float = 1.0,
) -> ConfidenceBreakdown:
    index = {f.key: f for f in state.facts}
    warned = {s.ref for s in state.segments if s.kind == "answer" and s.guard.level == "warn"}
    required = [
        c
        for c in policy.controls
        if tier in c.required_for
        and (c.applies_when is None or evaluate(policy.conditions[c.applies_when], index) != "FALSE")
    ]
    covered = sum(
        1
        for c in required
        if any(key in index and _verified(index[key], warned) for key in referenced_keys(c.rule))
    )
    coverage = covered / len(required) if required else 1.0
    grounded = [c for c in state.claims if c.grounded]
    grounding = len(grounded) / len(state.claims) if state.claims else 1.0
    results = list(state.executed_queries.values())
    fell_back = sum(1 for r in results if r.fallback_from)
    if not fell_back:
        source_health = 1.0
    elif fell_back * 2 > len(results):
        source_health = 0.4
    else:
        source_health = 0.7
    material = any(c.severity == "material" and not c.resolved for c in state.contradictions)
    signals = {
        "coverage": round(coverage, 4),
        "grounding": round(grounding, 4),
        "source_health": source_health,
        "contradiction_free": 0.0 if material else 1.0,
        "precedent_alignment": precedent_alignment,
    }
    value = sum(calibration.weights.get(name, 0.0) * score for name, score in signals.items())
    return ConfidenceBreakdown(
        value=round(value, 4), gate=calibration.gate(tier), abstained=False, signals=signals
    )
