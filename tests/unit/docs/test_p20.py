"""P20-T1, T4, T5: the live re-run evidence and the documents that cite it. Runs on committed files."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.report import latest_summary, render_summary_md
from scripts.check_trace import validate_file

pytestmark = pytest.mark.p20

ROOT = Path(__file__).resolve().parents[3]
LIVE = ROOT / "logs" / "examples" / "live"
PROOF = ROOT / "docs" / "evidence" / "nightshift_proof.json"
_MODEL_KEYS = ("model", "routed_model", "response_model", "winning_route_model")


def _live_traces() -> list[Path]:
    return sorted(LIVE.glob("trace-*.jsonl"))


def test_p20_t1_live_traces_are_live_and_collaborative() -> None:
    traces = _live_traces()
    assert traces, "no live example traces committed"
    for path in traces:
        assert validate_file(path, require_collaboration=True, require_live=True) == [], path.name


def _served_models() -> set[str]:
    """Model ids from successful Nightshift calls in the live examples, plus the proof receipts."""
    found: set[str] = set()
    for path in _live_traces():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("provider") == "meterless" and event.get("model"):
                found.add(event["model"])
            meta = event.get("provider_meta") or {}
            found.update(str(meta[key]) for key in _MODEL_KEYS if meta.get(key))
    proof = json.loads(PROOF.read_text(encoding="utf-8"))
    for lane in ("fast", "deep"):
        found.update(str(proof[lane][key]) for key in _MODEL_KEYS if proof[lane].get(key))
    return found


def test_p20_t4_metadata_models_were_served() -> None:
    models = json.loads((ROOT / "metadata.json").read_text(encoding="utf-8"))["models"]
    assert models
    missing = set(models) - _served_models()
    assert not missing, sorted(missing)


def test_p20_t5_readme_eval_block_is_latest_live_summary() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    start = text.index("<!-- EVAL:START -->") + len("<!-- EVAL:START -->")
    block = text[start : text.index("<!-- EVAL:END -->")].strip("\n")
    assert block == render_summary_md(latest_summary(ROOT / "eval" / "results_live")).strip("\n")
