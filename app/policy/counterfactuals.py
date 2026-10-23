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
    """One counterfactual per control. Contradiction text is merged into that control."""
    by_id = {control.id: control for control in policy.controls}
    state_by_id = {control.control_id: control.state for control in controls}
    rows: dict[str, Counterfactual] = {}
    order: list[str] = []

    def ensure(control_id: str) -> Counterfactual:
        existing = rows.get(control_id)
        if existing is not None:
            return existing
        spec = by_id.get(control_id)
        row = Counterfactual(
            control_id=control_id,
            from_state=state_by_id.get(control_id, "FALSE"),
            to_state="TRUE",
            evidence_required=list(spec.evidence_required) if spec is not None else [],
            question_ids=list(spec.question_ids) if spec is not None else [],
        )
        rows[control_id] = row
        order.append(control_id)
        return row

    for control in controls:
        if control.state == "TRUE" or not control.required:
            continue
        ensure(control.control_id)
    unresolved = sorted(
        (item for item in contradictions if not item.resolved),
        key=lambda item: (item.key, item.claim_id),
    )
    for item in unresolved:
        row = ensure(item.control_id)
        spec = by_id.get(item.control_id)
        question_ids = list(spec.question_ids) if spec is not None else []
        rows[item.control_id] = row.model_copy(
            update={
                "evidence_required": _dedupe(
                    [*row.evidence_required, f"resolve contradiction on {item.key}"]
                ),
                "question_ids": _dedupe([*row.question_ids, *question_ids]),
            }
        )
    return [rows[control_id] for control_id in order]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


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
