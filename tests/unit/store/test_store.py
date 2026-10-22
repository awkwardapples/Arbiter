"""P4-T15: SQLite round-trip across a reopened store, including fields P3 already saves."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.schemas.contract import ContractRisk, ContractScope, ExecutionContract, ToolStep
from app.store import Store
from tests.e2e.support import offline_env
from tests.unit.store.bundles import make_bundle

pytestmark = pytest.mark.p4b
__all__ = ["offline_env"]


def _contract(case_id: str) -> ExecutionContract:
    issued = datetime(2026, 10, 1, tzinfo=UTC)
    return ExecutionContract(
        contract_id="ctr-roundtrip",
        parent_id=None,
        trace_id="trace",
        case_id=case_id,
        intent="vendor.onboarding.decline",
        parameters={"kept": True},
        risk=ContractRisk(level="medium", approvals_required=[{"role": "tprm_lead"}]),
        tool_plan=[ToolStep(capability="procurement.decline.record")],
        scope=ContractScope(capabilities=["procurement.decline.record"]),
        issued_at=issued,
        expires_at=issued + timedelta(days=7),
        policy_pack_version="1.0.0",
        registry_version=1,
        signature="abc",
        state="pending_approval",
    )


def test_p4_t15_reopen_round_trip(tmp_path: Path) -> None:
    """P4-T15: a new Store on the same root returns the same case, contract and review."""
    root = tmp_path / "var"
    bundle = make_bundle("CASE-77")
    contract = _contract(bundle.case_id)
    store = Store(root)
    store.save(bundle)
    store.put_contract(contract)
    store.put_review({"case_id": bundle.case_id, "note": "kept"})
    del store

    assert (root / "arbiter.db").is_file()
    again = Store(root)
    assert again.get(bundle.case_id).model_dump(mode="json") == bundle.model_dump(mode="json")
    assert again.contracts_for(bundle.case_id)[0].model_dump(mode="json") == contract.model_dump(mode="json")
    assert again.reviews_for(bundle.case_id) == [{"case_id": bundle.case_id, "note": "kept"}]


def test_p4_t15_api_survives_reopen(offline_env: Path) -> None:
    """P4-T15: GET /cases/{id} is unchanged after the store is opened again."""
    del offline_env
    bundle = make_bundle("CASE-77")
    Store().save(bundle)
    client = TestClient(app)
    first = client.get("/cases/CASE-77")
    assert first.status_code == 200
    Store()
    second = client.get("/cases/CASE-77")
    assert second.status_code == 200
    assert first.json() == second.json()


def test_p4_t15_preserves_unknown_bundle_fields(tmp_path: Path) -> None:
    """P4-T15: a field P3 saved that CaseBundle does not declare stays in bundle_json and on get()."""
    root = tmp_path / "var"
    folder = root / "cases"
    folder.mkdir(parents=True)
    bundle = make_bundle("CASE-X")
    raw = bundle.model_dump(mode="json")
    raw["p3_extra"] = {"kept": True}
    (folder / "CASE-X.json").write_text(json.dumps(raw), encoding="utf-8")

    store = Store(root)
    restored = store.get("CASE-X")
    assert restored.model_dump(mode="json")["p3_extra"] == {"kept": True}
    store.save(restored)

    with sqlite3.connect(root / "arbiter.db") as conn:
        row = conn.execute("SELECT bundle_json FROM cases WHERE case_id = ?", ("CASE-X",)).fetchone()
    assert row is not None
    assert json.loads(row[0])["p3_extra"] == {"kept": True}
    known = bundle.model_dump(mode="json")
    stored = json.loads(row[0])
    for key, value in known.items():
        assert stored[key] == value
