"""P14A-T6 and T7: action drafts and the brief wording validator."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.agents.reporter import NAME, ReporterAgent, build_drafts
from app.errors import OfflineProvider
from app.llm.generator import GenerationResult
from app.schemas.case import CaseInput
from app.schemas.report import BriefWording
from app.state import new_state
from tests.unit.agents.support import AS_OF, baseline_facts, events, fact, make_ctx, record_for

pytestmark = pytest.mark.p14a


def _state(record: object, *, legal_name: str = "Acme Payroll Ltd", owner: str = "Alex Owner") -> object:
    state = new_state(
        CaseInput(vendor_id="VND-0001"),
        run_id="test-run",
        as_of=AS_OF,
        mode={"data": "duckdb", "llm": "offline"},
        budget_deadline=float("inf"),
    )
    state.decision = record  # type: ignore[assignment]
    state.profile["legal_name"] = legal_name
    state.profile["business_owner"] = owner
    return state


def test_p14a_t6_escalate_ticket_and_decline_memo() -> None:
    """P14A-T6: escalation drafts a ticket; a decline is a memo to the business owner."""
    failing = [item for item in baseline_facts() if item.key not in {"mfa.admin_enforced", "crypto.at_rest"}]
    failing.append(fact("F-C01-1", "mfa.admin_enforced", False, state="FALSE", kind="vendor_answer"))
    escalated = record_for(failing)
    assert escalated.outcome == "ESCALATE"
    drafts = build_drafts(escalated, _state(escalated))
    ticket = "\n".join(draft.subject + "\n" + draft.body for draft in drafts)
    assert "ticket" in ticket.lower()
    assert len(ticket) > 80

    declined_facts = [item for item in baseline_facts() if item.key != "sanctions.watchlist_matches"]
    declined_facts.append(fact("F-C11-1", "sanctions.watchlist_matches", 1))
    declined = record_for(declined_facts)
    assert declined.outcome == "DECLINE"
    memo = "\n".join(draft.subject + "\n" + draft.body for draft in build_drafts(declined, _state(declined)))
    assert "business owner" in memo.lower()
    assert "Alex Owner" in memo


def test_p14a_t7_invented_number_or_name_falls_back(tmp_path: Path) -> None:
    """P14A-T7: a model that invents a number or a vendor name is rejected for template:v2."""

    def fake(_prompt: str, **kwargs: object) -> GenerationResult:
        if kwargs.get("purpose") == "brief":
            return GenerationResult(
                text="{}",
                parsed=BriefWording(
                    headline="NotAVendor lost 99999 records",
                    why=["NotAVendor reported 99999 failures"],
                ),
                provider="fake",
                route="deep",
                model="fake-model",
                latency_ms=1,
            )
        raise OfflineProvider("cited report stays on the template")

    failing = [item for item in baseline_facts() if item.key != "mfa.admin_enforced"]
    failing.append(fact("F-C01-1", "mfa.admin_enforced", False, state="FALSE", kind="vendor_answer"))
    record = record_for(failing)
    ctx = make_ctx(tmp_path, generator=fake)
    state = _state(record, legal_name="Pellucid Forms Ltd")
    ReporterAgent()(state, ctx)
    brief = state.report.brief
    assert brief is not None
    assert brief.generator == "template:v2"
    prose = brief.headline + "\n" + "\n".join(point.text for point in brief.why)
    assert "99999" not in prose
    assert "NotAVendor" not in prose
    traced = events(ctx)
    assert any(row["status"] == "fallback" and row.get("purpose") == "brief" for row in traced)
    assert NAME == "ReporterAgent"
