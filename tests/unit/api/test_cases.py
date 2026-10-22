"""P4-T14: the case queue is ordered by residual risk, and badges carry text."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.schemas.common import Outcome
from app.store import Store
from tests.e2e.support import offline_env
from tests.unit.store.bundles import make_bundle

pytestmark = pytest.mark.p4b
__all__ = ["offline_env"]

_OUTCOMES: set[Outcome] = {
    "APPROVE",
    "APPROVE_WITH_CONDITIONS",
    "REQUEST_INFO",
    "ESCALATE",
    "DECLINE",
}


def test_p4_t14_queue_orders_by_residual_risk_then_created(offline_env: Path) -> None:
    """P4-T14: GET /cases sorts residual risk descending, then created ascending; outcome text is present."""
    del offline_env
    store = Store()
    specs: list[tuple[str, int, datetime, Outcome]] = [
        ("CASE-A", 90, datetime(2026, 1, 2, tzinfo=UTC), "ESCALATE"),
        ("CASE-B", 90, datetime(2026, 1, 1, tzinfo=UTC), "DECLINE"),
        ("CASE-C", 10, datetime(2026, 1, 3, tzinfo=UTC), "APPROVE"),
    ]
    for case_id, risk, created, outcome in specs:
        store.save(make_bundle(case_id, residual_risk=risk, created_at=created, outcome=outcome))

    response = TestClient(app).get("/cases")
    assert response.status_code == 200
    rows = response.json()
    assert [row["case_id"] for row in rows] == ["CASE-B", "CASE-A", "CASE-C"]
    for row in rows:
        assert row["outcome"] in _OUTCOMES
        assert row["vendor"] == "Queue Vendor Ltd"
        assert row["tier"] in {"T1", "T2", "T3"}
        assert isinstance(row["residual_risk"], int)
        assert isinstance(row["status"], str) and row["status"]
        assert row["created"]
