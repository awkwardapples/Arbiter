"""P19-T2: replay of a human-reviewed case replays the machine decision and verifies the review."""

from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from app.audit.replay import replay
from app.orchestrator import RunOptions, run
from app.schemas.case import CaseInput
from app.store import Store

pytestmark = pytest.mark.p19

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def session_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Run the sample memory session in a tmp working directory, never the real var/."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SAMPLE_MODE", "true")
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    monkeypatch.setenv("ARBITER_MEMORY", "on")
    monkeypatch.setenv("ARBITER_SIGNING_KEY", "ab" * 32)
    from app.actions.keys import reset_signing_key_cache_for_tests
    from app.cli.review import cmd_demo_session
    from app.config import get_settings
    from app.llm.resolve import reset_cache

    get_settings.cache_clear()
    reset_signing_key_cache_for_tests()
    reset_cache()
    code = cmd_demo_session(argparse.Namespace(reset=True, yes=True, live=False))
    assert code == 0
    return tmp_path


def test_p19_t2_reviewed_case_replays_with_override(session_env: Path) -> None:
    """CASE-0011: the machine ESCALATE replays and the lead's override is reported."""
    store = Store()
    assert store.get("CASE-0011").decision.outcome_reasons == ["HUMAN_REVIEW"]
    result = replay("CASE-0011", store=store)
    assert result.match is True, result.diff
    assert result.diff == []
    assert result.machine_outcome == "ESCALATE"
    assert result.machine_source == "stored"
    assert result.human_override is not None
    assert result.human_override.decision == "APPROVE_WITH_CONDITIONS"
    assert result.human_override.role == "tprm_lead"
    assert result.human_override.reviewer == "lead.reviewer@example.com"
    assert result.checks.policy_hash and result.checks.record_hash and result.checks.contract_signatures

    cli = subprocess.run(
        [sys.executable, str(ROOT / "run.py"), "replay", "CASE-0011"],
        cwd=session_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert cli.returncode == 0, cli.stderr or cli.stdout
    assert "Machine decision ESCALATE replays identically. Overridden by tprm_lead" in cli.stderr
    assert len(cli.stdout.strip().splitlines()) == 1  # stdout stays one JSON line


def test_p19_t2_tampered_human_outcome_fails(session_env: Path) -> None:
    """Changing the stored human outcome breaks the review check."""
    del session_env
    store = Store()
    bundle = store.get("CASE-0011")
    tampered = bundle.decision.model_copy(update={"outcome": "APPROVE"})
    store.save(bundle.model_copy(update={"decision": tampered}))
    result = replay("CASE-0011", store=Store())
    assert result.match is False
    assert result.diff


def test_p19_t2_unreviewed_case_unchanged(session_env: Path) -> None:
    """CASE-0003 has no review: today's path, new fields unset."""
    del session_env
    response = run(CaseInput(vendor_id="VND-0003"), options=RunOptions())
    assert response.output is not None
    assert response.output.case_id == "CASE-0003"
    result = replay("CASE-0003", store=Store())
    assert result.match is True
    assert result.diff == []
    assert result.human_override is None
    assert result.machine_outcome is None
    assert result.machine_source is None


def test_p19_t2_pre_p19_review_is_reconstructed(session_env: Path) -> None:
    """A case reviewed before P19 has no machine record: replay re-decides and says so."""
    with sqlite3.connect(session_env / "var" / "arbiter.db") as conn:
        conn.execute("DELETE FROM machine_decisions WHERE case_id = ?", ("CASE-0011",))
    result = replay("CASE-0011", store=Store())
    assert result.machine_source == "reconstructed"
    assert result.machine_outcome == "ESCALATE"
    assert result.human_override is not None
    assert result.match is True, result.diff
