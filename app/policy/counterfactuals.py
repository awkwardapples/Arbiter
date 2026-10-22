"""What would have to change for a required control to pass."""

from __future__ import annotations

from app.policy.loader import Policy
from app.schemas.decision import ControlResult, Counterfactual
from app.schemas.evidence import Contradiction, Fact

_VENDOR_KINDS = frozenset({"vendor_answer", "vendor_document"})


def compute_counterfactuals(
    controls: list[ControlResult],
    contradictions: list[Contradiction],
    policy: Policy,
) -> list[Counterfactual]:
    by_id = {control.id: control for control in policy.controls}
    state_by_id = {control.control_id: control.state for control in controls}
    rows: list[Counterfactual] = []
    for control in controls:
        if control.state == "TRUE" or not control.required:
            continue
        spec = by_id[control.control_id]
        rows.append(
            Counterfactual(
                control_id=control.control_id,
                from_state=control.state,
                to_state="TRUE",
                evidence_required=list(spec.evidence_required),
                question_ids=list(spec.question_ids),
            )
        )
    unresolved = sorted(
        (item for item in contradictions if not item.resolved),
        key=lambda item: (item.key, item.claim_id),
    )
    for item in unresolved:
        spec = by_id.get(item.control_id)
        rows.append(
            Counterfactual(
                control_id=item.control_id,
                from_state=state_by_id.get(item.control_id, "FALSE"),
                to_state="TRUE",
                evidence_required=[f"resolve contradiction on {item.key}"],
                question_ids=list(spec.question_ids) if spec is not None else [],
            )
        )
    return rows


def fragile_controls(controls: list[ControlResult], facts: list[Fact]) -> list[str]:
    by_fact = {fact.fact_id: fact for fact in facts}
    fragile: list[str] = []
    for control in controls:
        if not control.required or control.state != "TRUE" or control.conditional:
            continue
        used = [by_fact[fact_id] for fact_id in control.fact_ids if fact_id in by_fact]
        if not used or not _single_vendor_claim(used):
            continue
        fragile.append(control.control_id)
    return fragile


def _single_vendor_claim(facts: list[Fact]) -> bool:
    claim_ids: set[str] = set()
    for fact in facts:
        if not fact.provenance or any(item.kind not in _VENDOR_KINDS for item in fact.provenance):
            return False
        if len(fact.derived_from_claims) != 1:
            return False
        claim_ids.add(fact.derived_from_claims[0])
    return len(claim_ids) == 1
