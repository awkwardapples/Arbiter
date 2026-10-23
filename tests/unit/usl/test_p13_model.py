"""P13-T4 and P13-T5: the committed USL model and its compact catalogue."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.p13


def test_p13_t4_committed_model_has_keys_and_descriptions() -> None:
    """P13-T4: 10 tables, primary keys, foreign-key targets, and a description on every table."""
    from app.data.usl_model import load_model

    model = load_model()
    assert len(model.tables) == 10
    names = {table.name for table in model.tables}
    assert len(names) == 10
    for table in model.tables:
        assert table.description.strip()
        columns = {col.name for col in table.columns}
        assert table.primary_key
        assert set(table.primary_key) <= columns
        for fk in table.foreign_keys:
            assert fk.target_table in names
            target = next(item for item in model.tables if item.name == fk.target_table)
            target_cols = {col.name for col in target.columns}
            assert set(fk.target_columns) <= target_cols
            assert set(fk.columns) <= columns


def test_p13_t5_catalogue_lists_tables_and_stays_small() -> None:
    """P13-T5: compact catalogue is deterministic, lists every table and FK, and is at most 1,200 tokens."""
    from app.data.usl_model import catalogue_tokens, compact_catalogue, load_model

    model = load_model()
    first = compact_catalogue(model)
    second = compact_catalogue(model)
    assert first == second
    for table in model.tables:
        assert table.name in first
        for fk in table.foreign_keys:
            assert f"fk→{fk.target_table}.{fk.target_columns[0]}" in first
    assert catalogue_tokens(first) <= 1200
