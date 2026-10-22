"""Approve or reject a pending execution contract (lane P4-B)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.actions import contracts
from app.actions.executor import execute
from app.audit.chain import AuditChain
from app.errors import ContractInvalid, Forbidden, PolicyIneligible
from app.policy.loader import Policy, load_default
from app.schemas.api import ApprovalRequest
from app.schemas.contract import ExecutionContract
from app.store import Store

router = APIRouter(prefix="/contracts", tags=["contracts"])


def current_time() -> datetime:
    return datetime.now(UTC)


class ApprovalResult(BaseModel):
    contract_id: str
    parent_id: str | None
    state: str
    executed: bool
    artifact: str | None = None


def _unmet(contract: ExecutionContract, policy: Policy) -> list[str]:
    ranks = policy.roles
    granted = [
        ranks.get(str(row.get("role")), 0)
        for row in contract.risk.approvals
        if row.get("decision") == "approve"
    ]
    missing: list[str] = []
    for required in contract.risk.approvals_required:
        role = str(required.get("role"))
        need = ranks.get(role, 99)
        if not any(rank >= need for rank in granted):
            missing.append(role)
    return missing


def _role_ok(role: str, unmet: list[str], policy: Policy) -> bool:
    if not unmet:
        return role in policy.roles
    caller = policy.roles.get(role)
    if caller is None:
        return False
    return any(caller >= policy.roles.get(required, 99) for required in unmet)


@router.post("/{contract_id}/approve")
def approve(contract_id: str, body: ApprovalRequest) -> ApprovalResult:
    store = Store()
    contract = store.get_contract(contract_id)
    now = current_time()
    ok, reason = contracts.verify(contract, now=now)
    if not ok:
        if reason == "expired":
            raise ContractInvalid("expired")
        raise ContractInvalid(reason)
    if contract.state != "pending_approval":
        raise PolicyIneligible(f"contract is {contract.state}")

    policy, _calibration = load_default()
    unmet = _unmet(contract, policy)
    if not _role_ok(body.role, unmet, policy):
        needed = ", ".join(unmet) if unmet else ", ".join(policy.roles)
        raise Forbidden(f"required roles: {needed}")

    child = contracts.add_approval(
        contract,
        by=body.by,
        role=body.role,
        decision=body.decision,
        rationale=body.rationale,
        now=now,
        policy=policy,
    )
    store.put_contract(child)
    audit = AuditChain()
    payload: dict[str, Any] = {
        "contract_id": child.contract_id,
        "parent_id": contract.contract_id,
        "by": body.by,
        "role": body.role,
        "decision": body.decision,
        "state": child.state,
    }
    audit.append("contract_issued", contract.case_id, payload)

    artifact: str | None = None
    executed = False
    if body.decision == "approve":
        result = execute(
            child,
            now=now,
            policy=policy,
            outbox_dir=store.root / "outbox",
            payload={"case_id": contract.case_id, "parent_id": contract.contract_id},
        )
        store.put_contract(result.contract)
        if result.status == "executed":
            executed = True
            artifact = result.artifact
            audit.append(
                "action_executed",
                contract.case_id,
                {**payload, "state": result.contract.state, "artifact": artifact},
            )
        child = result.contract
    return ApprovalResult(
        contract_id=child.contract_id,
        parent_id=child.parent_id,
        state=child.state,
        executed=executed,
        artifact=artifact,
    )
