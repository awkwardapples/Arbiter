"""Parse and validate the versioned onboarding policy."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from app.canon import sha256_hex
from app.errors import PolicyError
from app.policy.dsl import LEAF_OPS
from app.schemas.facts import FACT_KEYS

PREDICATE_NAMES = frozenset(
    {
        "hard_gate_decline_false",
        "injection_blocked",
        "unresolved_material_contradiction",
        "hard_gate_escalate_false",
        "required_false_without_exception",
        "required_unknown",
        "confidence_below_gate",
        "any_conditional",
        "always",
    }
)
_TIERS = frozenset({"T1", "T2", "T3"})
_OUTCOMES = frozenset({"APPROVE", "APPROVE_WITH_CONDITIONS", "REQUEST_INFO", "ESCALATE", "DECLINE"})
_HARD_GATES = frozenset({"decline", "escalate"})


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SpendBand(_Strict):
    lt: float | None
    score: int


class TierRule(_Strict):
    tier: str
    inherent_gte: int | None = None
    or_data_category: str | None = None
    default: bool = False


class Tiering(_Strict):
    sensitivity: dict[str, int]
    criticality: dict[str, int]
    spend_bands: list[SpendBand]
    tiers: list[TierRule]


class ClaimRule(_Strict):
    op: str
    value: Any = None


class ContractStage(_Strict):
    when_contract_status_in: list[str]
    claim_fact: str
    claim_rule: ClaimRule
    condition: str
    approver_role: str


class PrecedentException(_Strict):
    allowed: bool
    mitigation_fact: str
    max_precedent_age_days: int
    approver_role: str
    condition: str


class ContradictionCheck(_Strict):
    claim: str
    sor: str
    compare: str
    severity: str


class Control(_Strict):
    id: str
    title: str
    weight: float
    required_for: list[str]
    rule: dict[str, Any]
    evidence_required: list[str]
    question_ids: list[str]
    t1_corroboration: bool = False
    applies_when: str | None = None
    hard_gate: str | None = None
    precedent_exception: PrecedentException | None = None
    contract_stage_condition: ContractStage | None = None
    contradiction_checks: list[ContradictionCheck] = []


class OutcomeRule(_Strict):
    id: str
    when: str
    outcome: str
    reason: str


class ConditionalApprovals(_Strict):
    contract_stage_only: list[str]
    precedent_exception: list[str]


class Approvals(_Strict):
    APPROVE: dict[str, list[str]]
    APPROVE_WITH_CONDITIONS: ConditionalApprovals
    REQUEST_INFO: list[str]
    ESCALATE: list[str]
    DECLINE: list[str]


class ResidualSpec(_Strict):
    tier_base: dict[str, int]
    per_false_weight: int
    per_unknown_weight: int
    per_material_contradiction: int
    injection: int
    cap: int


class Policy(_Strict):
    policy_id: str
    version: str
    owner_role: str
    effective_from: str
    references: list[str]
    tiering: Tiering
    conditions: dict[str, dict[str, Any]]
    controls: list[Control]
    outcome_rules: list[OutcomeRule]
    roles: dict[str, int]
    approvals: Approvals
    residual_risk: ResidualSpec


class Calibration(_Strict):
    version: str
    gates: dict[str, float]
    weights: dict[str, float]

    def gate(self, tier: str) -> float:
        try:
            return self.gates[tier]
        except KeyError as exc:
            raise PolicyError(f"invalid tier: {tier}") from exc


def load_policy(path: Path) -> Policy:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise PolicyError("invalid policy document")
    try:
        policy = Policy.model_validate(raw)
    except ValidationError as exc:
        raise PolicyError(f"invalid policy document: {exc}") from exc
    _validate(policy)
    return policy


def load_calibration(path: Path) -> Calibration:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    try:
        calibration = Calibration.model_validate(raw)
    except ValidationError as exc:
        raise PolicyError(f"invalid calibration: {exc}") from exc
    missing = _TIERS - set(calibration.gates)
    if missing:
        raise PolicyError(f"invalid tier: {sorted(missing)}")
    return calibration


def load_default() -> tuple[Policy, Calibration]:
    root = Path(__file__).resolve().parents[2]
    policy = load_policy(root / "policy" / "arbiter_policy.v1.yaml")
    active = (root / "policy" / "calibration" / "ACTIVE").read_text(encoding="utf-8").strip()
    calibration = load_calibration(root / "policy" / "calibration" / f"{active}.json")
    return policy, calibration


def policy_sha256(policy: Policy) -> str:
    return sha256_hex(policy)


def _validate(policy: Policy) -> None:
    _require_unique([control.id for control in policy.controls], "control id")
    _require_unique([rule.id for rule in policy.outcome_rules], "outcome rule id")
    for name, rule in policy.conditions.items():
        _walk_rule(rule, policy)
        if not name:
            raise PolicyError("invalid rule")
    for control in policy.controls:
        _walk_rule(control.rule, policy)
        for tier in control.required_for:
            _require_tier(tier)
        if control.applies_when is not None and control.applies_when not in policy.conditions:
            raise PolicyError(f"unknown predicate: {control.applies_when}")
        if control.hard_gate is not None and control.hard_gate not in _HARD_GATES:
            raise PolicyError(f"invalid policy document: hard_gate {control.hard_gate}")
        if control.precedent_exception is not None:
            _require_fact(control.precedent_exception.mitigation_fact)
            _require_role(policy, control.precedent_exception.approver_role)
        stage = control.contract_stage_condition
        if stage is not None:
            _require_fact(stage.claim_fact)
            _require_op(stage.claim_rule.op)
            _require_role(policy, stage.approver_role)
        for check in control.contradiction_checks:
            _require_fact(check.claim)
            _require_fact(check.sor)
    for rule in policy.outcome_rules:
        if rule.when not in PREDICATE_NAMES:
            raise PolicyError(f"unknown predicate: {rule.when}")
        if rule.outcome not in _OUTCOMES:
            raise PolicyError(f"invalid policy document: outcome {rule.outcome}")
    for rule in policy.tiering.tiers:
        _require_tier(rule.tier)
    for tier in policy.approvals.APPROVE:
        _require_tier(tier)
    _require_role(policy, policy.owner_role)


def _walk_rule(rule: dict[str, Any], policy: Policy) -> None:
    if "all" in rule:
        children = rule["all"]
    elif "any" in rule:
        children = rule["any"]
    elif "op" in rule and "fact" in rule:
        _require_op(str(rule["op"]))
        _require_fact(str(rule["fact"]))
        return
    else:
        raise PolicyError("invalid rule")
    if not isinstance(children, list):
        raise PolicyError("invalid rule")
    for child in children:
        if not isinstance(child, dict):
            raise PolicyError("invalid rule")
        _walk_rule(child, policy)


def _require_unique(values: list[str], label: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise PolicyError(f"duplicate {label}: {value}")
        seen.add(value)


def _require_fact(key: str) -> None:
    if key not in FACT_KEYS:
        raise PolicyError(f"unknown fact key: {key}")


def _require_op(op: str) -> None:
    if op not in LEAF_OPS:
        raise PolicyError(f"unknown op: {op}")


def _require_tier(tier: str) -> None:
    if tier not in _TIERS:
        raise PolicyError(f"invalid tier: {tier}")


def _require_role(policy: Policy, role: str) -> None:
    if role not in policy.roles:
        raise PolicyError(f"invalid policy document: unknown role {role}")
