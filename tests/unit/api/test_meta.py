"""P4-T12: audit verification over HTTP, plus the health and vendor reads."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.audit.chain import AuditChain
from tests.e2e.support import offline_env

pytestmark = pytest.mark.p4b
__all__ = ["offline_env"]

ROOT = Path(__file__).resolve().parents[3]


def test_p4_t12_audit_verify(offline_env: Path) -> None:
    """P4-T12: GET /audit/verify passes, then a tampered row returns ok false and first_bad_seq."""
    chain = AuditChain()
    seq = chain.append("decision_recorded", "CASE-1", {"ok": True})
    chain.close()

    client = TestClient(app)
    intact = client.get("/audit/verify")
    assert intact.status_code == 200
    assert intact.json() == {"ok": True, "first_bad_seq": None}

    with sqlite3.connect("var/audit.db") as conn:
        conn.execute("UPDATE audit_log SET hash = ? WHERE seq = ?", ("0" * 64, seq))

    broken = client.get("/audit/verify")
    assert broken.status_code == 200
    assert broken.json() == {"ok": False, "first_bad_seq": seq}

    cli = subprocess.run(
        [sys.executable, str(ROOT / "run.py"), "audit-verify"],
        cwd=offline_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert cli.returncode == 1
    assert "false" in cli.stdout.lower()


def test_health_extension_and_vendors(offline_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Health names data, provider and audit length; /vendors is the registry list."""
    del offline_env
    monkeypatch.setenv("SAMPLE_MODE", "true")
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert "mode" in body
    assert isinstance(body["data"], dict)
    assert body["data"]["backend"] == "duckdb"
    assert isinstance(body["provider"], dict)
    assert "hmem_records" in body
    assert isinstance(body["audit_chain_length"], int)
    assert "nvapi-" not in health.text

    vendors = client.get("/vendors")
    assert vendors.status_code == 200
    rows = vendors.json()
    assert rows
    assert "vendor_id" in rows[0]
    assert "legal_name" in rows[0]
