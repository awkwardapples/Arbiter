"""P3-T8: the Reporter validator keeps the report honest; the template covers every failure."""

from __future__ import annotations

import pytest

from app.agents.llm_schemas import ReportOut
from app.agents.reporter import QUESTION_TEXTS, template_report, validate_report
from app.schemas.report import CitedSentence
from tests.unit.agents.support import baseline_facts, fact, record_for

pytestmark = pytest.mark.p3


def _failing_record() -> object:
    facts = [f for f in baseline_facts() if f.key not in {"mfa.admin_enforced", "crypto.at_rest"}]
    facts.append(fact("F-C01-1", "mfa.admin_enforced", False, state="FALSE", kind="vendor_answer"))
    return record_for(facts)


def _request_info_record() -> object:
    return record_for([f for f in baseline_facts() if f.key != "crypto.at_rest"])


def _known(record: object) -> set[str]:
    ids = {f.fact_id for f in record.facts}  # type: ignore[attr-defined]
    ids |= {f"R-{c.control_id}" for c in record.controls}  # type: ignore[attr-defined]
    return ids


def _out(summary: str, rationale: list[CitedSentence]) -> ReportOut:
    return ReportOut(
        summary=summary,
        rationale=rationale,
        recommended_actions=["Open an ITSM ticket for the TPRM lead."],
        clarification_email=None,
        escalation_note="C01 failed.",
        limitations=["Synthetic data."],
    )


def test_p3_t8_uncited_and_unknown_citations_dropped() -> None:
    record = _failing_record()
    assert record.outcome == "ESCALATE"
    out = _out(
        "Outcome ESCALATE: admin MFA is not enforced [F-C01-1].",
        [
            CitedSentence(text="Admin MFA is not enforced.", citations=["F-C01-1", "R-C01"]),
            CitedSentence(text="An uncited opinion.", citations=[]),
            CitedSentence(text="A made-up citation.", citations=["F-C99-9"]),
        ],
    )
    report = validate_report(out, record, known_ids=_known(record), generator="meterless/deep:test")
    assert report is not None
    assert [s.text for s in report.rationale] == ["Admin MFA is not enforced."]
    assert report.generator == "meterless/deep:test"


def test_p3_t8_outcome_mismatch_rejected() -> None:
    record = _failing_record()
    out = _out(
        "Outcome APPROVE: the vendor meets policy.",
        [CitedSentence(text="Admin MFA is not enforced.", citations=["F-C01-1"])],
    )
    assert validate_report(out, record, known_ids=_known(record), generator="meterless/deep:test") is None


def test_p3_t8_template_mentions_every_failing_control_and_counterfactual() -> None:
    record = _failing_record()
    report = template_report(record)
    assert report.generator == "template:v1"
    text = " ".join([report.summary, *(s.text for s in report.rationale)])
    failing = {c.control_id for c in record.controls if c.state != "TRUE"}
    assert failing == {"C01", "C04"}
    for control_id in failing | {cf.control_id for cf in record.counterfactuals}:
        assert control_id in text
    assert record.outcome in report.summary
    for sentence in report.rationale:
        assert sentence.citations


def test_p3_t8_request_info_template_drafts_clarification_email() -> None:
    record = _request_info_record()
    assert record.outcome == "REQUEST_INFO"
    report = template_report(record)
    assert report.clarification_email is not None
    assert QUESTION_TEXTS["Q05"] in report.clarification_email.body
