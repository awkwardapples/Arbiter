from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class ContractRisk(BaseModel):
    level: Literal["low", "medium", "high"]
    flags: list[str] = []
    approvals_required: list[dict[str, Any]] = []
    approvals: list[dict[str, Any]] = []


class ToolStep(BaseModel):
    capability: str
    args: dict[str, Any] = {}


class ContractScope(BaseModel):
    capabilities: list[str]
    deadline: datetime | None = None
    budget: dict[str, Any] | None = None


class ExecutionContract(BaseModel):
    contract_id: str
    parent_id: str | None
    trace_id: str
    case_id: str
    intent: Literal[
        "vendor.onboarding.approve",
        "vendor.onboarding.approve_with_conditions",
        "vendor.onboarding.request_info",
        "vendor.onboarding.escalate",
        "vendor.onboarding.decline",
    ]
    parameters: dict[str, Any]
    risk: ContractRisk
    tool_plan: list[ToolStep]
    scope: ContractScope
    issued_at: datetime
    expires_at: datetime
    policy_pack_version: str
    registry_version: int
    signature: str
    signed_by: Literal["scout"] = "scout"
    state: Literal[
        "issued",
        "pending_approval",
        "approved",
        "executed",
        "rejected",
        "expired",
    ]
