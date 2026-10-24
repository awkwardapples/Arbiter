"""P19-T6: each outcome's brief headline starts with its own phrase."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.labels import build_brief
from app.orchestrator import RunOptions, run
from app.store import Store
from tests.e2e.support import EXAMPLE_FILES, expected, load_example, offline_env

pytestmark = pytest.mark.p19
__all__ = ["offline_env"]

LEADS = {
    "ESCALATE": "Escalate to the TPRM lead: ",
    "REQUEST_INFO": "Ask the vendor for more information: ",
    "DECLINE": "Decline, and tell the business owner: ",
    "APPROVE_WITH_CONDITIONS": "Approve with conditions: ",
    "APPROVE": "Approve: ",
}
_OLD = (" to the approval record", "Request information to", "Decline to the")


def test_p19_t6_six_examples(offline_env: Path) -> None:
    """The six sample examples, run offline: headline phrase per outcome."""
    del offline_env
    wanted = expected()
    seen: set[str] = set()
    with_points = None
    for name in EXAMPLE_FILES:
        response = run(load_example(name), options=RunOptions())
        assert response.output is not None
        bundle = Store().get(response.output.case_id)
        outcome = bundle.decision.outcome
        assert outcome == wanted[name]["outcome"], name
        brief = bundle.report.brief
        assert brief is not None
        assert brief.headline.startswith(LEADS[outcome]), (name, brief.headline)
        assert not any(old in brief.headline for old in _OLD), brief.headline
        if outcome == "APPROVE" and not brief.why:
            assert brief.headline.endswith("meets the checks this assessment could verify.")
        if brief.why and with_points is None:
            with_points = bundle.decision
        seen.add(outcome)
    assert seen == {"APPROVE", "ESCALATE", "REQUEST_INFO", "DECLINE"}

    # The examples do not reach APPROVE_WITH_CONDITIONS, nor APPROVE with why-points:
    # the same record under each outcome covers every phrase.
    assert with_points is not None
    for outcome, lead in LEADS.items():
        headline = build_brief(with_points.model_copy(update={"outcome": outcome})).headline
        assert headline.startswith(lead), headline
        assert not any(old in headline for old in _OLD), headline
