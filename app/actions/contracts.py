"""Signed execution contracts (Scout subset).

TTL defaults to 7 days — a declared deviation from Scout's short default for human-paced
onboarding approvals (see master spec §8.7).
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from app.actions import keys
from app.canon import canonical_json
from app.policy.engine import required_approvals
from app.policy.loader import Policy
from app.schemas.contract import ContractRisk, ContractScope, ExecutionContract, ToolStep
from app.schemas.decision import DecisionRecord
from app.schemas.report import Report

_INTENT_BY_OUTCOME = {
    "APPROVE": "vendor.onboarding.approve",
    "APPROVE_WITH_CONDITIONS": "vendor.onboarding.approve_with_conditions",
    "REQUEST_INFO": "vendor.onboarding.request_info",
    "ESCALATE": "vendor.onboarding.escalate",
    "DECLINE": "vendor.onboarding.decline",
}

_TOOL_BY_OUTCOME = {
    "APPROVE": [ToolStep(capability="procurement.approval.record", args={})],
    "APPROVE_WITH_CONDITIONS": [ToolStep(capability="procurement.approval.record", args={})],
    "REQUEST_INFO": [ToolStep(capability="outbox.email.draft", args={})],
    "ESCALATE": [ToolStep(capability="itsm.ticket.create", args={})],
    "DECLINE": [ToolStep(capability="procurement.decline.record", args={})],
}

_RISK_LEVEL = {
    "APPROVE": "low",
    "APPROVE_WITH_CONDITIONS": "medium",
    "REQUEST_INFO": "low",
    "ESCALATE": "high",
    "DECLINE": "medium",
}


def _payload_for_sign(contract: ExecutionContract) -> dict[str, Any]:
    data = contract.model_dump(mode="json")
    data.pop("signature", None)
    return data


def sign(contract: ExecutionContract, *, key: bytes | None = None) -> ExecutionContract:
    secret = key if key is not None else keys.signing_key()
    payload = canonical_json(_payload_for_sign(contract))
    sig = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return contract.model_copy(update={"signature": sig})


def verify(
    contract: ExecutionContract,
    *,
    now: datetime,
    key: bytes | None = None,
) -> tuple[bool, str]:
    secret = key if key is not None else keys.signing_key()
    payload = canonical_json(_payload_for_sign(contract))
    expected = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(contract.signature, expected):
        return False, "bad_signature"
    expires = contract.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    now_utc = now if now.tzinfo else now.replace(tzinfo=UTC)
    if now_utc > expires.astimezone(UTC):
        return False, "expired"
    allowed = set(contract.scope.capabilities)
    for step in contract.tool_plan:
        cap = step.capability if isinstance(step, ToolStep) else step["capability"]
        if cap not in allowed:
            return False, "capability_out_of_scope"
    if contract.state not in {
        "issued",
        "pending_approval",
        "approved",
        "executed",
        "rejected",
        "expired",
    }:
        return False, "illegal_state"
    return True, "ok"


def issue(
    decision: DecisionRecord,
    report: Report,
    *,
    capabilities_map: dict[str, list[str]],
    policy: Policy,
    ttl_days: int = 7,
    trace_id: str,
    registry_version: int,
    now: datetime | None = None,
) -> ExecutionContract:
    now = now or datetime.now(UTC)
    outcome = decision.outcome
    intent = _INTENT_BY_OUTCOME[outcome]
    caps = list(capabilities_map.get(outcome, capabilities_map.get(intent, [])))
    if not caps:
        caps = [step.capability for step in _TOOL_BY_OUTCOME[outcome]]

    roles = required_approvals(decision, policy)
    approvals_required = [{"role": role} for role in roles]
    state: Literal[
        "issued",
        "pending_approval",
        "approved",
        "executed",
        "rejected",
        "expired",
    ] = "pending_approval" if roles else "issued"

    contract = ExecutionContract(
        contract_id=f"ctr-{uuid.uuid4().hex[:12]}",
        parent_id=None,
        trace_id=trace_id,
        case_id=decision.case_id,
        intent=intent,  # type: ignore[arg-type]
        parameters={
            "outcome": outcome,
            "policy_version": decision.policy_version,
            "decision_record_sha256": decision.record_sha256,
            "report_generator": report.generator,
        },
        risk=ContractRisk(
            level=_RISK_LEVEL[outcome],  # type: ignore[arg-type]
            flags=[],
            approvals_required=approvals_required,
            approvals=[],
        ),
        tool_plan=_TOOL_BY_OUTCOME[outcome],
        scope=ContractScope(capabilities=caps, deadline=None, budget=None),
        issued_at=now,
        expires_at=now + timedelta(days=ttl_days),
        policy_pack_version=decision.policy_version,
        registry_version=registry_version,
        signature="",
        state=state,
    )
    return sign(contract)


def add_approval(
    contract: ExecutionContract,
    *,
    by: str,
    role: str,
    decision: Literal["approve", "reject"],
    rationale: str,
    now: datetime,
    policy: Policy,
    key: bytes | None = None,
) -> ExecutionContract:
    del policy
    ok, reason = verify(contract, now=now, key=key)
    if not ok:
        raise ValueError(f"cannot approve invalid contract: {reason}")

    approval_row = {
        "by": by,
        "role": role,
        "at": now.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "decision": decision,
        "rationale": rationale,
    }
    new_approvals = list(contract.risk.approvals) + [approval_row]
    new_state: Literal[
        "issued",
        "pending_approval",
        "approved",
        "executed",
        "rejected",
        "expired",
    ] = "rejected" if decision == "reject" else contract.state

    required_roles = {row["role"] for row in contract.risk.approvals_required}
    approved_roles = {row["role"] for row in new_approvals if row.get("decision") == "approve"}
    if decision == "approve" and required_roles and required_roles <= approved_roles:
        new_state = "approved"

    child = contract.model_copy(
        update={
            "contract_id": f"ctr-{uuid.uuid4().hex[:12]}",
            "parent_id": contract.contract_id,
            "risk": contract.risk.model_copy(update={"approvals": new_approvals}),
            "state": new_state,
            "signature": "",
        }
    )
    return sign(child, key=key)
