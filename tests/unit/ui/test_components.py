"""P5-T12: badges and status labels include visible text."""

from __future__ import annotations

import re

import pytest

from ui.components import OUTCOME_LABELS, TRACE_STATUSES, decision_badge, status_label

pytestmark = pytest.mark.p5a

_TEXT = re.compile(r"[A-Za-z]{3,}")


def test_p5_t12_outcome_labels_contain_words() -> None:
    """P5-T12: every outcome label includes alphabetic text."""
    for key, label in OUTCOME_LABELS.items():
        assert _TEXT.search(label), f"outcome {key} label lacks text: {label!r}"
        assert key in label


def test_p5_t12_status_labels_contain_words() -> None:
    """P5-T12: trace status renderers are not icon-only."""
    for status in TRACE_STATUSES:
        rendered = status_label(status)
        assert _TEXT.search(rendered), f"status {status} lacks text: {rendered!r}"


def test_p5_t12_decision_badge_does_not_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    """Smoke: decision_badge accepts every outcome key."""
    import streamlit as st

    monkeypatch.setattr(st, "markdown", lambda *a, **k: None)
    for outcome in OUTCOME_LABELS:
        decision_badge(outcome)
