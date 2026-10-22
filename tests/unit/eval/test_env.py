"""P5-T7: model ids and the offline label come from trace events."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.p5b


def test_p5_t7_models_and_offline_label_come_from_traces(tmp_path: Path) -> None:
    """P5-T7: env model ids are the trace's model fields, and provider=offline is labelled offline."""
    from eval.harness import describe_run
    from eval.report import render_summary_md

    trace = tmp_path / "trace-run.jsonl"
    trace.write_text(
        "\n".join(
            [
                json.dumps({"provider": "offline", "model": "from-trace-model", "status": "fallback"}),
                json.dumps({"provider": "offline", "model": None, "status": "success"}),
                json.dumps({"provider": "duckdb", "status": "success"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    info = describe_run([trace])
    assert info["model_ids"] == ["from-trace-model"]
    assert info["offline"] is True
    summary = {
        "splits": ["test"],
        "n": 1,
        "mode": {"data": "duckdb", "llm": "offline"},
        "offline": info["offline"],
        "model_ids": info["model_ids"],
        "synthetic": True,
        "systems": {},
    }
    rendered = render_summary_md(summary)
    assert "offline" in rendered.lower()
    assert "from-trace-model" in rendered
    assert "meterless/fast" not in rendered

    live = tmp_path / "trace-live.jsonl"
    live.write_text(
        json.dumps({"provider": "meterless", "model": "nvidia/nemotron", "status": "success"}) + "\n",
        encoding="utf-8",
    )
    clean = describe_run([live])
    assert clean["model_ids"] == ["nvidia/nemotron"]
    assert clean["offline"] is False
