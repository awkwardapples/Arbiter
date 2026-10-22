"""P2-T40: Meterless Scout adversarial injection set."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.guard.scout_guard import guard

pytestmark = pytest.mark.p2d

ROOT = Path(__file__).resolve().parents[2]
ADVERSARIAL = ROOT / "vendor/meterless/scout_adversarial.jsonl"


@pytest.mark.parametrize(
    "row",
    [json.loads(line) for line in ADVERSARIAL.read_text(encoding="utf-8").splitlines() if line.strip()],
    ids=lambda r: r["id"],
)
def test_p2_t40_scout_adversarial_row(row: dict) -> None:
    text = row["prompt"]
    expected_inj = bool(row["expected"]["injection"])
    result = guard(
        text,
        surface="api_input",
        capabilities=set(),
        segment_id=row["id"],
        use_model=False,
    )
    if expected_inj:
        assert result.level == "block", row["id"]
    else:
        assert result.level == "pass", row["id"]
