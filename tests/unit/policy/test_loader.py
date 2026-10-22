"""P2-T38: the loader rejects a bad policy and hashes the parsed rules."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.errors import PolicyError
from app.policy.loader import load_policy, policy_sha256

pytestmark = pytest.mark.p2c

POLICY_PATH = Path(__file__).resolve().parents[3] / "policy" / "arbiter_policy.v1.yaml"


def _dump(data: dict, path: Path) -> Path:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def test_p2_t38_rejects_bad_policies(tmp_path: Path) -> None:
    """P2-T38: unknown op, unknown fact key, duplicate id, and unknown predicate."""
    source = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))

    unknown_op = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    unknown_op["controls"][0]["rule"]["all"][0]["op"] = "contains"
    with pytest.raises(PolicyError, match="unknown op"):
        load_policy(_dump(unknown_op, tmp_path / "op.yaml"))

    unknown_fact = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    unknown_fact["controls"][0]["rule"]["all"][0]["fact"] = "mfa.not_a_fact"
    with pytest.raises(PolicyError, match="unknown fact key"):
        load_policy(_dump(unknown_fact, tmp_path / "fact.yaml"))

    duplicate = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    duplicate["controls"].append(duplicate["controls"][0])
    with pytest.raises(PolicyError, match="duplicate"):
        load_policy(_dump(duplicate, tmp_path / "dup.yaml"))

    unknown_predicate = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    unknown_predicate["outcome_rules"][0]["when"] = "sometimes"
    with pytest.raises(PolicyError, match="unknown predicate"):
        load_policy(_dump(unknown_predicate, tmp_path / "pred.yaml"))

    invalid_tier = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    invalid_tier["controls"][0]["required_for"] = ["T9"]
    with pytest.raises(PolicyError, match="invalid tier"):
        load_policy(_dump(invalid_tier, tmp_path / "tier.yaml"))

    assert source["policy_id"] == "arbiter-vendor-onboarding"


def test_p2_t38_hash_changes_when_a_rule_changes(tmp_path: Path) -> None:
    """P2-T38: policy_sha256 changes when any rule changes."""
    original = load_policy(POLICY_PATH)
    changed = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    changed["controls"][2]["rule"]["value"] = 89
    modified = load_policy(_dump(changed, tmp_path / "changed.yaml"))
    assert policy_sha256(original) != policy_sha256(modified)
    assert policy_sha256(original) == policy_sha256(load_policy(POLICY_PATH))
