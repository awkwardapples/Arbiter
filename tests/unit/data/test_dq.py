"""P1-T7 DQ invalid keys."""

from __future__ import annotations

import pytest

from app.data.dq import invalid_keys
from app.data.duckdb_backend import DuckDBBackend, reset_cache


@pytest.mark.p1a
def test_p1_t7_dq_contract_dpa_date() -> None:
    """P1-T7: VND-0028 contract flagged; clean vendors not false-positive."""
    reset_cache()
    backend = DuckDBBackend()
    bad = invalid_keys(backend, "contract", vendor_id="VND-0028")
    assert any("CTR" in k for k in bad)
    clean = invalid_keys(backend, "contract", vendor_id="VND-0003")
    assert not clean
