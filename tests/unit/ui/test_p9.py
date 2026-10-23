"""P9 reviewer-console explainability."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.unit.ui.conftest import FakeArbiterClient
from tests.unit.ui.test_pages_smoke import ROOT, _run_page

pytestmark = pytest.mark.p5a

SUMMARY = ROOT / "eval/results/20261022T080517661769Z/summary.md"
_DASH = "—"


def _text(elements) -> str:
    return " ".join(getattr(item, "value", "") or "" for item in elements)


def _payloads(at) -> list[object]:
    found: list[object] = []
    for block in at.code:
        try:
            found.append(json.loads(block.value))
        except json.JSONDecodeError:
            continue
    return found


def _see_raw_collapsed(at) -> None:
    expanders = [item for item in at.expander if item.label == "See raw"]
    assert expanders, "expected at least one See raw expander"
    assert all(item.proto.expanded is False for item in expanders)


def _list_has(payloads: list[object], key: str, value: object) -> bool:
    for payload in payloads:
        rows = payload if isinstance(payload, list) else []
        if any(isinstance(row, dict) and row.get(key) == value for row in rows):
            return True
    return False


def test_p9_humanised_bullet_puts_the_code_first() -> None:
    from ui.components import humanise_outcome_reason, humanised_bullet

    assert humanised_bullet("CONTRADICTION", humanise_outcome_reason("CONTRADICTION")) == (
        f"**CONTRADICTION** {_DASH} Contradiction on a system-of-record claim"
    )


def test_p9_formatters_for_case_sections() -> None:
    from ui.components import contradiction_rows, counterfactual_line, precedent_rows, signature_short

    rows = contradiction_rows([{"key": "incidents.vendor_reported_24m", "claim_value": 0, "sor_value": None}])
    assert rows == [
        {"Claim": "incidents.vendor_reported_24m: 0", "System of record": "null"},
    ]
    line = counterfactual_line(
        {
            "control_id": "C01",
            "evidence_required": [
                "Q01 and Q02 affirmative, naming the mechanism",
                "or assurance report noting the MFA control without exception",
            ],
            "question_ids": ["Q01", "Q02"],
        }
    )
    assert line.startswith(f"**C01** {_DASH}")
    assert "Q01, Q02" in line
    considered = [{"precedent_id": "P-0001", "hmem_confidence": 0.7, "applied": True}]
    table = precedent_rows(
        considered,
        candidates=[{"precedent_id": "P-0001", "created_as_of": "2026-10-10"}],
        as_of="2026-10-22",
    )
    assert table == [
        {"precedent_id": "P-0001", "confidence": "0.70", "age": "12 days", "applied": "true"},
    ]
    missing = precedent_rows(
        [{"precedent_id": "P-0002", "hmem_confidence": 0.5, "applied": False}],
        candidates=[],
        as_of="2026-10-22",
    )
    assert missing[0]["age"] == _DASH
    assert missing[0]["applied"] == "false"
    assert signature_short("abcdefghijklmnopQRST") == "abcdefgh…QRST"


def test_p9_ledger_line_is_text() -> None:
    from ui.components import ledger_line

    line = ledger_line(
        {
            "action": "create",
            "actor": "MemoryKeeper",
            "memory_id": "mem-1",
            "timestamp": 1761116400000,
            "previous_state": {"a": 1},
        }
    )
    assert "create" in line
    assert "MemoryKeeper" in line
    assert "mem-1" in line
    assert "[object Object]" not in line
    assert "previous_state" not in line


def test_p9_eval_renders_summary_when_present(
    fake_client: FakeArbiterClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ui.screens as screens

    assert SUMMARY.is_file()
    monkeypatch.setattr(screens, "EVAL_SUMMARY_PATH", SUMMARY, raising=False)
    fake_client.eval_latest_404 = True
    at = _run_page("Evaluation", "pages/evaluation.py", client=fake_client)
    assert not at.exception
    assert "Synthetic data" in _text(at.markdown)
    assert "not published yet" not in _text(at.info).lower()
    assert "docs/EVALUATION.md" in _text(at.caption)


def test_p9_eval_fallback_when_summary_missing(
    fake_client: FakeArbiterClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import ui.screens as screens

    monkeypatch.setattr(screens, "EVAL_SUMMARY_PATH", tmp_path / "missing.md", raising=False)
    fake_client.eval_latest_404 = True
    at = _run_page("Evaluation", "pages/evaluation.py", client=fake_client)
    assert not at.exception
    assert "not published yet" in _text(at.info).lower()
    assert "docs/EVALUATION.md" in _text(at.caption)


def test_p9_case_sections_and_see_raw(fake_client: FakeArbiterClient) -> None:
    record = fake_client.case_detail["record"]
    record["contradictions"] = [
        {
            "key": "incidents.vendor_reported_24m",
            "claim_value": 0,
            "sor_value": 2,
            "control_id": "C06",
        }
    ]
    record["precedents_considered"] = [{"precedent_id": "P-9TEST", "hmem_confidence": 0.8, "applied": True}]
    record.setdefault("policy_inputs", {})["precedents"] = [
        {"precedent_id": "P-9TEST", "created_as_of": "2026-10-10"}
    ]
    fake_client.case_detail["contracts"] = [
        {
            "contract_id": "ctr-p9",
            "intent": "vendor.onboarding.escalate",
            "parameters": {"outcome": "ESCALATE"},
            "state": "pending_approval",
            "signature": "abcdefghijklmnopQRSTUVWXYZ",
            "signed_by": "scout",
            "tool_plan": [{"capability": "draft_email", "args": {"to": "ops"}}],
        }
    ]
    at = _run_page("Case", "pages/case.py", client=fake_client)
    assert not at.exception
    _see_raw_collapsed(at)
    assert not list(at.json)
    assert not list(at.checkbox)
    blob = _text(at.markdown)
    assert "Evidence that would change this decision" in blob
    assert f"**C01** {_DASH}" in blob
    assert "ctr-p9" in blob
    assert "vendor.onboarding.escalate" in blob
    assert "ESCALATE" in blob
    assert "pending_approval" in blob
    assert "draft_email" in blob
    assert "abcdefgh…WXYZ" in blob
    frames = [frame.value for frame in at.dataframe]
    claim = next(frame for frame in frames if list(frame.columns) == ["Claim", "System of record"])
    assert "incidents.vendor_reported_24m: 0" in set(claim["Claim"])
    precedents = next(frame for frame in frames if "precedent_id" in frame.columns)
    assert "P-9TEST" in set(precedents["precedent_id"])
    payloads = _payloads(at)
    assert _list_has(payloads, "key", "incidents.vendor_reported_24m")
    assert _list_has(payloads, "contract_id", "ctr-p9")
    assert _list_has(payloads, "precedent_id", "P-9TEST")
    assert _list_has(payloads, "control_id", "C01")
    how = next(item for item in at.expander if item.label == "How to read this")
    assert how.proto.expanded is True
    captions = _text(at.caption)
    assert "A vendor claim and the system-of-record value" in captions
    assert any(item.value == "CASE-0007" for item in at.subheader)


def test_p9_case_precedents_empty_sentence(fake_client: FakeArbiterClient) -> None:
    at = _run_page("Case", "pages/case.py", client=fake_client)
    assert not at.exception
    assert "No precedents were considered for this case." in _text(at.markdown)


def test_p9_audit_replay_and_verify_see_raw(fake_client: FakeArbiterClient) -> None:
    fake_client.replay = lambda case_id: {  # type: ignore[method-assign]
        "match": False,
        "diff": ["replay-sentinel"],
        "checks": {"policy_hash": False},
    }
    fake_client.audit_verify = lambda: {"ok": True, "first_bad_seq": None, "entries": 12}  # type: ignore[method-assign]
    at = _run_page("Audit", "pages/audit.py", client=fake_client)
    at.session_state["nav_case_id"] = "CASE-0007"
    at.run()
    assert "Active case · CASE-0007" in _text(at.markdown)
    next(button for button in at.button if button.label == "Verify audit chain").click()
    at.run()
    assert not at.exception
    _see_raw_collapsed(at)
    assert any(json.loads(block.value).get("entries") == 12 for block in at.code)
    replay = _run_page("Audit", "pages/audit.py", client=fake_client)
    next(button for button in replay.button if button.label == "Replay CASE-0007").click()
    replay.run()
    assert not replay.exception
    _see_raw_collapsed(replay)
    diffs = [payload.get("diff") for payload in _payloads(replay) if isinstance(payload, dict)]
    assert ["replay-sentinel"] in diffs
    assert "CASE-0007" in _text(replay.markdown)
    assert not list(replay.json)


def test_p9_case_id_on_review_and_memory(fake_client: FakeArbiterClient) -> None:
    review = _run_page("Review", "pages/review.py", client=fake_client)
    assert not review.exception
    assert any(item.value == "Selected case · CASE-0007" for item in review.subheader)
    memory = _run_page("Memory", "pages/memory.py", client=fake_client)
    assert not memory.exception
    assert any(item.value == "Selected case · CASE-0007" for item in memory.subheader)


def test_p9_review_intro_and_empty_queue(fake_client: FakeArbiterClient) -> None:
    fake_client.list_cases = lambda: []  # type: ignore[method-assign]
    at = _run_page("Review", "pages/review.py", client=fake_client)
    assert not at.exception
    blob = _text(at.markdown)
    assert "Every assessment reaches a deterministic outcome through the policy engine." in blob
    assert "C05" in blob
    assert "VND-" not in blob
    assert (
        "No cases are currently awaiting review. Cases that reach DECLINE will appear here "
        "as pending approvals — the policy engine gates those actions on a human sign-off." in _text(at.info)
    )


def test_p9_review_amber_when_ineligible(fake_client: FakeArbiterClient) -> None:
    def submit_review(case_id: str, body: object, *, dry_run: bool = False) -> dict[str, object]:
        del case_id, body
        assert dry_run
        return {"eligible": False, "reasons": ["mitigation_not_true"]}

    fake_client.submit_review = submit_review  # type: ignore[method-assign]
    at = _run_page("Review", "pages/review.py", client=fake_client)
    assert not at.exception
    warn = _text(at.warning)
    assert "This case cannot create a precedent." in warn
    assert f"**mitigation_not_true** {_DASH} The mitigation fact is not TRUE" in warn
    assert "No precedent will be created." in warn
    _see_raw_collapsed(at)
    assert any(json.loads(block.value).get("reasons") == ["mitigation_not_true"] for block in at.code)


def test_p9_review_green_when_eligible(fake_client: FakeArbiterClient) -> None:
    calls: list[bool] = []

    def submit_review(case_id: str, body: object, *, dry_run: bool = False) -> dict[str, object]:
        del case_id, body
        calls.append(dry_run)
        return {"eligible": True, "reasons": []}

    fake_client.submit_review = submit_review  # type: ignore[method-assign]
    at = _run_page("Review", "pages/review.py", client=fake_client)
    assert not at.exception
    assert calls and all(calls)
    ok = _text(at.success)
    assert "This case is eligible for a C05 precedent." in ok
    assert f"**C05** {_DASH}" in ok
    assert f"**assurance.bridge_letter_current** {_DASH}" in ok
    assert f"**APPROVE** {_DASH}" in ok
    assert f"**tprm_lead** {_DASH}" in ok
    mitigations = next(item for item in at.text_input if item.label.startswith("Mitigations"))
    assert mitigations.value == "assurance.bridge_letter_current"
    _see_raw_collapsed(at)
    assert any(json.loads(block.value).get("eligible") is True for block in at.code)


def test_p9_memory_ledger_is_lines(fake_client: FakeArbiterClient) -> None:
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
                    "previous_state": {"nested": {"a": 1}},
                }
            ],
        }
    ]
    at = _run_page("Memory", "pages/memory.py", client=fake_client)
    assert not at.exception
    visible = _text(at.markdown) + _text(at.caption)
    assert f"create · MemoryKeeper · mem-1 · {when}" in visible
    assert "[object Object]" not in visible
    assert "previous_state" not in visible
    assert any("previous_state" in block.value for block in at.code)
    _see_raw_collapsed(at)


def test_p9_memory_autoselects_newest_case_with_precedents(fake_client: FakeArbiterClient) -> None:
    fake_client.queue = [
        {"case_id": "CASE-NEW", "created": "2026-10-23T00:00:00+00:00"},
        {"case_id": "CASE-MID", "created": "2026-10-15T00:00:00+00:00"},
        {"case_id": "CASE-OLD", "created": "2026-10-01T00:00:00+00:00"},
    ]
    base = fake_client.case_detail

    def get_case(case_id: str) -> dict[str, object]:
        detail = copy.deepcopy(base)
        detail["case_id"] = case_id
        considered: list[dict[str, object]] = []
        if case_id in {"CASE-MID", "CASE-OLD"}:
            considered = [{"precedent_id": f"P-{case_id}", "hmem_confidence": 0.7, "applied": False}]
        detail["record"]["precedents_considered"] = considered
        return detail

    fake_client.get_case = get_case  # type: ignore[method-assign]
    at = _run_page("Memory", "pages/memory.py", client=fake_client)
    assert not at.exception
    picked = next(item for item in at.selectbox if item.label.startswith("Precedents"))
    assert picked.value == "CASE-MID"
    assert any(item.value == "Selected case · CASE-MID" for item in at.subheader)


def test_p9_queue_and_audit_captions(fake_client: FakeArbiterClient) -> None:
    queue = _run_page("Queue", "pages/queue.py", client=fake_client)
    assert not queue.exception
    assert "Assessed cases. Filter, then open one to see why it was decided." in _text(queue.caption)
    audit = _run_page("Audit", "pages/audit.py", client=fake_client)
    assert not audit.exception
    assert (
        "Replay a case to confirm the same decision. Verify checks the hash chain for every case."
        in _text(audit.caption)
    )
