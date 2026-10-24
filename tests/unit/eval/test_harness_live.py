"""P15: harness live switches. No services: these check option selection, env and per-system run blocks."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from eval import harness

pytestmark = pytest.mark.p15


def test_p15_live_options_per_system() -> None:
    live = harness.system_options("arbiter", live=True)
    assert (live.sample_mode, live.llm) == (False, "meterless")
    offline = harness.system_options("arbiter_offline", live=True)
    assert (offline.sample_mode, offline.llm) == (True, "offline")
    default = harness.system_options("arbiter", live=False)
    assert (default.sample_mode, default.llm) == (True, "offline")


def test_p15_live_env_is_scoped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAMPLE_MODE", "true")
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    with harness.system_env("baseline", live=True) as settings:
        assert os.environ["SAMPLE_MODE"] == "false"
        assert os.environ["LLM_PROVIDER"] == "meterless"
        assert os.environ["ARBITER_MEMORY"] == "off"
        assert settings.SAMPLE_MODE is False
    with harness.system_env("arbiter_offline", live=True) as settings:
        assert os.environ["LLM_PROVIDER"] == "offline"
        assert settings.SAMPLE_MODE is True


def test_p15_case_subset_is_first_n_by_case_id() -> None:
    refs = ["VND-0009", "VND-0001", "VND-0004", "inline_kev", "VND-0003"]
    assert harness.select_cases(refs, None) == refs
    assert harness.select_cases(refs, 3) == ["VND-0001", "VND-0003", "VND-0004"]


def _event(**kw: object) -> str:
    base = {"agent_name": "A", "action": "x", "status": "success"}
    return json.dumps({**base, **kw})


def test_p15_run_block_from_traces(tmp_path: Path) -> None:
    vl = "nvidia/nemotron-3.5-super-vl-120b-a12b"
    trace = tmp_path / "trace-run-1.jsonl"
    trace.write_text(
        "\n".join(
            [
                _event(backend="zetaris", query_id="Q_VENDOR_PROFILE"),
                _event(
                    action="model_call",
                    provider="meterless",
                    route="fast",
                    model=vl,
                    provider_meta={"routed_model": vl},
                ),
                _event(
                    action="model_call",
                    provider="meterless",
                    route="deep",
                    model=vl,
                    provider_meta={"routed_model": vl},
                ),
                _event(action="model_call", provider="meterless", route="fast", status="fallback"),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rows = [
        {"case_ref": "VND-0001", "repeat": 0, "latency_ms": 1000, "trace_path": str(trace)},
        {"case_ref": "VND-0003", "repeat": 0, "latency_ms": 3000, "trace_path": ""},
    ]
    block = harness.run_block(rows, mode={"data": "zetaris", "llm": "meterless"})
    assert block["mode"] == {"data": "zetaris", "llm": "meterless"}
    assert block["n"] == 2
    assert block["case_refs"] == ["VND-0001", "VND-0003"]
    assert block["model_ids"] == [vl]
    assert block["routed_models"] == {"deep": [vl], "fast": [vl]}
    assert block["latency_ms"] == {"p50": 2000, "p95": 3000}
    assert block["model_calls_per_case"] == 1.5
    assert block["fallback_rate"] == {"rate": pytest.approx(1 / 3), "count": 1, "n": 3}
