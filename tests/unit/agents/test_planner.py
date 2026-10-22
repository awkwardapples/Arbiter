"""P3-T6: the planner validator. Model output can choose registry ids, never params or SQL."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.agents.catalogue import SCREEN_QUERIES
from app.agents.llm_schemas import PlannedQuery, PlanOut
from app.agents.planner import PlannerAgent
from app.errors import ParseFailure
from app.llm.generator import GenerationResult
from app.schemas.case import CaseInput
from tests.unit.agents.support import events, make_ctx, start

pytestmark = pytest.mark.p3


def _fake(plan: PlanOut, calls: list[dict[str, Any]]) -> Any:
    def generate(prompt: str, **kwargs: Any) -> GenerationResult:
        calls.append({"prompt": prompt, **kwargs})
        return GenerationResult(text="{}", parsed=plan, provider="fake", route="deep", latency_ms=1)

    return generate


def _plan(tmp_path: Path, generator: Any) -> tuple[Any, list[dict[str, Any]]]:
    ctx = make_ctx(tmp_path, generator=generator)
    st = PlannerAgent()(start(ctx, CaseInput(vendor_id="VND-0003")), ctx)
    return st, events(ctx)


def test_p3_t6_unknown_ids_dropped_and_mandatory_readded(tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []
    out = PlanOut(
        queries=[
            PlannedQuery(query_id="Q_DROP_TABLES", reason="x"),
            PlannedQuery(query_id="Q_SUBMISSION_ANSWERS", reason="read the answers"),
        ],
        extraction_targets=[],
        rationale="minimal",
    )
    st, rows = _plan(tmp_path, _fake(out, calls))
    assert calls and calls[0]["purpose"] == "plan" and calls[0]["schema"] is PlanOut
    ids = [s.query_id for s in st.plans[-1].steps]
    assert "Q_DROP_TABLES" not in ids
    assert set(SCREEN_QUERIES) <= set(ids)
    corrected = [r for r in rows if r["agent_name"] == "PlannerAgent" and r["action"] == "plan_corrected"]
    assert corrected
    assert "Q_DROP_TABLES" in corrected[0]["output_summary"]


def test_p3_t6_parse_failure_falls_back_to_deterministic_plan(tmp_path: Path) -> None:
    def broken(prompt: str, **kwargs: Any) -> Any:
        raise ParseFailure("bad json after repair")

    st, rows = _plan(tmp_path, broken)
    assert st.plans[-1].source == "deterministic"
    assert set(SCREEN_QUERIES) <= {s.query_id for s in st.plans[-1].steps}
    fallback = [r for r in rows if r["agent_name"] == "PlannerAgent" and r["status"] == "fallback"]
    assert fallback and fallback[0]["provider"] == "offline"


def test_p3_t6_params_never_come_from_the_model(tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []
    out = PlanOut(
        queries=[
            PlannedQuery(
                query_id="Q_VENDOR_CONTRACT", params={"vendor_id": "VND-0001' OR '1'='1"}, reason="x"
            ),
            PlannedQuery(
                query_id="Q_VENDOR_INCIDENTS", params={"vendor_id": "VND-0019", "since": "1900-01-01"}
            ),
        ],
        extraction_targets=[],
        rationale="malicious",
    )
    st, _ = _plan(tmp_path, _fake(out, calls))
    steps = {s.query_id: s for s in st.plans[-1].steps}
    assert steps["Q_VENDOR_CONTRACT"].params == {"vendor_id": "VND-0003"}
    assert steps["Q_VENDOR_INCIDENTS"].params["vendor_id"] == "VND-0003"
    assert steps["Q_VENDOR_INCIDENTS"].params["since"] == "2024-10-26"
    for step in st.plans[-1].steps:
        assert "OR" not in str(step.params) and "VND-0019" not in str(step.params)


def test_p3_t6_degraded_provider_skips_the_model(tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []
    ctx = make_ctx(tmp_path, generator=_fake(PlanOut(queries=[], extraction_targets=[], rationale=""), calls))
    ctx.degraded = True
    st = PlannerAgent()(start(ctx, CaseInput(vendor_id="VND-0003")), ctx)
    assert not calls
    assert st.plans[-1].source == "deterministic"
