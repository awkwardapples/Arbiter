"""P1-T8 simulator endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sources.simulator import _fault_state, create_app


@pytest.fixture
def client() -> TestClient:
    _fault_state.clear()
    return TestClient(create_app())


@pytest.mark.p1a
def test_p1_t8_simulator_routes_and_health(client: TestClient) -> None:
    """P1-T8: endpoints mirror files; health counts match."""
    routes = [
        "/procurement/v1/vendors",
        "/procurement/v1/vendor-aliases",
        "/clm/v2/contracts",
        "/itsm/api/incidents",
        "/grc/v1/watchlist",
        "/trust/v1/submissions",
        "/trust/v1/answers",
        "/trust/v1/documents",
        "/trust/v1/components",
    ]
    for route in routes:
        resp = client.get(route)
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == len(body["records"])
    health = client.get("/health").json()
    assert health["status"] == "ok"
    assert health["counts"]["/procurement/v1/vendors"] >= 32


@pytest.mark.p1a
def test_p1_t8_sim_faults(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """P1-T8: SIM_FAULTS returns 500 exactly N times."""
    monkeypatch.setenv("SIM_FAULTS", "itsm:500x2")
    _fault_state.clear()
    assert client.get("/itsm/api/incidents").status_code == 500
    assert client.get("/itsm/api/incidents").status_code == 500
    assert client.get("/itsm/api/incidents").status_code == 200
