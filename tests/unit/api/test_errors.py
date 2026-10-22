"""P4-T16: every error path returns ErrorResponse and no traceback."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.actions.contracts import sign
from app.api.main import app
from app.schemas.api import ErrorResponse
from app.store import Store
from tests.e2e.support import offline_env
from tests.unit.store.bundles import approval_body, issued_decline

pytestmark = pytest.mark.p4b
__all__ = ["offline_env"]


@pytest.mark.parametrize("status_code", [404, 400, 403, 409, 422])
def test_p4_t16_error_paths(status_code: int, offline_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """P4-T16: 404, 400, 403, 409 and 422 are ErrorResponse bodies with no traceback."""
    del offline_env
    store = Store()
    pending = issued_decline("CASE-PENDING", now=datetime.now(UTC))
    executed = sign(
        pending.model_copy(
            update={
                "contract_id": "ctr-executed",
                "state": "executed",
                "signature": "",
                "case_id": "CASE-DONE",
            }
        )
    )
    store.put_contract(pending)
    store.put_contract(executed)
    client = TestClient(app, raise_server_exceptions=False)

    if status_code == 404:
        response = client.get("/cases/does-not-exist")
    elif status_code == 400:
        response = client.post(
            f"/contracts/{pending.contract_id}/approve",
            json=approval_body(role="tprm_lead", rationale="too short"),
        )
    elif status_code == 403:
        response = client.post(
            f"/contracts/{pending.contract_id}/approve",
            json=approval_body(role="tprm_analyst"),
        )
    elif status_code == 409:
        monkeypatch.setattr(
            "app.api.routes_contracts.current_time",
            lambda: pending.expires_at + timedelta(days=1),
        )
        response = client.post(
            f"/contracts/{pending.contract_id}/approve",
            json=approval_body(role="tprm_lead"),
        )
    else:
        response = client.post(
            f"/contracts/{executed.contract_id}/approve",
            json=approval_body(role="tprm_lead"),
        )

    assert response.status_code == status_code
    ErrorResponse.model_validate(response.json())
    assert "Traceback" not in response.text
    assert "traceback" not in response.text
