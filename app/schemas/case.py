from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, model_validator


class Answer(BaseModel):
    question_id: str
    question: str
    answer_text: str


class Document(BaseModel):
    doc_id: str
    doc_type: str
    title: str
    issued_on: str | None = None
    expires_on: str | None = None
    text: str


class Component(BaseModel):
    product: str
    vendor: str | None = None
    version: str | None = None


class VendorSubmission(BaseModel):
    legal_name: str
    trading_name: str | None = None
    category: str
    requested_service: str
    criticality: Literal["low", "medium", "high"]
    annual_spend_gbp: float
    data_categories: list[Literal["none", "internal", "personal", "payment", "special_category"]]
    processing_countries: list[str]
    answers: list[Answer]
    documents: list[Document] = []
    declared_components: list[Component] = []
    patch_sla_critical_days: int | None = None


class CaseInput(BaseModel):
    vendor_id: str | None = None
    submission: VendorSubmission | None = None
    requested_by: str | None = None

    @model_validator(mode="after")
    def exactly_one_ref(self) -> CaseInput:
        has_vendor = self.vendor_id is not None and str(self.vendor_id).strip() != ""
        has_sub = self.submission is not None
        if has_vendor == has_sub:
            raise ValueError("exactly one of vendor_id or submission is required")
        return self
