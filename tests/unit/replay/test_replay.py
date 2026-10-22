"""P4-T10 and P4-T11: replay of offline decisions, and failure on tamper."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from app.orchestrator import RunOptions, run
from app.store import Store
from tests.e2e.support import EXAMPLE_FILES, load_example, offline_env

pytestmark = pytest.mark.p4b
__all__ = ["offline_env"]

ROOT = Path(__file__).resolve().parents[3]


def _replay():
    try:
        from app.audit.replay import replay
    except ImportError as exc:
        pytest.fail(f"replay is not implemented: {exc}")
    return replay


def test_p4_t10_replay_matches_six_examples(offline_env: Path) -> None:
    """P4-T10: replay match=true for all six e2e examples run offline."""
    replay = _replay()
    for name in EXAMPLE_FILES:
        response = run(load_example(name), options=RunOptions())
        assert response.output is not None
        case_id = response.output.case_id
        result = replay(case_id, store=Store())
        assert result.match is True
        assert result.diff == []
        assert result.checks.policy_hash is True
        assert result.checks.record_hash is True
        assert result.checks.contract_signatures is True
        cli = subprocess.run(
            [sys.executable, str(ROOT / "run.py"), "replay", case_id],
            cwd=offline_env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert cli.returncode == 0, cli.stderr or cli.stdout


def test_p4_t11_tampered_fact_and_policy(offline_env: Path, tmp_path: Path) -> None:
    """P4-T11: a tampered fact is named in the diff; a tampered policy fails policy_hash."""
    replay = _replay()
    del offline_env
    response = run(load_example("example_1.json"), options=RunOptions())
    assert response.output is not None
    case_id = response.output.case_id
    store = Store()
    bundle = store.get(case_id)
    assert bundle.decision.facts, "example 1 produced no facts to tamper"
    target = bundle.decision.facts[0]
    tampered_value = "tampered-fact-value" if target.value != "tampered-fact-value" else "other-tamper"

    policy_copy = tmp_path / "policy"
    shutil.copytree(ROOT / "policy", policy_copy)
    policy_file = policy_copy / "arbiter_policy.v1.yaml"
    original = policy_file.read_text(encoding="utf-8")
    assert "weight: 3" in original
    policy_file.write_text(original.replace("weight: 3", "weight: 9", 1), encoding="utf-8")
    tampered_policy = replay(case_id, store=store, policy_root=policy_copy)
    assert tampered_policy.checks.policy_hash is False
    assert tampered_policy.match is False

    facts = [
        fact.model_copy(update={"value": tampered_value}) if fact.fact_id == target.fact_id else fact
        for fact in bundle.decision.facts
    ]
    store.save(bundle.model_copy(update={"decision": bundle.decision.model_copy(update={"facts": facts})}))
    tampered_fact = replay(case_id, store=Store())
    assert tampered_fact.match is False
    assert any(target.key in item for item in tampered_fact.diff)
