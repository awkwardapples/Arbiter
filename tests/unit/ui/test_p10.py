"""P10 reviewer-console copy: generic, and it teaches the concept."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.unit.ui.conftest import FakeArbiterClient
from tests.unit.ui.test_pages_smoke import ROOT, _run_page

pytestmark = pytest.mark.p5a

_BANNED = ("VND-", "CASE-", "Marrowgate", "Tessellate", "Try this")
_REVIEW_EMPTY = (
    "No cases are currently awaiting review. Cases that reach DECLINE will appear here "
    "as pending approvals — the policy engine gates those actions on a human sign-off."
)
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
_ELIGIBLE = (
    "This case is eligible for a C05 precedent. "
    "The criteria that the policy requires for an exception are met."
)
_INELIGIBLE = (
    "This case cannot create a precedent. You can still record a review — "
    "the human decision is stored on the case — but no exception will be saved to memory. "
    "The reasons are below."
)
_OFFLINE_CAPTION = (
    "This is the offline evaluation — the same decision pipeline run without live Nightshift or Zetaris. "
    "The accuracy is measured against the policy engine's expected outcomes on a labelled set. "
    "For the live run, see the demo video or the trace logs."
)


def _text(elements) -> str:
    return " ".join(getattr(item, "value", "") or "" for item in elements)


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
    blob = _text(at.markdown)
    assert "Every assessment reaches a deterministic outcome through the policy engine." in blob
    assert "Any case that satisfies the criteria above will be eligible." in blob
    assert "Eligibility status" in blob
    assert "VND-" not in blob
    assert any(item.value == "About C05 (current independent assurance)" for item in at.subheader)
    assert any(item.label == "Check eligibility" for item in at.button)
    mitigations = next(item for item in at.text_input if item.label.startswith("Mitigations"))
    conditions = next(item for item in at.text_input if item.label.startswith("Conditions"))
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
    before = len(calls)
    next(button for button in at.button if button.label == "Check eligibility").click()
    at.run()
    assert not at.exception
    assert len(calls) >= before + 2
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
    warn = _text(amber.warning)
    assert _INELIGIBLE in warn
    assert "mitigation_not_true" in warn


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
    assert "A precedent is a human exception the system has decided to remember." in blob
    assert "Confidence starts at 0.70" in blob
    assert "Try this" not in visible
    assert "VND-" not in visible
    assert "[object Object]" not in visible
    assert any(item.value == "Precedents considered on a specific case" for item in at.subheader)
    assert "Empty list means the policy considered no precedent for this case." in captions
    assert "create is when the precedent was stored" in captions
    assert f"create · MemoryKeeper · mem-1 · {when}" in blob


def test_p10_audit_replay_captions(fake_client: FakeArbiterClient) -> None:
    mismatch = _run_page("Audit", "pages/audit.py", client=fake_client)

    def replay_mismatch(case_id: str) -> dict[str, object]:
        del case_id
        return {"match": False, "diff": ["policy drifted"], "checks": {"policy_hash": False}}

    fake_client.replay = replay_mismatch  # type: ignore[method-assign]
    next(button for button in mismatch.button if button.label == "Replay CASE-0007").click()
    mismatch.run()
    assert not mismatch.exception
    assert any(item.value == "Mismatch — see diff" for item in mismatch.error)
    assert "A mismatch means the decision as stored does not replay identically" in _text(mismatch.caption)

    matched = _run_page("Audit", "pages/audit.py", client=fake_client)

    def replay_match(case_id: str) -> dict[str, object]:
        del case_id
        return {
            "match": True,
            "diff": [],
            "checks": {"policy_hash": True, "record_hash": True, "contract_signatures": True},
        }

    fake_client.replay = replay_match  # type: ignore[method-assign]
    next(button for button in matched.button if button.label == "Replay CASE-0007").click()
    matched.run()
    assert not matched.exception
    assert any(item.value == "Match — the decision replays identically" for item in matched.success)
    assert "A match means the decision replays identically." in _text(matched.caption)


def test_p10_eval_offline_caption(fake_client: FakeArbiterClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import ui.screens as screens

    summary = ROOT / "eval/results/20261022T080517661769Z/summary.md"
    assert summary.is_file()
    monkeypatch.setattr(screens, "EVAL_SUMMARY_PATH", summary, raising=False)
    fake_client.eval_latest_404 = True
    at = _run_page("Evaluation", "pages/evaluation.py", client=fake_client)
    assert not at.exception
    blob = _text(at.markdown)
    assert "Synthetic data" in blob
    assert "System" in blob
    assert _OFFLINE_CAPTION in _text(at.caption)
