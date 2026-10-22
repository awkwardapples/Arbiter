"""P2-T47: audit hash chain."""

from __future__ import annotations

import inspect

import pytest

from app.audit.chain import AuditChain

pytestmark = pytest.mark.p2d


def test_p2_t47_append_and_verify(tmp_path) -> None:
    chain = AuditChain(tmp_path / "audit.db")
    for i in range(100):
        chain.append("case_started", f"CASE-{i:04d}", {"i": i})
    ok, bad = chain.verify()
    assert ok
    assert bad is None
    chain.close()


def test_p2_t47_tamper_reports_seq(tmp_path) -> None:
    chain = AuditChain(tmp_path / "audit.db")
    chain.append("decision_recorded", "CASE-0001", {"ok": True})
    chain.append("decision_recorded", "CASE-0001", {"ok": True})
    conn = chain._conn
    conn.execute("UPDATE audit_log SET payload_json = ? WHERE seq = 2", ('{"ok": false}',))
    conn.commit()
    ok, bad = chain.verify()
    assert not ok
    assert bad == 2
    chain.close()


def test_p2_t47_no_public_mutate_api() -> None:
    public = {
        name
        for name, fn in inspect.getmembers(AuditChain, predicate=inspect.isfunction)
        if not name.startswith("_")
    }
    assert "append" in public
    assert "verify" in public
    assert "close" in public
    forbidden = {n for n in public if "update" in n or "delete" in n or "mutate" in n}
    assert not forbidden
