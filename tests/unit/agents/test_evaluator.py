"""P3-T5: the Evaluator sends the Planner back for exactly the system-of-record checks the claims need."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.schemas.case import CaseInput
from tests.unit.agents.support import events, iterate, make_ctx, start

pytestmark = pytest.mark.p3


def _suggested(evaluation: object) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for gap in evaluation.gaps:  # type: ignore[attr-defined]
        out.setdefault(gap.control_id, set()).update(gap.suggested_query_ids)
    return out


def test_p3_t5_screen_then_verify_suggestions(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path)
    st = iterate(start(ctx, CaseInput(vendor_id="VND-0007")), ctx)
    first = st.evaluations[-1]
    assert not first.sufficient
    suggested = _suggested(first)
    assert "Q_VENDOR_CONTRACT" in suggested["C09"]
    assert "Q_COMPONENT_KEV" in suggested["C12"]
    assert "Q_VENDOR_INCIDENTS" in suggested["C06"]
    executed = set(st.executed_queries)
    assert not executed & set().union(*suggested.values())
    rows = events(ctx)
    revision = [r for r in rows if r["agent_name"] == "EvaluatorAgent" and r["status"] == "needs_revision"]
    assert revision and revision[-1]["target_agent"] == "PlannerAgent"
    assert "C09" in revision[-1]["output_summary"]


def test_p3_t5_no_components_means_no_kev_suggestion(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path)
    st = iterate(start(ctx, CaseInput(vendor_id="VND-0003")), ctx)
    every = set().union(*(set(g.suggested_query_ids) for e in st.evaluations for g in e.gaps))
    assert "Q_COMPONENT_KEV" not in every
    assert "Q_VENDOR_INCIDENTS" in every
    kev = next(f for f in st.facts if f.key == "vuln.kev_matches")
    assert kev.value == 0


def test_p3_t5_material_contradiction_gets_one_confirm_requery(tmp_path: Path) -> None:
    ctx = make_ctx(tmp_path)
    st = start(ctx, CaseInput(vendor_id="VND-0007"))
    st = iterate(st, ctx)
    st = iterate(st, ctx)
    second = st.evaluations[-1]
    assert any(c.key == "residency.regions" and c.severity == "material" for c in second.contradictions)
    assert "Q_VENDOR_CONTRACT" in _suggested(second).get("C09", set())
    assert st.query_counts["Q_VENDOR_CONTRACT"] == 1

    st = iterate(st, ctx)
    third = st.evaluations[-1]
    assert st.query_counts["Q_VENDOR_CONTRACT"] == 2
    assert third.sufficient
    assert "Q_VENDOR_CONTRACT" not in set().union(*(set(g.suggested_query_ids) for g in third.gaps))
    assert any(c.key == "residency.regions" and not c.resolved for c in third.contradictions)
