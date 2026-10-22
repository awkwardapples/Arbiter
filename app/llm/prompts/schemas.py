"""Output models targeted by the JSON prompt templates (first version; P3 may refine)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class PlannedQuery(BaseModel):
    query_id: str
    params: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class PlanOut(BaseModel):
    queries: list[PlannedQuery]


class ExtractedClaim(BaseModel):
    key: str
    value: Any
    quote: str
    control_id: str | None = None


class ExtractOut(BaseModel):
    claims: list[ExtractedClaim]


class CritiqueIssue(BaseModel):
    kind: Literal["gap", "contradiction", "ungrounded", "stale", "other"]
    detail: str
    fact_keys: list[str] = Field(default_factory=list)


class CritiqueOut(BaseModel):
    needs_revision: bool
    issues: list[CritiqueIssue] = Field(default_factory=list)


class ChallengeOut(BaseModel):
    action: Literal["none", "request_evidence", "escalate"]
    reasons: list[str] = Field(default_factory=list)
    requested_evidence: list[str] = Field(default_factory=list)


class GuardClassifyOut(BaseModel):
    label: Literal["benign", "suspicious", "injection"]
    reason: str = ""
