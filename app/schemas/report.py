from __future__ import annotations

from pydantic import BaseModel


class CitedSentence(BaseModel):
    text: str
    citations: list[str]


class Draft(BaseModel):
    to_role: str
    subject: str
    body: str


class EvidenceRef(BaseModel):
    source_label: str
    record_label: str
    field_label: str
    value: str
    quote: str | None = None
    provenance_id: str = ""


class BriefPoint(BaseModel):
    text: str
    claim: EvidenceRef | None = None
    record: EvidenceRef | None = None
    citations: list[str] = []


class NextStep(BaseModel):
    action: str
    owner_role: str
    due: str | None = None


class AnalystBrief(BaseModel):
    headline: str
    why: list[BriefPoint]
    next_steps: list[NextStep]
    generator: str


class BriefWording(BaseModel):
    """Model output: headline and why text only. Evidence refs stay on the template."""

    headline: str
    why: list[str]


class Report(BaseModel):
    summary: str
    rationale: list[CitedSentence]
    recommended_actions: list[str]
    clarification_email: Draft | None = None
    limitations: list[str]
    generator: str
    brief: AnalystBrief | None = None
    drafts: list[Draft] = []
