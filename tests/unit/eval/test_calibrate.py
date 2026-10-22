"""P5-T3: calibration is deterministic and stays on the calibration split."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.p5b

ROOT = Path(__file__).resolve().parents[3]


def test_p5_t3_calibration_split_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """P5-T3: same inputs, same file; chosen gates have 0 unsafe approvals on calibration."""
    monkeypatch.setenv("SAMPLE_MODE", "true")
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    monkeypatch.setenv("ARBITER_MEMORY", "off")
    from app.llm.resolve import reset_cache

    reset_cache()
    from eval.calibrate import calibrate_split

    active = (ROOT / "policy" / "calibration" / "ACTIVE").read_text(encoding="utf-8")
    initial = (ROOT / "policy" / "calibration" / "cal-initial.json").read_text(encoding="utf-8")
    first = calibrate_split(out_dir=tmp_path / "a")
    second = calibrate_split(out_dir=tmp_path / "b")
    assert first.path.read_bytes() == second.path.read_bytes()
    assert first.split == "calibration"
    assert first.unsafe_approvals == 0
    splits = json.loads((ROOT / "data" / "evals" / "splits.json").read_text(encoding="utf-8"))
    assert first.split_sha256 == splits["sha256"]["calibration"]
    assert first.split_sha256 != splits["sha256"]["test"]
    payload = json.loads(first.path.read_text(encoding="utf-8"))
    assert payload["split_sha256"] == splits["sha256"]["calibration"]
    assert payload["objective"]
    assert payload["calibration_results"]["unsafe_approvals"] == 0
    assert payload["calibration_results"]["n"] == len(splits["calibration"])
    weights = json.loads(initial)["weights"]
    assert payload["weights"] == weights
    assert (ROOT / "policy" / "calibration" / "cal-initial.json").is_file()
    assert (ROOT / "policy" / "calibration" / "ACTIVE").read_text(encoding="utf-8") == active
    assert os.environ["LLM_PROVIDER"] == "offline"
