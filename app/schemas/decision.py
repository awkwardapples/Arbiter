from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.common import Outcome, Tier, TriState
from app.schemas.evidence import Contradiction, Fact, GuardFlag


class TierProfile(BaseModel):
    data_categories: list[str]
    criticality: Literal["low", "medium", "high"]
    annual_spend_gbp: float
    contract_status: str


class ControlResult(BaseModel):
    control_id: str
    title: str
    required: bool
    state: TriState
    fact_ids: list[str]
    rule_id: str
    weight: float
    hard_gate: str | None = None
    exception_applied: str | None = None
    conditional: bool = False
    condition_text: str | None = None


class Counterfactual(BaseModel):
    control_id: str
    from_state: TriState
    to_state: TriState
    evidence_required: list[str]
    question_ids: list[str] = []


class ConfidenceBreakdown(BaseModel):
    value: float
    gate: float
    abstained: bool
    signals: dict[str, float]


class PrecedentCandidate(BaseModel):
    precedent_id: str
    hmem_id: str
    control_id: str
    mitigation: str
    reviewer_role: str
    decision: Outcome
    created_as_of: date
    tier: Tier
    hmem_confidence: float
    relevance: float


class PrecedentRef(BaseModel):
    precedent_id: str
    hmem_id: str
    control_id: str
    relevance: float
    hmem_confidence: float
    applied: bool
    failed_criteria: list[str] = []


class PolicyInputs(BaseModel):
    case_id: str
    run_id: str
    as_of: date
    profile: TierProfile
    facts: list[Fact]
    contradictions: list[Contradiction]
    guard_flags: list[GuardFlag]
    precedents: list[PrecedentCandidate] = []
    confidence: ConfidenceBreakdown


class DecisionRecord(BaseModel):
    case_id: str
    run_id: str
    policy_version: str
    policy_sha256: str
    calibration_version: str
    tier: Tier
    inherent_risk_score: int
    facts: list[Fact]
    controls: list[ControlResult]
    contradictions: list[Contradiction]
    outcome: Outcome
    outcome_reasons: list[str]
    escalation_reasons: list[str] = []
    counterfactuals: list[Counterfactual]
    precedents_considered: list[PrecedentRef]
    exceptions_applied: list[str]
    residual_risk: int
    confidence: ConfidenceBreakdown
    conditions: list[str] = []
    as_of: date
    policy_inputs: PolicyInputs
    created_at: datetime
    record_sha256: str
