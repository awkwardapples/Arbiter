"""P10 reviewer-console copy: generic, and it teaches the concept."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.unit.ui.conftest import FakeArbiterClient
from tests.unit.ui.test_pages_smoke import _run_page

pytestmark = pytest.mark.p5a

_BANNED = ("VND-", "CASE-", "Marrowgate", "Tessellate", "Try this")
_REVIEW_EMPTY = "No cases awaiting review."
_MITIGATION_HELP = (
    "The fact that the policy checks when applying the precedent. Pre-filled when the case is eligible."
)
_CONDITIONS_HELP = (
    "Freeform notes for future reviewers — the renewal deadline, the specific report, "
    "any commitments the vendor has made. Not evaluated by the policy."
)
_PRECEDENT_HELP = (
    "Save this exception to H-MEM. A later case with the same mitigation and conditions "
    "can reuse this decision."
)
_ELIGIBLE = "Eligible for C05 precedent."
_INELIGIBLE = "Not eligible for precedent."


def _text(elements) -> str:
    return " ".join(getattr(item, "value", "") or "" for item in elements)


def test_p10_new_assessment_how_to_use(fake_client: FakeArbiterClient) -> None:
    at = _run_page("New assessment", "pages/new_assessment.py", client=fake_client)
    assert not at.exception
    assert not any("How to" in item.label for item in at.expander)
    assert (
        "Start an assessment on a vendor. The pipeline runs the agent loop and produces a decision record."
        in _text(at.caption)
    )
    assert "VND-" not in _text(at.caption)


def test_p10_ui_sources_name_no_sample_vendor() -> None:
    root = Path(__file__).resolve().parents[3]
    for rel in ("ui/screens.py", "ui/components.py"):
        text = (root / rel).read_text(encoding="utf-8")
        for token in _BANNED:
            assert token not in text, f"{rel} contains {token!r}"


def test_p10_split_eval_summary() -> None:
    from ui.components import split_eval_summary

    head, tail = split_eval_summary("intro\nSynthetic data. Small n. More on this line.\nkept\n")
    assert head == "intro\nSynthetic data. Small n. More on this line.\n"
    assert tail == "kept\n"
    whole, rest = split_eval_summary("no marker here\n")
    assert whole == "no marker here\n"
    assert rest == ""


def test_p10_review_copy_and_tooltips(fake_client: FakeArbiterClient) -> None:
    at = _run_page("Review", "pages/review.py", client=fake_client)
    assert not at.exception
    captions = _text(at.caption)
    assert "Record a reviewer decision on a pending case." in captions
    assert "VND-" not in captions
    assert not any(item.value == "About C05 (current independent assurance)" for item in at.subheader)
    assert not any(item.label == "Check eligibility" for item in at.button)
    mitigations = next(item for item in at.multiselect if item.label.startswith("Mitigations"))
    conditions = next(item for item in at.multiselect if item.label.startswith("Conditions"))
    precedent = next(item for item in at.checkbox if item.label == "Create precedent")
    assert mitigations.help == _MITIGATION_HELP
    assert conditions.help == _CONDITIONS_HELP
    assert precedent.help == _PRECEDENT_HELP


def test_p10_check_eligibility_requests_a_fresh_dry_run(fake_client: FakeArbiterClient) -> None:
    calls: list[bool] = []

    def submit_review(case_id: str, body: object, *, dry_run: bool = False) -> dict[str, object]:
        del case_id, body
        calls.append(dry_run)
        return {"eligible": False, "reasons": ["mitigation_not_true"]}

    fake_client.submit_review = submit_review  # type: ignore[method-assign]
    at = _run_page("Review", "pages/review.py", client=fake_client)
    assert not at.exception
    assert calls and all(calls)
    assert not any(button.label == "Check eligibility" for button in at.button)
    before = len(calls)
    at.run()
    assert not at.exception
    assert len(calls) >= before + 1
    assert all(calls)


def test_p10_review_eligibility_titles(fake_client: FakeArbiterClient) -> None:
    def eligible(case_id: str, body: object, *, dry_run: bool = False) -> dict[str, object]:
        del case_id, body
        assert dry_run
        return {"eligible": True, "reasons": []}

    fake_client.submit_review = eligible  # type: ignore[method-assign]
    green = _run_page("Review", "pages/review.py", client=fake_client)
    assert not green.exception
    assert _ELIGIBLE in _text(green.success)

    def ineligible(case_id: str, body: object, *, dry_run: bool = False) -> dict[str, object]:
        del case_id, body
        assert dry_run
        return {"eligible": False, "reasons": ["mitigation_not_true"]}

    fake_client.submit_review = ineligible  # type: ignore[method-assign]
    amber = _run_page("Review", "pages/review.py", client=fake_client)
    assert not amber.exception
    assert _INELIGIBLE in _text(amber.warning)
    assert "mitigation_not_true" in _text(amber.markdown)


def test_p10_review_empty_names_no_vendor(fake_client: FakeArbiterClient) -> None:
    fake_client.list_cases = lambda: []  # type: ignore[method-assign]
    at = _run_page("Review", "pages/review.py", client=fake_client)
    assert not at.exception
    assert _REVIEW_EMPTY in _text(at.info)
    assert "VND-" not in _text(at.markdown) + _text(at.info)


def test_p10_memory_copy(fake_client: FakeArbiterClient) -> None:
    when = datetime.fromtimestamp(1761116400000 / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    fake_client.precedents = [
        {
            "precedent_id": "P-0001",
            "hmem_id": "mem-1",
            "confidence": 0.7,
            "control_id": "C05",
            "ledger": [
                {
                    "action": "create",
                    "actor": "MemoryKeeper",
                    "memory_id": "mem-1",
                    "timestamp": 1761116400000,
                    "previous_state": {"nested": True},
                }
            ],
        }
    ]
    at = _run_page("Memory", "pages/memory.py", client=fake_client)
    assert not at.exception
    blob = _text(at.markdown)
    captions = _text(at.caption)
    visible = blob + captions
    assert any(item.value == "Precedents" for item in at.title)
    assert "Human exceptions saved to H-MEM." in captions
    assert "Try this" not in visible
    assert "VND-" not in visible
    assert "[object Object]" not in visible
    assert any(item.value == "Precedents considered on a case" for item in at.subheader)
    assert "Select a case to see which precedents the policy retrieved for it." in captions
    assert f"create · MemoryKeeper · mem-1 · {when}" in blob


def test_p10_audit_replay_captions(fake_client: FakeArbiterClient) -> None:
    mismatch = _run_page("Audit", "pages/audit.py", client=fake_client)

    def replay_mismatch(case_id: str) -> dict[str, object]:
        del case_id
        return {"match": False, "diff": ["policy drifted"], "checks": {"policy_hash": False}}

    fake_client.replay = replay_mismatch  # type: ignore[method-assign]
    next(button for button in mismatch.button if button.label == "Replay").click()
    mismatch.run()
    assert not mismatch.exception
    assert any(item.value == "Mismatch — see diff" for item in mismatch.error)
    assert "The decision does not reproduce." in _text(mismatch.caption)

    matched = _run_page("Audit", "pages/audit.py", client=fake_client)

    def replay_match(case_id: str) -> dict[str, object]:
        del case_id
        return {
            "match": True,
            "diff": [],
            "checks": {"policy_hash": True, "record_hash": True, "contract_signatures": True},
        }

    fake_client.replay = replay_match  # type: ignore[method-assign]
    next(button for button in matched.button if button.label == "Replay").click()
    matched.run()
    assert not matched.exception
    assert any(item.value == "Match — the decision replays identically" for item in matched.success)
    assert "The decision reproduces identically from its inputs." in _text(matched.caption)


def test_p10_eval_offline_caption(fake_client: FakeArbiterClient) -> None:
    at = _run_page("Evaluation", "pages/evaluation.py", client=fake_client)
    assert not at.exception
    blob = _text(at.markdown)
    assert "Synthetic data" in blob
    assert "System" in blob
    assert any(item.value == "Offline benchmark" for item in at.subheader)
    assert "docs/EVALUATION.md" in _text(at.caption)
