"""P15-T7: the committed Nightshift proof validates and names Nemotron. No services needed."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.p15

ROOT = Path(__file__).resolve().parents[3]
PROOF = ROOT / "docs" / "evidence" / "nightshift_proof.json"
SCHEMA = ROOT / "docs" / "evidence" / "nightshift_proof.schema.json"
HUMAN = ROOT / "docs" / "evidence" / "nightshift_deviations.md"


def test_p15_t7_proof_validates_and_names_nemotron() -> None:
    from app.cli.llm import ProofDocument

    assert PROOF.is_file(), "run `python run.py llm proof` against the live Nightshift"
    raw = PROOF.read_text(encoding="utf-8")
    doc = ProofDocument.model_validate_json(raw)
    assert "nemotron" in doc.fast.response_model
    assert "nemotron" in doc.deep.response_model
    for lane in (doc.fast, doc.deep):
        assert lane.receipt_id.startswith("rcpt_"), lane.receipt_id
        assert lane.sent_model.startswith("meterless/"), lane.sent_model
    lowered = raw.lower()
    assert "authorization" not in lowered and "bearer" not in lowered
    assert (ROOT / doc.human_observations).is_file()


def test_p15_t7_schema_file_matches_model() -> None:
    from app.cli.llm import ProofDocument

    assert json.loads(SCHEMA.read_text(encoding="utf-8")) == ProofDocument.model_json_schema()


def test_p15_t7_human_observations_are_committed() -> None:
    text = HUMAN.read_text(encoding="utf-8")
    assert "nightshift_proof.json" in text
