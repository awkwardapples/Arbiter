"""P11 professional reviewer console: layout, copy, and the audit event route."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tests.unit.ui.conftest import FakeArbiterClient
from tests.unit.ui.test_pages_smoke import PAGES, _run_page

pytestmark = pytest.mark.p5a

_UI = Path(__file__).resolve().parents[3] / "ui"
_BANNED_PHRASES = ("how to use", "how to read", "try this", "you can", "this page does")
_WIDGETS = {
    "selectbox",
    "text_area",
    "multiselect",
    "text_input",
    "checkbox",
    "button",
    "success",
    "warning",
}
_REVIEW_FLOW = (
    ("selectbox", "Case"),
    ("success", ""),
    ("selectbox", "Decision"),
    ("text_area", "Rationale"),
    ("multiselect", "Mitigations"),
    ("multiselect", "Conditions"),
    ("text_input", "Other condition"),
    ("checkbox", "Create precedent"),
    ("button", "Submit"),
    ("button", "Dry-run"),
)
_CASE_SECTIONS = (
    "Controls",
    "Timeline",
    "Contradictions",
    "Counterfactuals",
    "Precedents considered",
    "Actions",
    "Trace and raw data",
)
_TITLES = {
    "pages/new_assessment.py": "New assessment",
    "pages/queue.py": "Cases",
    "pages/review.py": "Review",
    "pages/memory.py": "Precedents",
    "pages/audit.py": "Audit",
    "pages/evaluation.py": "Evaluation",
}


def _text(elements) -> str:
    return " ".join(getattr(item, "value", "") or "" for item in elements)


def _flow(at) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for node in at:
        kind = getattr(node, "type", None)
        if kind not in _WIDGETS:
            continue
        label = str(getattr(node, "label", "") or "")
        found.append((str(kind), label))
    return found


def _disabled(widget: object) -> bool:
    proto = getattr(widget, "proto", None)
    return bool(getattr(proto, "disabled", False))


def test_p11_no_tutorial_expanders(fake_client: FakeArbiterClient) -> None:
    for title, page in PAGES:
        at = _run_page(title, page, client=fake_client)
        assert not at.exception
        labels = [item.label for item in at.expander]
        assert not any("How to" in label for label in labels)
    for path in _UI.rglob("*.py"):
        lowered = path.read_text(encoding="utf-8").lower()
        for phrase in _BANNED_PHRASES:
            assert phrase not in lowered, f"{path.name} contains {phrase!r}"


def test_p11_pages_are_title_then_caption(fake_client: FakeArbiterClient) -> None:
    for title, page in PAGES:
        if page == "pages/case.py":
            continue
        at = _run_page(title, page, client=fake_client)
        assert not at.exception
        assert at.title[0].value == _TITLES[page]
        assert _text(at.caption).strip()
    case = _run_page("Case", "pages/case.py", client=fake_client)
    assert not case.exception
    detail = fake_client.case_detail
    assert case.title[0].value == f"{detail['case_id']} · {detail['vendor']}"
    record = detail["record"]
    assert f"{record['run_id']} · {record['created_at']}" in _text(case.caption)


def test_p11_review_order_and_autofill(fake_client: FakeArbiterClient) -> None:
    green = _run_page("Review", "pages/review.py", client=fake_client)
    assert not green.exception
    assert not any(item.label == "Check eligibility" for item in green.button)
    flow = _flow(green)
    cursor = 0
    for kind, label in _REVIEW_FLOW:
        matches = [
            index
            for index, item in enumerate(flow)
            if item[0] == kind and (label == "" or item[1].startswith(label)) and index >= cursor
        ]
        assert matches, f"missing {kind} {label!r} after position {cursor} in {flow}"
        cursor = matches[0] + 1
    mitigations = next(item for item in green.multiselect if item.label.startswith("Mitigations"))
    assert "assurance.bridge_letter_current" in mitigations.value
    assert "Available when the case is eligible." not in _text(green.caption)

    def ineligible(case_id: str, body: object, *, dry_run: bool = False) -> dict[str, object]:
        del case_id, body
        assert dry_run
        return {"eligible": False, "reasons": ["mitigation_not_true"]}

    fake_client.submit_review = ineligible  # type: ignore[method-assign]
    amber = _run_page("Review", "pages/review.py", client=fake_client)
    assert not amber.exception
    assert "Not eligible for precedent." in _text(amber.warning)
    assert "Available when the case is eligible." in _text(amber.caption)
    assert any(item.label == "Why not eligible?" for item in amber.expander)
    assert "mitigation_not_true" in _text(amber.markdown)
    for label in ("Mitigations", "Conditions", "Other condition"):
        widget = next(
            item for item in [*amber.multiselect, *amber.text_input] if str(item.label).startswith(label)
        )
        assert _disabled(widget)
    precedent = next(item for item in amber.checkbox if item.label == "Create precedent")
    assert _disabled(precedent)


def test_p11_review_conditions_join() -> None:
    from ui.components import review_conditions

    assert review_conditions(
        ["SOC 2 Type II report within 60 days", "SOC 2 Type II report within 60 days"],
        "  bridge letter on file  ",
    ) == [
        "SOC 2 Type II report within 60 days",
        "bridge letter on file",
    ]
    assert review_conditions(["ISO 27001 certificate within 90 days"], "   ") == [
        "ISO 27001 certificate within 90 days"
    ]


def test_p11_review_success_survives_when_case_leaves(fake_client: FakeArbiterClient) -> None:
    state = {"gone": False}
    original = list(fake_client.queue)

    def list_cases() -> list[dict[str, object]]:
        return [] if state["gone"] else original

    def submit_review(case_id: str, body: object, *, dry_run: bool = False) -> dict[str, object]:
        del case_id, body
        if dry_run:
            return {"eligible": True, "reasons": []}
        state["gone"] = True
        return {
            "review_id": "rev-1",
            "precedent": {"precedent_id": "P-NEW", "control_id": "C05"},
        }

    fake_client.list_cases = list_cases  # type: ignore[method-assign]
    fake_client.submit_review = submit_review  # type: ignore[method-assign]
    at = _run_page("Review", "pages/review.py", client=fake_client)
    next(item for item in at.text_area if item.label.startswith("Rationale")).set_value("x" * 30)
    at.run()
    next(item for item in at.button if item.label == "Submit").click()
    at.run()
    assert not at.exception
    at.run()
    assert not at.exception
    assert any("Review recorded for CASE-0007." in item.value for item in at.success)
    exported = " ".join(frame.value.to_csv(index=False) for frame in at.dataframe)
    assert "P-NEW" in exported


def test_p11_case_section_order(fake_client: FakeArbiterClient) -> None:
    at = _run_page("Case", "pages/case.py", client=fake_client)
    assert not at.exception
    headings = [item.value for item in at.subheader]
    positions = [headings.index(name) for name in _CASE_SECTIONS]
    assert positions == sorted(positions)
    assert not any(item.label == "How to read this" for item in at.expander)


def test_p11_evaluation_split(fake_client: FakeArbiterClient) -> None:
    at = _run_page("Evaluation", "pages/evaluation.py", client=fake_client)
    assert not at.exception
    headings = [item.value for item in at.subheader]
    assert headings.index("Offline benchmark") < headings.index("Live runs on this instance")
    assert "Synthetic data" in _text(at.markdown)
    metrics = {item.label: item.value for item in at.metric}
    assert metrics["Cases"] == "1"
    assert metrics["Data backend"] == "duckdb"
    assert metrics["LLM provider"] == "offline"


def test_p11_live_run_summary() -> None:
    from ui.components import live_run_summary

    empty = live_run_summary([], {})
    assert empty["n"] == "0"
    assert empty["latest"] == "—"
    assert empty["data_backend"] == "unknown"
    assert empty["llm_provider"] == "unknown"
    resolved = live_run_summary(
        [{"created": "2026-10-01T00:00:00Z"}, {"created": "2026-10-02T00:00:00Z"}],
        {
            "mode": {"data": "zetaris", "llm": "auto"},
            "provider": {"provider": "offline", "provider_resolved": "meterless"},
            "data": {"backend": "duckdb"},
        },
    )
    assert resolved == {
        "n": "2",
        "latest": "2026-10-02T00:00:00Z",
        "data_backend": "zetaris",
        "llm_provider": "meterless",
    }


def test_p11_audit_events_and_replay_selector(fake_client: FakeArbiterClient) -> None:
    def audit_recent(limit: int = 20) -> list[dict[str, object]]:
        del limit
        return [
            {
                "seq": 4,
                "timestamp": "2026-10-23T00:00:00Z",
                "case_id": "CASE-0007",
                "event_type": "review_recorded",
            }
        ]

    fake_client.audit_recent = audit_recent  # type: ignore[method-assign]
    at = _run_page("Audit", "pages/audit.py", client=fake_client)
    assert not at.exception
    exported = " ".join(frame.value.to_csv(index=False) for frame in at.dataframe)
    assert "review_recorded" in exported
    assert any(item.label == "Replay" for item in at.button)
    assert not any(str(item.label).startswith("Replay CASE-") for item in at.button)


def test_p11_audit_recent_returns_rows_without_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.api.routes_meta as meta

    db = tmp_path / "audit.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            """
            CREATE TABLE audit_log (
                seq INTEGER PRIMARY KEY,
                ts TEXT NOT NULL,
                case_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                hash TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO audit_log VALUES (1, ?, ?, ?, ?, ?, ?)",
            ("2026-10-23T00:00:00Z", "CASE-1", "review_recorded", '{"secret":"x"}', "", "abc"),
        )
    monkeypatch.setattr(meta, "_AUDIT_DB", db)
    rows = meta.audit_recent()
    assert len(rows) == 1
    dumped = rows[0].model_dump()
    assert set(dumped) == {"seq", "timestamp", "case_id", "event_type"}
    assert dumped["timestamp"] == "2026-10-23T00:00:00Z"
    assert dumped["event_type"] == "review_recorded"
    assert "secret" not in str(dumped)
    monkeypatch.setattr(meta, "_AUDIT_DB", tmp_path / "missing.db")
    assert meta.audit_recent() == []


def test_p11_ui_sources_name_no_vendor() -> None:
    for path in _UI.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in ("VND-", "Marrowgate", "Tessellate", "Try this"):
            assert token not in text, f"{path.name} contains {token!r}"
    root = _UI.parent
    for rel in ("ui/screens.py", "ui/components.py"):
        text = (root / rel).read_text(encoding="utf-8")
        assert "CASE-" not in text
