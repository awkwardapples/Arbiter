"""Wire-format models owned by the reviewer console. Does not import app."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Outcome = Literal[
    "APPROVE",
    "APPROVE_WITH_CONDITIONS",
    "REQUEST_INFO",
    "ESCALATE",
    "DECLINE",
]


class Answer(BaseModel):
    model_config = ConfigDict(extra="allow")

    question_id: str = Field()
    question: str = Field()
    answer_text: str = Field()


class Document(BaseModel):
    model_config = ConfigDict(extra="allow")

    doc_id: str = Field()
    doc_type: str = Field()
    title: str = Field()
    issued_on: str | None = Field(default=None)
    expires_on: str | None = Field(default=None)
    text: str = Field()


class Component(BaseModel):
    model_config = ConfigDict(extra="allow")

    product: str = Field()
    vendor: str | None = Field(default=None)
    version: str | None = Field(default=None)


class VendorSubmission(BaseModel):
    model_config = ConfigDict(extra="allow")

    legal_name: str = Field()
    trading_name: str | None = Field(default=None)
    category: str = Field()
    requested_service: str = Field()
    criticality: Literal["low", "medium", "high"] = Field()
    annual_spend_gbp: float = Field()
    data_categories: list[Literal["none", "internal", "personal", "payment", "special_category"]] = Field()
    processing_countries: list[str] = Field()
    answers: list[Answer] = Field()
    documents: list[Document] = Field(default_factory=list)
    declared_components: list[Component] = Field(default_factory=list)
    patch_sla_critical_days: int | None = Field(default=None)


class CaseInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    vendor_id: str | None = Field(default=None)
    submission: VendorSubmission | None = Field(default=None)
    requested_by: str | None = Field(default=None)

    @model_validator(mode="after")
    def exactly_one_ref(self) -> CaseInput:
        has_vendor = self.vendor_id is not None and str(self.vendor_id).strip() != ""
        has_sub = self.submission is not None
        if has_vendor == has_sub:
            raise ValueError("exactly one of vendor_id or submission is required")
        return self


class ReviewRequest(BaseModel):
    """Used by the Review page. Kept here so ui/ does not import app."""

    model_config = ConfigDict(extra="allow")

    reviewer: str = Field()
    role: str = Field()
    decision: Outcome = Field()
    rationale: str = Field(min_length=30)
    mitigations: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    create_precedent: bool = Field(default=False)
