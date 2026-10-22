"""P2-T41: domain injection set metrics (deterministic only)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.guard.eval_metrics import compute_metrics
from app.guard.scout_guard import guard

pytestmark = pytest.mark.p2d

DOMAIN = Path(__file__).resolve().parents[3] / "data/evals/injection_domain.jsonl"


def test_p2_t41_domain_precision_recall() -> None:
    rows = [json.loads(line) for line in DOMAIN.read_text(encoding="utf-8").splitlines() if line.strip()]
    predicted: list[bool] = []
    expected: list[bool] = []
    for row in rows:
        result = guard(
            row["text"],
            surface=row.get("surface", "vendor_answer"),
            capabilities=set(),
            segment_id=row["id"],
            use_model=False,
        )
        predicted.append(result.level == "block")
        expected.append(bool(row["expected"]["injection"]))
    metrics = compute_metrics(predicted_positive=predicted, expected_positive=expected)
    assert metrics.precision >= 0.95, metrics
    assert metrics.recall >= 0.90, metrics
    assert metrics.precision >= 0.90
    assert metrics.recall >= 0.82
