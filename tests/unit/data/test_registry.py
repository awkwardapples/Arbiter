"""Registry tests P1-T6, P1-T11."""

from __future__ import annotations

import pytest

from app.data.registry import assert_ansi_subset, load_registry, render, validate_params
from app.errors import ValidationFailed


@pytest.mark.p1a
def test_p1_t6_param_validation_and_render() -> None:
    """P1-T6: reject injection, long lists, bad dates; escape quotes."""
    with pytest.raises(ValidationFailed):
        validate_params("Q_VENDOR_PROFILE", {"vendor_id": "VND-0001' OR '1'='1"})
    with pytest.raises(ValidationFailed):
        validate_params("Q_INCIDENTS_BY_NAME", {"names": ["a"] * 21, "since": "2024-01-01"})
    with pytest.raises(ValidationFailed):
        validate_params("Q_VENDOR_INCIDENTS", {"vendor_id": "VND-0001", "since": "not-a-date"})
    sql = render(
        "Q_INCIDENTS_BY_NAME",
        {"names": ["o'brien ltd"], "since": "2024-01-01"},
        backend="duckdb",
    )
    assert "o''brien ltd" in sql
    assert re_unescaped_quote(sql) is False


def re_unescaped_quote(sql: str) -> bool:
    in_str = False
    i = 0
    while i < len(sql):
        if sql[i] == "'":
            if in_str and i + 1 < len(sql) and sql[i + 1] == "'":
                i += 2
                continue
            in_str = not in_str
        i += 1
    return in_str


@pytest.mark.p1a
def test_p1_t11_ansi_subset() -> None:
    """P1-T11: registry SQL uses allowed ANSI subset."""
    for _qid, qdef in load_registry().items():
        if qdef.sql:
            assert_ansi_subset(qdef.sql)
