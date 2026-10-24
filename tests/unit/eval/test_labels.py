"""P15-T3: labels come from the policy oracle on truth facts, and the test split holds the hard cases."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest

from app.policy.engine import decide
from app.policy.loader import load_default
from tests.e2e.test_label_oracle import _inputs

pytestmark = pytest.mark.p15

ROOT = Path(__file__).resolve().parents[3]
EVALS = ROOT / "data" / "evals"
_HARD = ("S06", "S07", "S09", "S11", "S12")


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _labels() -> dict[str, dict[str, Any]]:
    return {row["case_ref"]: row for row in _jsonl(EVALS / "labels.jsonl")}


def _truth() -> dict[str, dict[str, Any]]:
    return {row["case_ref"]: row for row in _jsonl(EVALS / "truth_facts.jsonl")}


def _codes(scenario_key: str) -> list[str]:
    return scenario_key.split("+")


def test_p15_t3_failing_and_unknown_controls_match_oracle() -> None:
    policy, calibration = load_default()
    truth = _truth()
    labels = _labels()
    assert len(labels) == 32
    any_failing = False
    for ref, label in sorted(labels.items()):
        record = decide(_inputs(truth[ref]), policy, calibration)
        failing = sorted(
            c.control_id
            for c in record.controls
            if c.required and c.state == "FALSE" and not c.exception_applied
        )
        unknown = sorted(c.control_id for c in record.controls if c.required and c.state == "UNKNOWN")
        assert label["expected_failing_controls"] == failing, ref
        assert label["expected_unknown_controls"] == unknown, ref
        any_failing = any_failing or bool(failing)
    assert any_failing, "no label has a failing control; the oracle did not run"


def test_p15_t3_contradiction_keys_from_truth() -> None:
    truth = _truth()
    for ref, label in _labels().items():
        expected = sorted({c["key"] for c in truth[ref]["contradictions"]})
        assert label["expected_contradiction_keys"] == expected, ref
        codes = _codes(label["scenario"])
        if "S06" in codes:
            assert "residency.regions" in label["expected_contradiction_keys"], ref
        if "S07" in codes:
            assert label["expected_contradiction_keys"], ref


def test_p15_t3_test_split_holds_hard_scenarios() -> None:
    splits = json.loads((EVALS / "splits.json").read_text(encoding="utf-8"))
    test = set(splits["test"])
    calibration = set(splits["calibration"])
    by_code: dict[str, list[str]] = defaultdict(list)
    for ref, label in _labels().items():
        for code in _codes(label["scenario"]):
            by_code[code].append(ref)
    for code in _HARD:
        assert test.intersection(by_code[code]), f"{code} has no vendor in the test split"
    for code, refs in by_code.items():
        if len(refs) >= 2:
            assert test.intersection(refs) and calibration.intersection(refs), code
    labels = _labels()
    contradiction_cases = [ref for ref in test if labels[ref]["expected_contradiction_keys"]]
    assert any(
        "residency.regions" in labels[ref]["expected_contradiction_keys"] for ref in contradiction_cases
    )
