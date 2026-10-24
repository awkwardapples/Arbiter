"""P15-T6: the published live eval equals render(latest live summary): three systems, live model ids."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from eval import report

pytestmark = pytest.mark.p15

ROOT = Path(__file__).resolve().parents[3]
LIVE_ROOT = ROOT / "eval" / "results_live"
_SYSTEMS = {"arbiter", "baseline", "arbiter_offline"}


def _block(text: str) -> str:
    start = text.index(report.EVAL_START) + len(report.EVAL_START)
    return text[start : text.index(report.EVAL_END)].strip()


def test_p15_t6_evaluation_block_equals_latest_live_summary() -> None:
    summary = report.latest_summary(LIVE_ROOT)
    text = (ROOT / "docs" / "EVALUATION.md").read_text(encoding="utf-8")
    assert _block(text) == report.render_summary_md(summary).strip()
    assert set(summary["systems"]) == _SYSTEMS
    live = summary["systems"]["arbiter"]["run"]
    assert live["mode"] == {"data": "zetaris", "llm": "meterless"}
    assert any("nemotron" in model for model in live["model_ids"])
    assert summary["systems"]["arbiter_offline"]["run"]["mode"] == {"data": "duckdb", "llm": "offline"}


def _summary(**overrides: Any) -> dict[str, Any]:
    def system(
        mode: dict[str, str], models: list[str], lanes: dict[str, list[str]], n: int
    ) -> dict[str, Any]:
        return {
            "accuracy": {"rate": 1.0, "correct": n, "n": n},
            "unsafe_approvals": {"count": 0, "n": n},
            "invalid_rate": {"rate": 0.0, "count": 0, "n": n},
            "abstention_rate": {"rate": 0.0, "count": 0, "n": n},
            "run": {
                "mode": mode,
                "n": n,
                "case_refs": [f"VND-{i:04d}" for i in range(1, n + 1)],
                "model_ids": models,
                "routed_models": lanes,
                "latency_ms": {"p50": 40000, "p95": 52000},
                "model_calls_per_case": 6.0,
                "fallback_rate": {"rate": 0.1, "count": 3, "n": 30},
            },
        }

    vl = "nvidia/nemotron-3.5-super-vl-120b-a12b"
    summary: dict[str, Any] = {
        "splits": ["test"],
        "split_sha256": {"test": "abc"},
        "n": 15,
        "mode": {"data": "mixed", "llm": "mixed"},
        "offline": False,
        "provider": "meterless",
        "model_ids": [vl],
        "synthetic": True,
        "git_sha": "deadbeef",
        "generated_at": "2026-10-25T00:00:00Z",
        "live_subset": {"n": 5, "rule": "first 5 test cases by case_id"},
        "systems": {
            "arbiter": system({"data": "zetaris", "llm": "meterless"}, [vl], {"fast": [vl], "deep": [vl]}, 5),
            "baseline": system({"data": "zetaris", "llm": "meterless"}, [vl], {"deep": [vl]}, 5),
            "arbiter_offline": system({"data": "duckdb", "llm": "offline"}, [], {}, 15),
        },
    }
    summary.update(overrides)
    return summary


def test_p15_t6_render_three_way_with_lanes_and_subset() -> None:
    text = report.render_summary_md(_summary())
    for name in sorted(_SYSTEMS):
        assert f"| {name} |" in text
    assert "zetaris / meterless" in text and "duckdb / offline" in text
    assert "n=5 for the live systems, n=15 for the offline system" in text
    assert "first 5 test cases by case_id" in text
    assert "fast lane routed to: nvidia/nemotron-3.5-super-vl-120b-a12b" in text
    assert "deep lane routed to: nvidia/nemotron-3.5-super-vl-120b-a12b" in text
    # The same model served both lanes, so the deviation is stated, computed from the summary.
    assert (
        "both the fast and deep lanes were served by nvidia/nemotron-3.5-super-vl-120b-a12b" in text.lower()
    )
    assert "p50" in text and "p95" in text and "fallback" in text.lower()


def test_p15_t6_no_deviation_when_lanes_differ() -> None:
    summary = _summary()
    summary["systems"]["arbiter"]["run"]["routed_models"]["fast"] = ["nvidia/nemotron-3.5-lightning-30b-a3b"]
    assert "both the fast and deep lanes" not in report.render_summary_md(summary).lower()


def test_p15_t6_publish_keeps_hand_written_text(tmp_path: Path) -> None:
    docs = tmp_path / "EVALUATION.md"
    docs.write_text(
        f"# Evaluation\n\nintro\n\n{report.EVAL_START}\nold\n{report.EVAL_END}\n\n## Discussion\nkept\n",
        encoding="utf-8",
    )
    summary = _summary()
    report.publish(summary, docs_path=docs, readme_path=None)
    text = docs.read_text(encoding="utf-8")
    assert "intro" in text and "## Discussion\nkept" in text and "old" not in text
    assert _block(text) == report.render_summary_md(summary).strip()
    report.publish(summary, docs_path=docs, readme_path=None)
    assert docs.read_text(encoding="utf-8") == text


def test_p15_t6_committed_summary_is_json() -> None:
    found = sorted(LIVE_ROOT.glob("*/summary.json"))
    assert found, "publish the live eval into eval/results_live/"
    assert isinstance(json.loads(found[-1].read_text(encoding="utf-8")), dict)
