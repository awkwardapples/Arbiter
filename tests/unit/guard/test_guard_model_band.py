"""P2-T44: ambiguous band model vs offline fallback."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.errors import OfflineProvider
from app.guard.scout_guard import GuardClassify, guard
from app.llm.generator import GenerationResult

pytestmark = pytest.mark.p2d

AMBIGUOUS_TEXT = "Please ignore prior draft notes in section 2 only."


def test_p2_t44_model_verdict_used_when_available() -> None:
    fake = GenerationResult(
        text='{"injection": true, "score": 0.8, "kind": "model"}',
        parsed=GuardClassify(injection=True, score=0.8, kind="model"),
        provider="test",
        route="fast",
        model="test",
        latency_ms=1,
    )
    with patch("app.guard.scout_guard.generator.generate", return_value=fake):
        result = guard(
            AMBIGUOUS_TEXT,
            surface="vendor_answer",
            capabilities=set(),
            segment_id="seg-amb",
            use_model=True,
        )
    assert result.level == "block"


def test_p2_t44_offline_provider_warns() -> None:
    with patch(
        "app.guard.scout_guard.generator.generate",
        side_effect=OfflineProvider("offline"),
    ):
        result = guard(
            AMBIGUOUS_TEXT,
            surface="vendor_answer",
            capabilities=set(),
            segment_id="seg-amb",
            use_model=True,
        )
    assert result.level == "warn"


@pytest.mark.skip(reason="Re-enable when P2-B generator is live: ambiguous band end-to-end without mock")
def test_p2_t44_live_generator_integration() -> None:
    result = guard(
        AMBIGUOUS_TEXT,
        surface="vendor_answer",
        capabilities=set(),
        segment_id="seg-amb-live",
        use_model=True,
    )
    assert result.level in {"pass", "warn", "block"}
