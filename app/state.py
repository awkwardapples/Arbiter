"""Per-run case state shared by the orchestrator and the agents."""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.data.backend import QueryResult
from app.data.inline import inline_vendor_ref
from app.schemas.case import CaseInput
from app.schemas.common import Provenance
from app.schemas.contract import ExecutionContract
from app.schemas.decision import DecisionRecord, PrecedentCandidate
from app.schemas.evidence import Claim, Contradiction, DQFlag, EvaluationReport, Fact, GuardFlag, GuardResult
from app.schemas.report import Report


class PlanStep(BaseModel):
    query_id: str
    params: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class Plan(BaseModel):
    iteration: int
    steps: list[PlanStep]
    source: str
    rationale: str = ""
    extraction_targets: list[str] = Field(default_factory=list)


class Segment(BaseModel):
    """One piece of vendor text after the guard: an answer or a document."""

    segment_id: str
    kind: Literal["answer", "document"]
    ref: str
    query_id: str
    record_key: str
    text: str
    guard: GuardResult

    @property
    def usable(self) -> bool:
        return self.guard.level != "block"


class ChallengeResult(BaseModel):
    action: Literal["accept", "re_plan", "escalate"]
    reason_code: str | None = None
    suggested_query_ids: list[str] = Field(default_factory=list)
    source: str = "deterministic"
    rejected: list[str] = Field(default_factory=list)
    cited_fact_ids: list[str] = Field(default_factory=list)
    rationale: str = ""


class CaseState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    case_id: str
    run_id: str
    as_of: date
    input: CaseInput
    mode: dict[str, str]
    budget_deadline: float
    vendor_ref: str
    profile: dict[str, Any] = Field(default_factory=dict)
    aliases: list[str] = Field(default_factory=list)
    tier_hint: str | None = None
    plans: list[Plan] = Field(default_factory=list)
    executed_queries: dict[str, QueryResult] = Field(default_factory=dict)
    query_counts: dict[str, int] = Field(default_factory=dict)
    segments: list[Segment] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    facts: list[Fact] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    dq_flags: list[DQFlag] = Field(default_factory=list)
    guard_flags: list[GuardFlag] = Field(default_factory=list)
    evaluations: list[EvaluationReport] = Field(default_factory=list)
    first_decision: DecisionRecord | None = None
    decision: DecisionRecord | None = None
    precedents: list[PrecedentCandidate] = Field(default_factory=list)
    challenge: ChallengeResult | None = None
    report: Report | None = None
    contracts: list[ExecutionContract] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    eval_loops: int = 0
    challenge_loops: int = 0
    evidence_index: dict[str, Provenance] = Field(default_factory=dict)
    extractors: list[str] = Field(default_factory=list)
    critiqued: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @property
    def is_inline(self) -> bool:
        return self.input.submission is not None

    def latest_evaluation(self) -> EvaluationReport | None:
        return self.evaluations[-1] if self.evaluations else None


def case_id_for(case_input: CaseInput) -> tuple[str, str]:
    """Return (case_id, vendor_ref): digits of the vendor id, or the inline submission digest."""
    if case_input.submission is not None:
        ref = inline_vendor_ref(case_input.submission)
        return f"CASE-{ref.split('-', 1)[1].upper()}", ref
    vendor_id = str(case_input.vendor_id).strip()
    digits = "".join(re.findall(r"\d", vendor_id)) or vendor_id.upper()
    return f"CASE-{digits}", vendor_id


def new_state(
    case_input: CaseInput,
    *,
    run_id: str,
    as_of: date,
    mode: dict[str, str],
    budget_deadline: float,
) -> CaseState:
    case_id, vendor_ref = case_id_for(case_input)
    return CaseState(
        case_id=case_id,
        run_id=run_id,
        as_of=as_of,
        input=case_input,
        mode=dict(mode),
        budget_deadline=budget_deadline,
        vendor_ref=vendor_ref,
    )
