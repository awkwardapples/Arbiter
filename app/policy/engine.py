"""Map verified facts to an outcome. Pure: no clock and no I/O."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, time

from app.canon import sha256_hex
from app.errors import PolicyError
from app.policy.counterfactuals import compute_counterfactuals
from app.policy.dsl import evaluate, referenced_keys
from app.policy.loader import Calibration, Control, Policy
from app.policy.residual import residual_risk
from app.policy.tiering import tier
from app.schemas.common import Outcome, Tier
from app.schemas.decision import (
    ControlResult,
    DecisionRecord,
    PolicyInputs,
    PrecedentCandidate,
    PrecedentRef,
)
from app.schemas.evidence import Fact

_RANK: dict[Outcome, int] = {
    "APPROVE": 0,
    "APPROVE_WITH_CONDITIONS": 1,
    "REQUEST_INFO": 2,
    "ESCALATE": 3,
    "DECLINE": 4,
}
_TIER_RISK: dict[Tier, int] = {"T1": 3, "T2": 2, "T3": 1}
_MIN_CONFIDENCE = 0.70
_MIN_RELEVANCE = 0.35
_PASSING_DECISIONS = frozenset({"APPROVE", "APPROVE_WITH_CONDITIONS"})


class _View:
    def __init__(self, controls: list[ControlResult], inputs: PolicyInputs, gate: float) -> None:
        self.controls = controls
        self.inputs = inputs
        self.gate = gate


def decide(inputs: PolicyInputs, policy: Policy, calibration: Calibration) -> DecisionRecord:
    normalized = _normalize(inputs)
    indexed = _fact_index(normalized.facts)
    case_tier, inherent = tier(normalized.profile, policy)
    selected = [control for control in policy.controls if _applies(control, case_tier, indexed, policy)]
    controls = [_evaluate_control(control, indexed) for control in selected]
    controls = [
        _apply_contract(control, result, normalized, indexed)
        for control, result in zip(selected, controls, strict=True)
    ]
    controls, considered = _apply_precedents(controls, normalized, policy, case_tier, indexed)
    view = _View(controls, normalized, calibration.gate(case_tier))
    matched = [rule for rule in policy.outcome_rules if _PREDICATES[rule.when](view)]
    if not matched:
        raise PolicyError("invalid policy document: no outcome rule matched")
    outcome = _outcome(matched[0].outcome)
    confidence = normalized.confidence.model_copy(update={"gate": view.gate, "abstained": _below_gate(view)})
    record = DecisionRecord(
        case_id=normalized.case_id,
        run_id=normalized.run_id,
        policy_version=policy.version,
        policy_sha256=sha256_hex(policy),
        calibration_version=calibration.version,
        tier=case_tier,
        inherent_risk_score=inherent,
        facts=list(normalized.facts),
        controls=controls,
        contradictions=list(normalized.contradictions),
        outcome=outcome,
        outcome_reasons=[rule.reason for rule in matched],
        counterfactuals=compute_counterfactuals(controls, list(normalized.contradictions), policy),
        precedents_considered=considered,
        exceptions_applied=[item.exception_applied for item in controls if item.exception_applied],
        residual_risk=residual_risk(case_tier, controls, normalized, policy),
        confidence=confidence,
        conditions=[item.condition_text for item in controls if item.conditional and item.condition_text],
        as_of=normalized.as_of,
        policy_inputs=normalized,
        created_at=datetime.combine(normalized.as_of, time.min, tzinfo=UTC),
        record_sha256="",
    )
    return record.model_copy(update={"record_sha256": _record_hash(record)})


def force_escalate(record: DecisionRecord, reason: str) -> DecisionRecord:
    updated = record.model_copy(
        update={
            "outcome": worse_of(record.outcome, "ESCALATE"),
            "escalation_reasons": [*record.escalation_reasons, reason],
        }
    )
    return updated.model_copy(update={"record_sha256": _record_hash(updated)})


def worse_of(current: Outcome, proposed: Outcome) -> Outcome:
    if _RANK[current] >= _RANK[proposed]:
        return current
    return proposed


def required_approvals(record: DecisionRecord, policy: Policy) -> list[str]:
    approvals = policy.approvals
    if record.outcome == "APPROVE":
        return list(approvals.APPROVE[record.tier])
    if record.outcome == "APPROVE_WITH_CONDITIONS":
        if any(control.exception_applied for control in record.controls):
            return list(approvals.APPROVE_WITH_CONDITIONS.precedent_exception)
        return list(approvals.APPROVE_WITH_CONDITIONS.contract_stage_only)
    if record.outcome == "DECLINE":
        return list(approvals.DECLINE)
    return []


def _decline(view: _View) -> bool:
    return any(control.hard_gate == "decline" and control.state == "FALSE" for control in view.controls)


def _injection(view: _View) -> bool:
    return any(flag.level == "block" for flag in view.inputs.guard_flags)


def _material_contradiction(view: _View) -> bool:
    return any(item.severity == "material" and not item.resolved for item in view.inputs.contradictions)


def _hard_escalate(view: _View) -> bool:
    return any(
        control.hard_gate == "escalate" and control.state == "FALSE" and not control.conditional
        for control in view.controls
    )


def _required_false(view: _View) -> bool:
    return any(
        control.required and control.state == "FALSE" and not control.exception_applied
        for control in view.controls
    )


def _required_unknown(view: _View) -> bool:
    return any(
        control.required and control.state == "UNKNOWN" and not control.conditional
        for control in view.controls
    )


def _below_gate(view: _View) -> bool:
    return view.inputs.confidence.value < view.gate


def _any_conditional(view: _View) -> bool:
    return any(control.state == "TRUE" and control.conditional for control in view.controls)


def _always(_view: _View) -> bool:
    return True


_PREDICATES: dict[str, Callable[[_View], bool]] = {
    "hard_gate_decline_false": _decline,
    "injection_blocked": _injection,
    "unresolved_material_contradiction": _material_contradiction,
    "hard_gate_escalate_false": _hard_escalate,
    "required_false_without_exception": _required_false,
    "required_unknown": _required_unknown,
    "confidence_below_gate": _below_gate,
    "any_conditional": _any_conditional,
    "always": _always,
}


def _applies(control: Control, case_tier: Tier, indexed: dict[str, Fact], policy: Policy) -> bool:
    if case_tier not in control.required_for:
        return False
    if control.applies_when is None:
        return True
    return evaluate(policy.conditions[control.applies_when], indexed) != "FALSE"


def _evaluate_control(control: Control, indexed: dict[str, Fact]) -> ControlResult:
    fact_ids = sorted(indexed[key].fact_id for key in referenced_keys(control.rule) if key in indexed)
    return ControlResult(
        control_id=control.id,
        title=control.title,
        required=True,
        state=evaluate(control.rule, indexed),
        fact_ids=fact_ids,
        rule_id=control.id,
        weight=float(control.weight),
        hard_gate=control.hard_gate,
    )


def _apply_contract(
    control: Control,
    result: ControlResult,
    inputs: PolicyInputs,
    indexed: dict[str, Fact],
) -> ControlResult:
    stage = control.contract_stage_condition
    if stage is None or result.state == "TRUE":
        return result
    if inputs.profile.contract_status not in stage.when_contract_status_in:
        return result
    claim_rule = {"fact": stage.claim_fact, "op": stage.claim_rule.op, "value": stage.claim_rule.value}
    if evaluate(claim_rule, indexed) != "TRUE":
        return result
    fact_ids = list(result.fact_ids)
    claim = indexed.get(stage.claim_fact)
    if claim is not None and claim.fact_id not in fact_ids:
        fact_ids.append(claim.fact_id)
    return result.model_copy(
        update={
            "state": "TRUE",
            "conditional": True,
            "condition_text": stage.condition,
            "fact_ids": sorted(fact_ids),
        }
    )


def _apply_precedents(
    controls: list[ControlResult],
    inputs: PolicyInputs,
    policy: Policy,
    case_tier: Tier,
    indexed: dict[str, Fact],
) -> tuple[list[ControlResult], list[PrecedentRef]]:
    policy_controls = {item.id: item for item in policy.controls}
    current = {item.control_id: item for item in controls}
    grouped: dict[str, list[PrecedentCandidate]] = {}
    for candidate in inputs.precedents:
        grouped.setdefault(candidate.control_id, []).append(candidate)
    considered: list[PrecedentRef] = []
    for control_id, candidates in grouped.items():
        ordered = sorted(
            candidates,
            key=lambda item: (-item.relevance, -item.hmem_confidence, item.precedent_id),
        )
        applied_one = False
        for candidate in ordered:
            policy_control = policy_controls.get(control_id)
            failed = _failed_criteria(policy_control, candidate, inputs, indexed, policy, case_tier)
            result = current.get(control_id)
            applied = False
            if not failed and result is not None and result.state != "TRUE" and not applied_one:
                spec = policy_control.precedent_exception if policy_control is not None else None
                applied = True
                applied_one = True
                current[control_id] = result.model_copy(
                    update={
                        "state": "TRUE",
                        "conditional": True,
                        "condition_text": None if spec is None else spec.condition,
                        "exception_applied": candidate.precedent_id,
                    }
                )
            elif not failed and applied_one:
                failed = ["superseded"]
            elif not failed and result is not None and result.state == "TRUE":
                failed = ["control_already_satisfied"]
            elif not failed:
                failed = ["control_not_applicable"]
            considered.append(_precedent_ref(candidate, applied=applied, failed=failed))
    ordered_controls = [current[item.control_id] for item in controls]
    considered.sort(key=lambda item: item.precedent_id)
    return ordered_controls, considered


def _failed_criteria(
    control: Control | None,
    candidate: PrecedentCandidate,
    inputs: PolicyInputs,
    indexed: dict[str, Fact],
    policy: Policy,
    case_tier: Tier,
) -> list[str]:
    spec = None if control is None else control.precedent_exception
    if spec is None or not spec.allowed:
        return ["exception_not_allowed"]
    failed: list[str] = []
    mitigation = indexed.get(spec.mitigation_fact)
    if mitigation is None or mitigation.state != "TRUE":
        failed.append("mitigation_fact")
    held = policy.roles.get(candidate.reviewer_role)
    if (
        held is None
        or held < policy.roles[spec.approver_role]
        or candidate.decision not in _PASSING_DECISIONS
        or candidate.control_id != control.id  # type: ignore[union-attr]
        or candidate.mitigation != spec.mitigation_fact
    ):
        failed.append("reviewer_authority")
    if (inputs.as_of - candidate.created_as_of).days > spec.max_precedent_age_days:
        failed.append("precedent_age")
    if candidate.hmem_confidence < _MIN_CONFIDENCE or candidate.relevance < _MIN_RELEVANCE:
        failed.append("retrieval_quality")
    if _TIER_RISK[case_tier] > _TIER_RISK[candidate.tier]:
        failed.append("tier_risk")
    return failed


def _precedent_ref(candidate: PrecedentCandidate, *, applied: bool, failed: list[str]) -> PrecedentRef:
    return PrecedentRef(
        precedent_id=candidate.precedent_id,
        hmem_id=candidate.hmem_id,
        control_id=candidate.control_id,
        relevance=candidate.relevance,
        hmem_confidence=candidate.hmem_confidence,
        applied=applied,
        failed_criteria=list(failed),
    )


def _normalize(inputs: PolicyInputs) -> PolicyInputs:
    return inputs.model_copy(
        update={
            "facts": sorted(inputs.facts, key=lambda item: item.fact_id),
            "contradictions": sorted(inputs.contradictions, key=lambda item: (item.key, item.claim_id)),
            "precedents": sorted(inputs.precedents, key=lambda item: item.precedent_id),
            "guard_flags": sorted(
                inputs.guard_flags,
                key=lambda item: (item.kind, item.segment_id or "", item.level),
            ),
        }
    )


def _fact_index(facts: list[Fact]) -> dict[str, Fact]:
    indexed: dict[str, Fact] = {}
    for fact in facts:
        indexed[fact.key] = fact
    return indexed


def _record_hash(record: DecisionRecord) -> str:
    return sha256_hex(record.model_dump(exclude={"record_sha256"}))


def _outcome(value: str) -> Outcome:
    if value not in _RANK:
        raise PolicyError(f"invalid policy document: outcome {value}")
    return value  # type: ignore[return-value]
