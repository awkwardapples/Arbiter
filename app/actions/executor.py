"""Execute a signed contract: verify it, check approvals, then write the outbox."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from app.actions import contracts, outbox
from app.policy.loader import Policy
from app.schemas.contract import ExecutionContract
from app.tracing import Tracer


class ExecutionResult(BaseModel):
    contract: ExecutionContract
    status: Literal["executed", "pending_approval", "rejected"]
    reason: str
    artifact: str | None = None


def _approved(contract: ExecutionContract, policy: Policy) -> bool:
    ranks = policy.roles
    granted = [
        ranks.get(str(a.get("role")), 0) for a in contract.risk.approvals if a.get("decision") == "approve"
    ]
    for required in contract.risk.approvals_required:
        need = ranks.get(str(required.get("role")), 99)
        if not any(rank >= need for rank in granted):
            return False
    return True


def execute(
    contract: ExecutionContract,
    *,
    now: datetime,
    policy: Policy,
    outbox_dir: Path,
    payload: dict[str, Any] | None = None,
    tracer: Tracer | None = None,
) -> ExecutionResult:
    ok, reason = contracts.verify(contract, now=now)
    if not ok:
        result = ExecutionResult(contract=contract, status="rejected", reason=reason)
    elif contract.state in {"rejected", "expired", "executed"}:
        result = ExecutionResult(contract=contract, status="rejected", reason=f"state_{contract.state}")
    elif not _approved(contract, policy):
        roles = ",".join(str(r.get("role")) for r in contract.risk.approvals_required)
        result = ExecutionResult(contract=contract, status="pending_approval", reason=f"awaiting {roles}")
    else:
        path = outbox.write(contract, payload or {}, root=outbox_dir)
        done = contracts.sign(contract.model_copy(update={"state": "executed"}))
        result = ExecutionResult(contract=done, status="executed", reason="ok", artifact=path.as_posix())
    if tracer is not None:
        tracer.event(
            "ActionExecutor",
            "execute_action",
            input_summary=f"contract={contract.contract_id} intent={contract.intent}",
            output_summary=f"{result.status}: {result.reason}"
            + (f" → {result.artifact}" if result.artifact else ""),
            status="pending_approval"
            if result.status == "pending_approval"
            else ("success" if result.status == "executed" else "error"),
        )
    return result
