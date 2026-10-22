from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from app.schemas.common import Provenance, TriState


class GuardFlag(BaseModel):
    kind: str
    score: float
    level: Literal["pass", "warn", "block"]
    segment_id: str | None = None


class GuardResult(BaseModel):
    level: Literal["pass", "warn", "block"]
    flags: list[GuardFlag]
    redacted_text: str
    redactions: list[str] = []


class Claim(BaseModel):
    claim_id: str
    control_id: str
    key: str
    asserted_value: bool | float | str | list[str] | None
    state: TriState
    provenance: Provenance
    extractor: str
    grounded: bool | None = None


class Fact(BaseModel):
    fact_id: str
    control_id: str
    key: str
    value: bool | float | str | list[str] | None
    state: TriState
    provenance: list[Provenance]
    derived_from_claims: list[str] = []
    dq_flags: list[str] = []


class Contradiction(BaseModel):
    key: str
    control_id: str
    claim_id: str
    claim_value: Any
    sor_value: Any
    sor_provenance: Provenance
    severity: Literal["material", "minor"]
    resolved: bool = False


class Gap(BaseModel):
    control_id: str
    reason: str
    suggested_query_ids: list[str] = []
    suggested_answer_ids: list[str] = []


class DQFlag(BaseModel):
    rule: str
    table: str
    record_key: str


class EvaluationReport(BaseModel):
    sufficient: bool
    gaps: list[Gap]
    contradictions: list[Contradiction]
    ungrounded_claim_ids: list[str]
    dq_flags: list[DQFlag]
    injection_flags: list[GuardFlag]
    revision_request: str | None = None
