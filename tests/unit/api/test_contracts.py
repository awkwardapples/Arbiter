"""P4-T13: DECLINE approval is role-gated, and an injected clock expires the contract."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.orchestrator import RunOptions, run
from app.store import Store
from tests.e2e.support import load_example, offline_env
from tests.unit.store.bundles import approval_body

pytestmark = pytest.mark.p4b
__all__ = ["offline_env"]


def test_p4_t13_decline_approval_and_expiry(offline_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """P4-T13: analyst is 403, lead executes an outbox file, and a future clock returns 409."""
    response = run(load_example("example_5.json"), options=RunOptions())
    assert response.output is not None
    assert response.output.decision == "DECLINE"
    case_id = response.output.case_id
    contracts = Store().contracts_for(case_id)
    assert len(contracts) == 1
    contract = contracts[0]
    assert contract.state == "pending_approval"

    client = TestClient(app)
    denied = client.post(
        f"/contracts/{contract.contract_id}/approve",
        json=approval_body(role="tprm_analyst"),
    )
    assert denied.status_code == 403
    assert "tprm_lead" in denied.text
    assert list((offline_env / "var" / "outbox").rglob("*.json")) == []

    approved = client.post(
        f"/contracts/{contract.contract_id}/approve",
        json=approval_body(role="tprm_lead"),
    )
    assert approved.status_code == 200
    executed = [item for item in Store().contracts_for(case_id) if item.state == "executed"]
    assert executed
    assert list((offline_env / "var" / "outbox").rglob("*.json"))

    monkeypatch.setattr(
        "app.api.routes_contracts.current_time",
        lambda: contract.expires_at + timedelta(days=1),
    )
    expired = client.post(
        f"/contracts/{contract.contract_id}/approve",
        json=approval_body(role="tprm_lead"),
    )
    assert expired.status_code == 409
    assert "expired" in expired.text.lower()
