from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.case import CaseInput
from app.schemas.common import Outcome, Tier


class RunRequestOptions(BaseModel):
    sample_mode: bool | None = None
    llm: Literal["auto", "meterless", "nvidia", "offline"] | None = None


class RunRequestEnvelope(BaseModel):
    input: CaseInput
    options: RunRequestOptions | None = None


class RunRequest(BaseModel):
    """Accepts bare CaseInput or organisers' wrapped shape."""

    case: CaseInput
    options: RunRequestOptions | None = None

    @model_validator(mode="before")
    @classmethod
    def parse_shape(cls, data: Any) -> Any:
        if isinstance(data, CaseInput):
            return {"case": data, "options": None}
        if not isinstance(data, dict):
            return data
        if "input" in data:
            env = RunRequestEnvelope.model_validate(data)
            return {"case": env.input, "options": env.options}
        return {"case": data, "options": data.get("options")}


class RunOutputVendor(BaseModel):
    vendor_id: str | None = None
    legal_name: str


class RunOutputFinding(BaseModel):
    text: str
    citations: list[str]


class RunOutputContradiction(BaseModel):
    key: str
    claim: str
    system_of_record: str


class RunOutputCounterfactual(BaseModel):
    control_id: str
    evidence_required: list[str]
    question_ids: list[str] = []


class RunOutputAction(BaseModel):
    contract_id: str
    intent: str
    state: str
    capability: str | None = None


class RunOutput(BaseModel):
    case_id: str
    vendor: RunOutputVendor
    decision: Outcome
    risk_tier: Tier
    residual_risk: int
    confidence: dict[str, Any]
    summary: str
    findings: list[RunOutputFinding]
    contradictions: list[RunOutputContradiction]
    counterfactuals: list[RunOutputCounterfactual]
    precedents: list[Any] = []
    recommendations: list[str]
    actions: list[RunOutputAction]
    artifacts: list[str]
    limitations: list[str]


class AgentInfo(BaseModel):
    name: str
    role: str


class RunResponse(BaseModel):
    run_id: str
    status: Literal["success", "partial_success", "escalated", "error"]
    output: RunOutput | None = None
    agents: list[AgentInfo] = []
    trace_id: str
    log_file: str
    execution_time_seconds: float
    mode: dict[str, Any]


class ErrorBody(BaseModel):
    type: str
    message: str
    recoverable: bool = False


class ErrorResponse(BaseModel):
    run_id: str | None = None
    status: Literal["error"] = "error"
    error: ErrorBody
    trace_id: str | None = None
    execution_time_seconds: float | None = None


class ReviewRequest(BaseModel):
    reviewer: str
    role: str
    decision: Outcome
    rationale: str = Field(min_length=30)
    mitigations: list[str] = []
    conditions: list[str] = []
    create_precedent: bool = False


class ApprovalRequest(BaseModel):
    by: str
    role: str
    decision: Literal["approve", "reject"]
    rationale: str = Field(min_length=30)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    mode: dict[str, str]
