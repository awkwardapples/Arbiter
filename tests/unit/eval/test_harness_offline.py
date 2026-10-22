"""P5-T2: the offline test-split command finishes and writes every metric key."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.p5b

ROOT = Path(__file__).resolve().parents[3]
METRIC_KEYS = (
    "accuracy",
    "macro_f1",
    "unsafe_approvals",
    "over_escalations",
    "failing_control_recall",
    "contradiction_recall",
    "contradiction_precision",
    "injection_detection",
    "injection_false_positive_rate",
    "fact_accuracy",
    "grounding_rate",
    "consistency",
    "abstention_rate",
    "selective_accuracy",
    "invalid_rate",
    "cost",
    "fallback_rate",
)


def test_p5_t2_offline_test_split(tmp_path: Path) -> None:
    """P5-T2: eval --split test --systems arbiter_offline,baseline --llm offline completes on DuckDB."""
    env = os.environ.copy()
    env["SAMPLE_MODE"] = "true"
    env["LLM_PROVIDER"] = "offline"
    env["ARBITER_MEMORY"] = "off"
    env["ARBITER_EVAL_ROOT"] = str(tmp_path)
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "run.py"),
            "eval",
            "--split",
            "test",
            "--systems",
            "arbiter_offline,baseline",
            "--llm",
            "offline",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    summaries = sorted(tmp_path.glob("**/summary.json"))
    assert len(summaries) == 1
    summary = json.loads(summaries[0].read_text(encoding="utf-8"))
    splits = json.loads((ROOT / "data" / "evals" / "splits.json").read_text(encoding="utf-8"))
    assert summary["splits"] == ["test"]
    assert "calibration" not in summary["splits"]
    systems = summary["systems"]
    assert set(systems) == {"arbiter_offline", "baseline"}
    for block in systems.values():
        missing = [key for key in METRIC_KEYS if key not in block]
        assert missing == []
        assert block["accuracy"]["n"] == len(splits["test"])
    assert systems["baseline"]["invalid_rate"]["rate"] == 1.0
    assert systems["arbiter_offline"]["invalid_rate"]["rate"] is None
    env_doc = json.loads((summaries[0].parent / "env.json").read_text(encoding="utf-8"))
    assert env_doc["split_sha256"]["test"] == splits["sha256"]["test"]
    assert env_doc["mode"]["data"] == "duckdb"
    assert env_doc["mode"]["llm"] == "offline"
    blob = json.dumps(env_doc).lower()
    assert "zetaris" not in blob
    assert "meterless" not in blob
