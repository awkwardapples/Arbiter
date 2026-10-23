"""P8 UI polish: queue, case, review, and audit display."""

from __future__ import annotations

import inspect
import json

import pytest

from tests.unit.ui.conftest import FakeArbiterClient
from tests.unit.ui.test_pages_smoke import _run_page
from ui.client import ArbiterAPIError

pytestmark = pytest.mark.p5a

SPINNER_TEXT = "Running the assessment loop — this takes 2–5 seconds in sample mode, up to 60 seconds live…"

OUTCOME_SENTENCES = {
    "CONTRADICTION": "Contradiction on a system-of-record claim",
    "CONTROL_FAILED": "One or more controls failed",
    "EVIDENCE_MISSING": "Evidence is missing for a required control",
    "LOW_CONFIDENCE_ABSTAIN": "Confidence below the gate — abstained",
    "HARD_GATE_DECLINE": "A hard gate requires decline",
    "HARD_GATE_ESCALATE": "A hard gate requires escalation",
    "ALL_REQUIRED_CONTROLS_MET": "All required controls met",
    "UNTRUSTED_CONTENT_TAMPERING": "Untrusted content tampering detected",
}

ELIGIBILITY_SENTENCES = {
    "mitigation_not_true": "The mitigation fact is not TRUE — this precedent can't apply",
    "no_exception_control_failing": "No exception-eligible control is failing",
    "non_exception_control_failing": "A control that can't be excepted is failing",
    "reviewer_authority": "The reviewer's role is below the required authority",
    "precedent_age": "The precedent is older than the 365-day window",
    "retrieval_quality": "H-MEM confidence or relevance is below the threshold",
    "tier_risk": "This case's risk tier is higher than the precedent's",
    "reviewer_role_insufficient": "The reviewer's role is below the required authority",
    "no_failing_controls": "No required control is failing",
    "decision_not_approving": "The review decision is not an approval",
}


def _text(elements) -> str:
    return " ".join(getattr(item, "value", "") or "" for item in elements)


def _button(at, label: str):
    return next(button for button in at.button if button.label == label)


def test_p8_spinner_text_is_the_approved_sentence() -> None:
    """The assessment spinner uses the approved sentence and does not cycle stages."""
    from ui.screens import ASSESSMENT_SPINNER, page_new_assessment

    assert ASSESSMENT_SPINNER == SPINNER_TEXT
    source = inspect.getsource(page_new_assessment)
    assert "ASSESSMENT_SPINNER" in source
    assert "stage" not in source.lower()


def test_p8_outcome_and_eligibility_maps() -> None:
    """Approved reason codes humanise; unknown codes stay raw."""
    from ui.components import humanise_eligibility_reason, humanise_outcome_reason

    for code, sentence in OUTCOME_SENTENCES.items():
        assert humanise_outcome_reason(code) == sentence
    assert humanise_outcome_reason("NOT_A_REAL_CODE") == "NOT_A_REAL_CODE"
    for code, sentence in ELIGIBILITY_SENTENCES.items():
        assert humanise_eligibility_reason(code) == sentence
    assert humanise_eligibility_reason("not_in_map") == "not_in_map"


def test_p8_replay_check_lines() -> None:
    from ui.components import replay_check_line

    assert replay_check_line("policy_hash", True) == "✓ policy hash matches"
    assert replay_check_line("record_hash", False) == "✗ record hash mismatch"
    assert replay_check_line("contract_signatures", True) == "✓ contract signatures matches"
    assert replay_check_line("some_other_check", False) == "✗ some other check mismatch"


def test_p8_control_rows_drop_rule_id() -> None:
    """rule_id stays on the control dict and is not a table column."""
    from ui.components import control_rows

    controls = [
        {
            "control_id": "C01",
            "title": "MFA",
            "state": "UNKNOWN",
            "rule_id": "C01",
            "fact_ids": ["F-C01-1", "F-C01-2"],
        }
    ]
    rows = control_rows(controls, [])
    assert list(rows[0]) == ["Control id", "Name", "Status", "Fact ids"]
    assert rows[0]["Control id"] == "C01"
    assert rows[0]["Fact ids"] == "F-C01-1, F-C01-2"
    assert "Rule" not in rows[0]
    assert controls[0]["rule_id"] == "C01"


