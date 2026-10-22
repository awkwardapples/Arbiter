"""P4-A session and review e2e tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.orchestrator import RunOptions, run
from app.schemas.api import ReviewRequest
from app.schemas.case import CaseInput
from app.store import Store

pytestmark = pytest.mark.p4a
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def memory_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SAMPLE_MODE", "true")
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    monkeypatch.setenv("ARBITER_MEMORY", "on")
    from app.llm.resolve import reset_cache

    reset_cache()
    return tmp_path


def _client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def test_p4_t3_session_pair(memory_env: Path) -> None:
    """P4-T3: VND-0011 precedent enables VND-0012 APPROVE_WITH_CONDITIONS with P-0001."""
    r1 = run(CaseInput(vendor_id="VND-0011"), options=RunOptions())
    assert r1.output and r1.output.decision == "ESCALATE"
    case_id = r1.output.case_id
    review = ReviewRequest(
        reviewer="lead@example.com",
        role="tprm_lead",
        decision="APPROVE_WITH_CONDITIONS",
        rationale="Bridge letter accepted; conditions recorded for audit trail.",
        mitigations=["bridge_letter"],
        create_precedent=True,
    )
    resp = _client().post(f"/cases/{case_id}/review", json=review.model_dump(mode="json"))
    assert resp.status_code == 200, resp.text
    r2 = run(CaseInput(vendor_id="VND-0012"), options=RunOptions())
    assert r2.output
    bundle = Store().get(r2.output.case_id)
    assert bundle.decision.outcome == "APPROVE_WITH_CONDITIONS"
    assert "P-0001" in bundle.decision.exceptions_applied
    contracts = Store().contracts_for(r2.output.case_id)
    assert contracts and contracts[-1].state == "pending_approval"
    assert any(r["role"] == "tprm_lead" for r in contracts[-1].risk.approvals_required)


def test_p4_t6_prior_assessment_shapes_plan(memory_env: Path) -> None:
    """P4-T6: prior C09 escalation adds Q_VENDOR_CONTRACT on iteration 1."""
    from datetime import UTC, datetime

    from app.memory.keeper import HMemMemory

    mem = HMemMemory(var_dir=Path("var"), clock=lambda: datetime.now(UTC), tracer=None)
    mem.set_run_context(run_id="seed", case_tier="T2", failing=[], vendor_ref="VND-0099")
    mem._hmem.add(  # noqa: SLF001
        "assessment vendor VND-0099 outcome ESCALATE failing C09 unknown -",
        source="assessment:seed",
        type="factual",
        layer="working",
        tags=["vendor_assessment", "vnd-0099", "escalate"],
    )
    from app.agents.planner import required_queries
    from app.schemas.case import CaseInput
    from app.state import CaseState

    st = CaseState(
        case_id="CASE-0099",
        run_id="run-1",
        as_of=datetime.now(UTC).date(),
        input=CaseInput(vendor_id="VND-0099"),
        mode={"data": "duckdb", "llm": "offline"},
        budget_deadline=0.0,
        vendor_ref="VND-0099",
    )
    ids = [q for q, _ in required_queries(st, mem)]
    assert "Q_VENDOR_CONTRACT" in ids
    assert any("prior assessment" in r for _, r in required_queries(st, mem))


def test_p4_t7_demo_session(memory_env: Path) -> None:
    """P4-T7: demo-session --reset --yes passes all six steps."""
    py = sys.executable
    proc = subprocess.run(
        [py, str(ROOT / "run.py"), "demo-session", "--reset", "--yes"],
        cwd=memory_env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "| 6 |" in proc.stdout


def test_p4_t8_review_endpoint(memory_env: Path) -> None:
    """P4-T8: short rationale 400; review links human decision and executes contract."""
    r1 = run(CaseInput(vendor_id="VND-0011"), options=RunOptions())
    assert r1.output
    case_id = r1.output.case_id
    resp = _client().post(
        f"/cases/{case_id}/review",
        json={
            "reviewer": "lead@example.com",
            "role": "tprm_lead",
            "decision": "APPROVE_WITH_CONDITIONS",
            "rationale": "too short",
            "create_precedent": False,
        },
    )
    assert resp.status_code == 400
    good = ReviewRequest(
        reviewer="lead@example.com",
        role="tprm_lead",
        decision="APPROVE_WITH_CONDITIONS",
        rationale="Human override with sufficient rationale for audit.",
        create_precedent=False,
    )
    resp = _client().post(f"/cases/{case_id}/review", json=good.model_dump(mode="json"))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["human_decision"]["outcome_reasons"] == ["HUMAN_REVIEW"]
    bundle = Store().get(case_id)
    assert bundle.decision.outcome == "APPROVE_WITH_CONDITIONS"
    reviews = Store().reviews_for(case_id)
    assert reviews and reviews[-1]["machine_run_id"] == r1.run_id
    contract = body["contract"]
    assert contract["risk"]["approvals"]
