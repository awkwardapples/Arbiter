"""Output models targeted by the JSON prompt templates (strict: unknown fields are rejected)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import TriState
from app.schemas.report import CitedSentence, Draft


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlannedQuery(_Strict):
    query_id: str
    params: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class PlanOut(_Strict):
    queries: list[PlannedQuery]
    extraction_targets: list[str] = Field(default_factory=list)
    rationale: str = ""


class ExtractedClaim(_Strict):
    question_id: str
    key: str
    value: bool | int | float | str | list[str] | None
    state: TriState
    quote: str


class ClaimListOut(_Strict):
    claims: list[ExtractedClaim]


ExtractOut = ClaimListOut


class Downgrade(_Strict):
    claim_id: str
    reason: str = ""


class CritiqueOut(_Strict):
    downgrades: list[Downgrade] = Field(default_factory=list)


ChallengeCategory = Literal[
    "uncorroborated_claim", "stale_evidence", "precedent_mismatch", "scope_gap", "other"
]


class ChallengeOut(_Strict):
    action: Literal["accept", "re_plan", "escalate"]
    category: ChallengeCategory
    cited_fact_ids: list[str] = Field(default_factory=list)
    suggested_query_ids: list[str] = Field(default_factory=list)
    rationale: str = ""


class ReportOut(_Strict):
    summary: str
    rationale: list[CitedSentence]
    recommended_actions: list[str] = Field(default_factory=list)
    clarification_email: Draft | None = None
    escalation_note: str | None = None
    limitations: list[str] = Field(default_factory=list)


class GuardClassifyOut(_Strict):
    label: Literal["benign", "suspicious", "injection"]
    reason: str = ""
