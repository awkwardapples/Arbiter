"""P14A-T10: every analyst-facing code in the policy and registry has a plain label."""

from __future__ import annotations

import pytest
from app.data.registry import load_registry
from app.labels import control_title, ...
from app.policy.loader import load_default

pytestmark = pytest.mark.p14a

_OUTCOMES = ("APPROVE", "APPROVE_WITH_CONDITIONS", "REQUEST_INFO", "ESCALATE", "DECLINE")
_SYSTEMS = {
    "procurement": "Procurement (ERP)",
    "clm": "Contract system (CLM)",
    "itsm": "Service desk (ITSM)",
    "grc_watchlist": "Sanctions watchlist (GRC)",
    "trust_portal": "Vendor trust portal",
    "cisa_kev": "CISA Known Exploited Vulnerabilities",
}


def test_p14a_t10_label_coverage() -> None:
    """P14A-T10: outcomes, reasons, controls, systems and questions all have labels."""
    policy, _calibration = load_default()
    for outcome in _OUTCOMES:
        assert outcome_label(outcome)
        assert outcome_meaning(outcome)
        assert outcome not in outcome_label(outcome)
    for rule in policy.outcome_rules:
        text = reason_text(rule.reason)
        assert text
        assert rule.reason not in text
    for control in policy.controls:
        assert control_title(control.id) == control.title
    registry = load_registry()
    systems = {system for query in registry.values() for system in query.systems}
    assert systems == set(_SYSTEMS)
    for system, label in _SYSTEMS.items():
        assert system_label(system) == label
    question_ids = {qid for control in policy.controls for qid in control.question_ids}
    assert question_ids
    for question_id in question_ids:
        text = question_text(question_id)
        assert text
        assert question_id not in text
