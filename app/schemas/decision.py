from __future__ import annotations

from datetime import UTC, date, datetime
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

    @classmethod
    def safe_escalation(
        cls,
        *,
        case_id: str,
        run_id: str,
        as_of: date,
        reason: str,
        policy_version: str,
        policy_sha256: str,
        calibration_version: str,
    ) -> DecisionRecord:
        """A minimal ESCALATE record for when the policy engine itself could not run."""
        from app.canon import sha256_hex

        confidence = ConfidenceBreakdown(value=0.0, gate=1.0, abstained=True, signals={})
        inputs = PolicyInputs(
            case_id=case_id,
            run_id=run_id,
            as_of=as_of,
            profile=TierProfile(
                data_categories=[], criticality="high", annual_spend_gbp=0.0, contract_status="none"
            ),
            facts=[],
            contradictions=[],
            guard_flags=[],
            confidence=confidence,
        )
        record = cls(
            case_id=case_id,
            run_id=run_id,
            policy_version=policy_version,
            policy_sha256=policy_sha256,
            calibration_version=calibration_version,
            tier="T1",
            inherent_risk_score=0,
            facts=[],
            controls=[],
            contradictions=[],
            outcome="ESCALATE",
            outcome_reasons=[],
            escalation_reasons=[reason],
            counterfactuals=[],
            precedents_considered=[],
            exceptions_applied=[],
            residual_risk=100,
            confidence=confidence,
            as_of=as_of,
            policy_inputs=inputs,
            created_at=datetime.combine(as_of, datetime.min.time()).replace(tzinfo=UTC),
            record_sha256="",
        )
        return record.model_copy(
            update={"record_sha256": sha256_hex(record.model_dump(exclude={"record_sha256"}))}
        )
