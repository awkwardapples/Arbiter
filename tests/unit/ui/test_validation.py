"""P5-T14: intake validation without calling /run."""

from __future__ import annotations

import pytest

from tests.unit.ui.conftest import FakeArbiterClient
from ui.validation import parse_case_input

pytestmark = pytest.mark.p5a


def test_p5_t14_invalid_submission_errors() -> None:
    """P5-T14: invalid JSON returns errors and no CaseInput."""
    case, errors = parse_case_input("{not json")
    assert case is None
    assert errors


def test_p5_t14_both_vendor_and_submission_rejected() -> None:
    case, errors = parse_case_input({"vendor_id": "VND-1", "submission": {"legal_name": "x"}})
    assert case is None
    assert errors


def test_p5_t14_valid_vendor_id() -> None:
    case, errors = parse_case_input({"vendor_id": "VND-0007"})
    assert errors == []
    assert case is not None
    assert case.vendor_id == "VND-0007"


def test_p5_t14_run_not_called_on_invalid() -> None:
    client = FakeArbiterClient()

    def attempt_run_after_invalid() -> None:
        case, errors = parse_case_input("")
        if errors:
            return
        client.run(case)

    attempt_run_after_invalid()
    assert client.run_calls == 0
