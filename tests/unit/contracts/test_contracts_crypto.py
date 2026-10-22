"""P2-T45: contract signing and verification."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.actions.contracts import issue, sign, verify
from app.schemas.contract import ExecutionContract, ToolStep
from tests.unit.contracts.support import CAPABILITIES_MAP, sample_report, t1_approve_decision

pytestmark = pytest.mark.p2d


@pytest.fixture
def signed_contract() -> ExecutionContract:
    decision, policy = t1_approve_decision()
    assert decision.outcome == "APPROVE"
    now = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
    return issue(
        decision,
        sample_report(),
        capabilities_map=CAPABILITIES_MAP,
        policy=policy,
        trace_id="trace-1",
        registry_version=1,
        now=now,
    )


def _tamper_update(field: str, contract: ExecutionContract) -> dict:
    if field == "contract_id":
        return {"contract_id": contract.contract_id + "-x"}
    if field == "parent_id":
        return {"parent_id": "ctr-parent-tamper"}
    if field == "trace_id":
        return {"trace_id": "trace-tamper"}
    if field == "case_id":
        return {"case_id": "case-tamper"}
    if field == "intent":
        return {"intent": "vendor.onboarding.decline"}
    if field == "parameters":
        return {"parameters": {**contract.parameters, "tampered": True}}
    if field == "risk":
        return {"risk": contract.risk.model_copy(update={"level": "high"})}
    if field == "tool_plan":
        return {
            "tool_plan": [
                ToolStep(capability="procurement.approval.record", args={"tampered": True}),
            ]
        }
    if field == "scope":
        return {"scope": contract.scope.model_copy(update={"capabilities": ["evil.action"]})}
    if field == "issued_at":
        return {"issued_at": contract.issued_at + timedelta(minutes=1)}
    if field == "expires_at":
        return {"expires_at": contract.expires_at + timedelta(minutes=1)}
    if field == "policy_pack_version":
        return {"policy_pack_version": "tampered"}
    if field == "registry_version":
        return {"registry_version": contract.registry_version + 1}
    if field == "signed_by":
        return {"signed_by": "scout"}  # type: ignore[dict-item]
    if field == "state":
        return {"state": "issued"}
    if field == "signature":
        return {"signature": "00" * 32}
    raise KeyError(field)


@pytest.mark.parametrize("field", list(ExecutionContract.model_fields.keys()))
def test_p2_t45_tamper_field_fails(field: str, signed_contract: ExecutionContract) -> None:
    if field == "signature":
        tampered = signed_contract.model_copy(update={"signature": "deadbeef" * 8})
    elif field == "signed_by":
        tampered = ExecutionContract.model_construct(
            **{**signed_contract.model_dump(), "signed_by": "not-scout"}
        )
    else:
        tampered = signed_contract.model_copy(update=_tamper_update(field, signed_contract), deep=True)
    now = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
    ok, _ = verify(tampered, now=now)
    assert not ok


def test_p2_t45_sign_verify_ok(signed_contract: ExecutionContract) -> None:
    now = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
    ok, reason = verify(signed_contract, now=now)
    assert ok, reason


def test_p2_t45_expired_fails(signed_contract: ExecutionContract) -> None:
    ok, reason = verify(signed_contract, now=signed_contract.expires_at + timedelta(seconds=1))
    assert not ok
    assert reason == "expired"


def test_p2_t45_capability_out_of_scope(signed_contract: ExecutionContract) -> None:
    now = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
    bad = signed_contract.model_copy(
        update={
            "tool_plan": [ToolStep(capability="evil.action", args={})],
            "signature": "",
        }
    )
    bad = sign(bad)
    ok, reason = verify(bad, now=now)
    assert not ok
    assert reason == "capability_out_of_scope"


def test_p2_t45_key_order_permutation_still_verifies(signed_contract: ExecutionContract) -> None:
    now = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
    reshuffled = ExecutionContract.model_validate(signed_contract.model_dump())
    ok, reason = verify(reshuffled, now=now)
    assert ok, reason
