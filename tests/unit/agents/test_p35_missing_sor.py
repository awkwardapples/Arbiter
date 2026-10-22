"""P3.5-T1: request a verify query only when a grounded claim has no SoR counterpart."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.agents.evaluator import _gaps
from app.schemas.case import CaseInput
from app.schemas.common import Provenance
from app.schemas.evidence import Fact
from app.state import new_state
from tests.unit.agents.support import AS_OF, baseline_facts, make_ctx

pytestmark = pytest.mark.p3


def _claim_fact(key: str, value: object, *, state: str = "TRUE", grounded: bool = True) -> Fact:
    return Fact(
        fact_id="F-C09-1",
        control_id="C09",
        key=key,
        value=value,  # type: ignore[arg-type]
        state=state,  # type: ignore[arg-type]
        provenance=[Provenance(kind="vendor_answer", quote="EU-only residency for production data.")],
        derived_from_claims=["CL-Q10-1"] if grounded else [],
    )


def _sor_fact() -> Fact:
    return Fact(
        fact_id="F-C09-2",
        control_id="C09",
        key="residency.regions_contract",
        value=["US"],
        state="TRUE",
        provenance=[Provenance(kind="system_of_record", query_id="Q_VENDOR_CONTRACT")],
    )


def _queries(tmp_path: Path, facts: list[Fact]) -> set[str]:
    ctx = make_ctx(tmp_path)
    state = new_state(
        CaseInput(vendor_id="VND-0900"),
        run_id="test-run",
        as_of=AS_OF,
        mode={"data": "duckdb", "llm": "offline"},
        budget_deadline=float("inf"),
    )
    state.facts = facts
    gaps = _gaps(state, ctx, "T3")
    return {query for gap in gaps for query in gap.suggested_query_ids}


def test_p35_t1_missing_sor_requests_contract_verify(tmp_path: Path) -> None:
    """P3.5-T1: EU residency claim, no contract fact, C09 not applicable → Q_VENDOR_CONTRACT."""
    facts = [
        *baseline_facts(),
        _claim_fact("residency.regions_claimed", ["EU"]),
    ]
    assert "Q_VENDOR_CONTRACT" in _queries(tmp_path, facts)


def test_p35_t1_both_facts_present_does_not_request(tmp_path: Path) -> None:
    """P3.5-T1: claim and residency.regions_contract both present → no extra contract query."""
    facts = [
        *baseline_facts(),
        _claim_fact("residency.regions_claimed", ["EU"]),
        _sor_fact(),
    ]
    assert "Q_VENDOR_CONTRACT" not in _queries(tmp_path, facts)


def test_p35_t1_no_grounded_claim_does_not_request(tmp_path: Path) -> None:
    """P3.5-T1: an ungrounded residency answer does not request the contract."""
    facts = [
        *baseline_facts(),
        _claim_fact("residency.regions_claimed", None, state="UNKNOWN", grounded=False),
    ]
    assert "Q_VENDOR_CONTRACT" not in _queries(tmp_path, facts)
