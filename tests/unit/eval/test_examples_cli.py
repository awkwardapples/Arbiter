"""P15: `run.py examples` writes live runs and the sample-mode set to separate directories."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.cli import examples

pytestmark = pytest.mark.p15

ROOT = Path(__file__).resolve().parents[3]


def test_p15_example_directories() -> None:
    assert examples.example_dirs(live=True) == (ROOT / "output_examples", ROOT / "logs" / "examples" / "live")
    assert examples.example_dirs(live=False) == (
        ROOT / "output_examples" / "sample_mode",
        ROOT / "logs" / "examples" / "sample_mode",
    )


@pytest.mark.parametrize(
    ("mode", "live"),
    [
        ({"data": "zetaris", "llm": "meterless"}, True),
        ({"data": "zetaris", "llm": "nvidia"}, False),
        ({"data": "zetaris", "llm": "auto"}, False),
        ({"data": "zetaris", "llm": "offline"}, False),
        ({"data": "duckdb", "llm": "meterless"}, False),
        ({"data": "zetaris", "llm": ""}, False),
    ],
)
def test_p15_is_live_reads_the_recorded_provider(mode: dict[str, str], live: bool) -> None:
    assert examples._is_live(mode) is live
