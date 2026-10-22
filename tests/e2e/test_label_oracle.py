"""P3-T16: label oracle. Ground-truth facts fed straight into `decide` reproduce every label."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.policy.engine import decide
from app.policy.loader import load_default
from app.schemas.common import Provenance
from app.schemas.decision import ConfidenceBreakdown, PolicyInputs, TierProfile
from app.schemas.evidence import Contradiction, Fact, GuardFlag

ROOT = Path(__file__).resolve().parents[2]
EVALS = ROOT / "data" / "evals"
AS_OF = date(2026, 10, 26)


def _truth() -> list[dict[str, Any]]:
    lines = (EVALS / "truth_facts.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _labels() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for line in (EVALS / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[row["case_ref"]] = row
    spec = yaml.safe_load((ROOT / "data" / "generator" / "scenarios.yaml").read_text(encoding="utf-8"))
    for case in spec["inline_cases"]:
        out[case["id"]] = {"expected_outcome": case["outcome"], "injection": case["id"] == "inline_injection"}
    return out


def _inputs(row: dict[str, Any]) -> PolicyInputs:
    facts = [
        Fact(
            fact_id=f"F-T-{i}",
            control_id="TRUTH",
            key=key,
            value=spec["value"],
            state=spec["state"],
            provenance=[Provenance(kind=spec["source"])],
        )
        for i, (key, spec) in enumerate(sorted(row["facts"].items()), start=1)
    ]
    contradictions = [
        Contradiction(
            key=c["key"],
            control_id=c["control_id"],
            claim_id=f"CL-T-{i}",
            claim_value=None,
            sor_value=None,
            sor_provenance=Provenance(kind="system_of_record"),
            severity=c["severity"],
        )
        for i, c in enumerate(row["contradictions"], start=1)
    ]
    block = GuardFlag(kind="injection", score=1.0, level="block", segment_id="truth")
    flags = [block] if row["guard_blocked"] else []
    return PolicyInputs(
        case_id=row["case_ref"],
        run_id="oracle",
        as_of=AS_OF,
        profile=TierProfile(**row["profile"]),
        facts=facts,
        contradictions=contradictions,
        guard_flags=flags,
        confidence=ConfidenceBreakdown(value=1.0, gate=0.0, abstained=False, signals={}),
    )


@pytest.mark.p3
def test_p3_t16_truth_covers_every_labelled_case() -> None:
    truth = {row["case_ref"] for row in _truth()}
    labels = _labels()
    assert len([r for r in labels.values() if "case_ref" in r]) == 32
    assert truth == set(labels), sorted(truth ^ set(labels))
    for row in _truth():
        assert row["guard_blocked"] == bool(labels[row["case_ref"]]["injection"]), row["case_ref"]


@pytest.mark.p3
@pytest.mark.parametrize("row", _truth(), ids=lambda r: r["case_ref"])
def test_p3_t16_label_oracle(row: dict[str, Any]) -> None:
    policy, calibration = load_default()
    label = _labels()[row["case_ref"]]
    record = decide(_inputs(row), policy, calibration)
    assert record.outcome == label["expected_outcome"], (record.outcome_reasons, record.controls)
    if "tier" in label:
        assert record.tier == label["tier"]
    for reason in label.get("expected_reasons", []):
        assert reason in record.outcome_reasons
