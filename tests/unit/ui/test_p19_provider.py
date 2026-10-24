"""P19-T4: the provider sidebar names the served model; spinner copy; Streamlit toolbar."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from tests.unit.ui.p14b_support import live_health

pytestmark = pytest.mark.p19

ROOT = Path(__file__).resolve().parents[3]
TRACE = ROOT / "logs" / "examples" / "live" / "trace-run-83de5da137c0.jsonl"


def test_p19_t4_sidebar_names_served_model() -> None:
    import ui.provider as provider

    events = [json.loads(line) for line in TRACE.read_text(encoding="utf-8").splitlines() if line.strip()]
    lines = provider.provider_lines(live_health(), events)
    blob = "\n".join(lines)
    assert "deep → nvidia/nemotron-3.5-super-vl-120b-a12b" in blob
    assert "fast → nvidia/nemotron-3.5-super-vl-120b-a12b" in blob
    assert "meterless/auto" not in blob


def test_p19_t4_served_ignores_provider_model() -> None:
    """provider_model is the routing mode; winning_route.model is the last resort."""
    import ui.provider as provider

    event = {
        "provider": "meterless",
        "route": "deep",
        "provider_meta": {"provider_model": "meterless/auto", "winning_route.model": "nvidia/x"},
    }
    assert provider._served([event])[0] == {"deep": "nvidia/x"}  # noqa: SLF001


def test_p19_t4_spinner_copy() -> None:
    from ui.screens import ASSESSMENT_SPINNER

    assert ASSESSMENT_SPINNER == (
        "Running the assessment. Sample mode takes a few seconds; "
        "a live run takes about 2–4 minutes (measured median 142 s)."
    )


def test_p19_t4_streamlit_toolbar_minimal() -> None:
    config = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    assert config["client"]["toolbarMode"] == "minimal"