def test_p8_evidence_lines() -> None:
    from ui.components import evidence_from_line, evidence_summary_line

    fact = {"key": "mfa.admin_enforced", "value": None, "state": "UNKNOWN"}
    assert evidence_summary_line(fact) == "`mfa.admin_enforced` = `null` → `UNKNOWN`"
    assert evidence_from_line(fact, {"quote": None}) == "From: No narrative is stored for this fact."
    assert evidence_from_line(fact, {"quote": "Quoted sentence."}) == "From: Quoted sentence."
    with_text = {**fact, "evidence_text": "Human sentence."}
    assert evidence_from_line(with_text, {"quote": "Quoted sentence."}) == "From: Human sentence."


def test_p8_queue_row_names_the_case(fake_client: FakeArbiterClient) -> None:
    at = _run_page("Queue", "pages/queue.py", client=fake_client)
    assert not at.exception
    assert "CASE-0007" in _text(at.markdown)


def test_p8_open_case_sets_state_and_switches(
    fake_client: FakeArbiterClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import streamlit as st

    switched: list[tuple[object, object, object]] = []

    def _switch(page: object, **_kwargs: object) -> None:
        switched.append(
            (
                page,
                st.session_state.get("last_case_id"),
                st.session_state.get("nav_case_id"),
            )
        )

    monkeypatch.setattr(st, "switch_page", _switch)
    at = _run_page("Queue", "pages/queue.py", client=fake_client)
    _button(at, "Open case").click()
    at.run()
    assert not at.exception
    assert at.session_state["last_case_id"] == "CASE-0007"
    assert at.session_state["nav_case_id"] == "CASE-0007"
    assert switched == [("pages/case.py", "CASE-0007", "CASE-0007")]


def test_p8_case_header_reasons_and_controls(fake_client: FakeArbiterClient) -> None:
    fake_client.case_detail["record"]["outcome_reasons"] = [
        "EVIDENCE_MISSING",
        "NOT_A_REAL_CODE",
    ]
    at = _run_page("Case", "pages/case.py", client=fake_client)
    assert not at.exception
    blob = _text(at.markdown)
    assert "**EVIDENCE_MISSING** — Evidence is missing for a required control" in blob
    assert "**NOT_A_REAL_CODE** — NOT_A_REAL_CODE" in blob
    frames = [frame.value for frame in at.dataframe]
    wanted = ["Control id", "Name", "Status", "Fact ids"]
    control = next(frame for frame in frames if list(frame.columns) == wanted)
    assert "Rule" not in control.columns
    assert "C01" in set(control["Control id"])
    assert control["Fact ids"].str.contains("F-C01").any()


def test_p8_evidence_hides_raw_json(fake_client: FakeArbiterClient) -> None:
    fact = fake_client.case_detail["record"]["facts"][0]
    fact["evidence_text"] = "Vendor stated MFA is enforced."
    fact["provenance"][0]["quote"] = "should not win"
    at = _run_page("Case", "pages/case.py", client=fake_client)
    assert not at.exception
    blob = _text(at.markdown)
    assert "`mfa.admin_enforced` = `null` → `UNKNOWN`" in blob
    assert "From: Vendor stated MFA is enforced." in blob
    assert "should not win" not in blob
    labels = [expander.label for expander in at.expander]
    assert "See raw" in labels
    raw_bodies = [code.value for code in at.code]
    assert any(json.loads(body).get("key") == "mfa.admin_enforced" for body in raw_bodies)
    for element in at.json:
        data = json.loads(element.value)
        if isinstance(data, dict):
            assert set(data) != {"key", "value", "state"}


def test_p8_review_eligibility_bullets(fake_client: FakeArbiterClient) -> None:
    def submit_review(case_id: str, body: object, *, dry_run: bool = False) -> dict[str, object]:
        del case_id, body
        assert dry_run
        return {
            "eligible": False,
            "reasons": ["mitigation_not_true", "reviewer_authority", "not_in_map"],
        }

    fake_client.submit_review = submit_review  # type: ignore[method-assign]
    at = _run_page("Review", "pages/review.py", client=fake_client)
    at.checkbox[0].check()
    at.run()
    _button(at, "Check eligibility").click()
    at.run()
    assert not at.exception
    warn = _text(at.warning)
    assert "**mitigation_not_true** — The mitigation fact is not TRUE — this precedent can't apply" in warn
    assert "**reviewer_authority** — The reviewer's role is below the required authority" in warn
    assert "**not_in_map** — not_in_map" in warn
    visible = _text(at.markdown) + _text(at.info) + _text(at.success) + warn
    assert '"eligible"' not in visible


def test_p8_review_eligibility_when_clear(fake_client: FakeArbiterClient) -> None:
    def submit_review(case_id: str, body: object, *, dry_run: bool = False) -> dict[str, object]:
        del case_id, body, dry_run
        return {"eligible": True, "reasons": []}

    fake_client.submit_review = submit_review  # type: ignore[method-assign]
    at = _run_page("Review", "pages/review.py", client=fake_client)
    at.checkbox[0].check()
    at.run()
    _button(at, "Check eligibility").click()
    at.run()
    assert not at.exception
    assert any("This case can create a C05 precedent." in item.value for item in at.success)


def test_p8_audit_replay_mismatch(fake_client: FakeArbiterClient) -> None:
    def replay(case_id: str) -> dict[str, object]:
        del case_id
        return {
            "match": False,
            "diff": ["facts.mfa.admin_enforced"],
            "checks": {
                "policy_hash": True,
                "record_hash": False,
                "contract_signatures": True,
            },
        }

    fake_client.replay = replay  # type: ignore[method-assign]
    at = _run_page("Audit", "pages/audit.py", client=fake_client)
    _button(at, "Replay CASE-0007").click()
    at.run()
    assert not at.exception
    assert any(item.value == "Mismatch — see diff" for item in at.error)
    blob = _text(at.markdown)
    assert "✓ policy hash matches" in blob
    assert "✗ record hash mismatch" in blob
    assert "✓ contract signatures matches" in blob
    assert "facts.mfa.admin_enforced" in blob
    assert not list(at.json)


def test_p8_audit_replay_match(fake_client: FakeArbiterClient) -> None:
    def replay(case_id: str) -> dict[str, object]:
        del case_id
        return {
            "match": True,
            "diff": [],
            "checks": {"policy_hash": True, "record_hash": True, "contract_signatures": True},
        }

    fake_client.replay = replay  # type: ignore[method-assign]
    at = _run_page("Audit", "pages/audit.py", client=fake_client)
    _button(at, "Replay CASE-0007").click()
    at.run()
    assert not at.exception
    assert any(item.value == "Match — the decision replays identically" for item in at.success)


def test_p8_audit_verify_broken(fake_client: FakeArbiterClient) -> None:
    fake_client.audit_verify = lambda: {"ok": False, "first_bad_seq": 4}  # type: ignore[method-assign]
    at = _run_page("Audit", "pages/audit.py", client=fake_client)
    _button(at, "Verify audit chain").click()
    at.run()
    assert not at.exception
    assert any(item.value == "Chain broken at sequence 4" for item in at.error)


def test_p8_audit_verify_count_from_result(fake_client: FakeArbiterClient) -> None:
    def health() -> dict[str, object]:
        raise ArbiterAPIError("down")

    fake_client.health = health  # type: ignore[method-assign]
    fake_client.audit_verify = lambda: {"ok": True, "first_bad_seq": None, "entries": 12}  # type: ignore[method-assign]
    at = _run_page("Audit", "pages/audit.py", client=fake_client)
    _button(at, "Verify audit chain").click()
    at.run()
    assert not at.exception
    assert any(item.value == "Chain intact — 12 entries across all cases" for item in at.success)


def test_p8_audit_verify_count_from_health(fake_client: FakeArbiterClient) -> None:
    fake_client.health = lambda: {"audit_chain_length": 7, "mode": {}}  # type: ignore[method-assign]
    fake_client.audit_verify = lambda: {"ok": True, "first_bad_seq": None}  # type: ignore[method-assign]
    at = _run_page("Audit", "pages/audit.py", client=fake_client)
    _button(at, "Verify audit chain").click()
    at.run()
    assert not at.exception
    assert any(item.value == "Chain intact — 7 entries across all cases" for item in at.success)


def test_p8_audit_verify_degrades_when_health_fails(fake_client: FakeArbiterClient) -> None:
    def health() -> dict[str, object]:
        raise ArbiterAPIError("down")

    fake_client.health = health  # type: ignore[method-assign]
    fake_client.audit_verify = lambda: {"ok": True, "first_bad_seq": None}  # type: ignore[method-assign]
    at = _run_page("Audit", "pages/audit.py", client=fake_client)
    _button(at, "Verify audit chain").click()
    at.run()
    assert not at.exception
    assert any(item.value == "Chain intact" for item in at.success)
    assert all("entries" not in item.value for item in at.success)
