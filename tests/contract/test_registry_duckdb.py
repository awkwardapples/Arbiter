"""P1-T5: registry contract against DuckDB."""

from __future__ import annotations

import pytest

from app.data.duckdb_backend import DuckDBBackend, reset_cache
from app.data.registry import load_registry

VENDORS = [f"VND-{i:04d}" for i in range(1, 33)]


@pytest.fixture
def backend() -> DuckDBBackend:
    reset_cache()
    return DuckDBBackend()


@pytest.mark.p1a
def test_p1_t5_all_queries_all_vendors(backend: DuckDBBackend) -> None:
    """P1-T5: every registry query runs on DuckDB with declared columns."""
    registry = load_registry()
    since = "2024-10-26"
    for qid, qdef in registry.items():
        for vid in VENDORS:
            params: dict[str, object] = {}
            if any(p.name == "vendor_id" for p in qdef.params):
                params["vendor_id"] = vid
            if any(p.name == "since" for p in qdef.params):
                params["since"] = since
            if qid == "Q_KEV_BY_PRODUCTS":
                params["products"] = ["FortiOS"]
            if qid == "Q_INCIDENTS_BY_NAME":
                params["names"] = ["pellucid forms ltd"]
            result = backend.run(qid, params)
            assert result.columns == qdef.columns
            for row in result.rows:
                assert list(row.keys()) == qdef.columns
