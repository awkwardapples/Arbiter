"""P13-T6: the model path sees the USL catalogue; the deterministic plan does not change."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.agents.catalogue import SCREEN_QUERIES, SCREEN_QUERIES_INLINE
from app.agents.llm_schemas import PlanOut
from app.agents.planner import PlannerAgent
from app.llm.generator import GenerationResult
from app.schemas.case import Answer, CaseInput, VendorSubmission
from tests.unit.agents.support import make_ctx, start

pytestmark = pytest.mark.p13

CATALOGUE_HEADING = "Semantic catalogue from the USL model vendor_risk"


def _submission() -> VendorSubmission:
    return VendorSubmission(
        legal_name="Inline Probe Ltd",
        category="SaaS",
        requested_service="Probe service",
        criticality="low",
        annual_spend_gbp=1000.0,
        data_categories=["internal"],
        processing_countries=["GB"],
        answers=[Answer(question_id="Q01", question="Is MFA enforced?", answer_text="Yes")],
    )


def _fake(calls: list[dict[str, Any]]) -> Any:
    def generate(prompt: str, **kwargs: Any) -> GenerationResult:
        calls.append({"prompt": prompt, **kwargs})
        return GenerationResult(
            text="{}",
            parsed=PlanOut(queries=[], extraction_targets=[], rationale="recorded"),
            provider="fake",
            route="deep",
            latency_ms=1,
        )

    return generate


def test_p13_t6_llm_prompt_contains_catalogue_and_query_tables(tmp_path: Path) -> None:
    """P13-T6: the model prompt carries the USL catalogue and the tables each query reads."""
    calls: list[dict[str, Any]] = []
    ctx = make_ctx(tmp_path, generator=_fake(calls))
    PlannerAgent()(start(ctx, CaseInput(vendor_id="VND-0003")), ctx)
    assert calls
    prompt = calls[0]["prompt"]
    assert CATALOGUE_HEADING in prompt
    assert "Q_VENDOR_CONTRACT" in prompt
    assert "vendor" in prompt and "contract" in prompt


def test_p13_t6_deterministic_plan_is_unchanged(tmp_path: Path) -> None:
    """P13-T6: offline planning still emits the screen set and does not load the USL model."""
    loaded: list[str] = []

    def _boom() -> None:
        loaded.append("load_model")
        raise AssertionError("deterministic plan must not load the USL model")

    import app.agents.planner as planner

    ctx = make_ctx(tmp_path)
    ctx.offline = True
    original = getattr(planner, "load_model", None)
    planner.load_model = _boom  # type: ignore[attr-defined]
    try:
        registered = PlannerAgent()(start(ctx, CaseInput(vendor_id="VND-0003")), ctx)
        submission = _submission()
        inline_ctx = make_ctx(tmp_path, submission=submission)
        inline_ctx.offline = True
        inline = PlannerAgent()(start(inline_ctx, CaseInput(submission=submission)), inline_ctx)
    finally:
        if original is None:
            if hasattr(planner, "load_model"):
                delattr(planner, "load_model")
        else:
            planner.load_model = original  # type: ignore[attr-defined]
    assert [s.query_id for s in registered.plans[-1].steps] == list(SCREEN_QUERIES)
    assert [s.query_id for s in inline.plans[-1].steps] == list(SCREEN_QUERIES_INLINE)
    assert loaded == []
