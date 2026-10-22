from __future__ import annotations

from pydantic import BaseModel


class CitedSentence(BaseModel):
    text: str
    citations: list[str]


class Draft(BaseModel):
    to_role: str
    subject: str
    body: str


class Report(BaseModel):
    summary: str
    rationale: list[CitedSentence]
    recommended_actions: list[str]
    clarification_email: Draft | None = None
    limitations: list[str]
    generator: str
