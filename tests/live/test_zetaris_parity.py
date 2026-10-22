"""Live Zetaris parity tests (P1-T25..P1-T28)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.config import get_settings
from app.data.duckdb_backend import DuckDBBackend, reset_cache
from app.data.registry import load_registry
from app.data.zetaris import ZetarisBackend
from app.tracing import Tracer
from zetaris.parity import (
    SKIP_QUERIES,
    SOURCE_TABLES,
    _canonical_rows,
    _default_params,
    _simulator_count,
    _table_count_sql,
    _vendor_ids,
)

ROOT = Path(__file__).resolve().parents[2]
pytestmark = [pytest.mark.p1b, pytest.mark.live]


@pytest.fixture(scope="module")
def live_backend() -> ZetarisBackend:
    if os.environ.get("ARBITER_LIVE_TESTS") != "1":
        pytest.skip("ARBITER_LIVE_TESTS=1 required")
    settings = get_settings()
    if settings.ZETARIS_API_KEY is None:
        pytest.skip("ZETARIS_API_KEY not configured")
    tracer = Tracer("live-p1b", mode=settings.mode(), log_dir=str(ROOT / "logs"))
    return ZetarisBackend(settings, load_registry(), tracer)


@pytest.mark.p1b
@pytest.mark.live
def test_p1_t25_table_counts(live_backend: ZetarisBackend) -> None:
    """P1-T25: USL/view counts match simulator envelopes."""
    settings = get_settings()
    layer = settings.ZETARIS_QUERY_LAYER
    for table, raw_file in SOURCE_TABLES:
        expected = _simulator_count(raw_file)
        rows = live_backend.execute_sql(_table_count_sql(table, layer))
        assert int(rows[0]["c"]) == expected


@pytest.mark.p1b
@pytest.mark.live
def test_p1_t26_query_parity(live_backend: ZetarisBackend) -> None:
    """P1-T26: registry queries match DuckDB rows and hashes."""
    reset_cache()
    duck = DuckDBBackend()
    reg = load_registry()
    for qid, qdef in reg.items():
        if qid in SKIP_QUERIES or qdef.handler:
            continue
        for vendor_id in _vendor_ids()[:5]:
            params = _default_params(qid, vendor_id)
            zrows = live_backend.run(qid, params).rows
            drows = duck.run(qid, params).rows
            assert len(zrows) == len(drows)
            assert _canonical_rows(zrows, qdef.columns) == _canonical_rows(drows, qdef.columns)


@pytest.mark.p1b
@pytest.mark.live
def test_p1_t27_dq_parity(live_backend: ZetarisBackend) -> None:
    """P1-T27: DQ invalid key sets match DuckDB."""
    from app.data.dq import invalid_keys, load_dq_rules

    reset_cache()
    duck = DuckDBBackend()
    for rule in load_dq_rules():
        assert live_backend.dq_invalid(rule.table) == invalid_keys(duck, rule.table)


@pytest.mark.p1b
@pytest.mark.live
def test_p1_t28_kev_subset(live_backend: ZetarisBackend) -> None:
    """P1-T28: snapshot catalogue CVEs appear in live KEV."""
    settings = get_settings()
    layer = settings.ZETARIS_QUERY_LAYER
    snapshot = json.loads((ROOT / "data" / "kev" / "kev_snapshot.json").read_text(encoding="utf-8"))
    catalogue_products = {"moveit", "fortios", "netscaler", "confluence", "epmm"}
    checked = 0
    for vuln in snapshot.get("vulnerabilities") or []:
        product = str(vuln.get("product") or "").lower()
        if not any(p in product for p in catalogue_products):
            continue
        cve = str(vuln.get("cveID") or "")
        if layer == "views":
            table = "arbiter.kev_vuln_v"
        else:
            table = "lightning.metastore.arbiter.vendor_risk.kev_vuln"
        rows = live_backend.execute_sql(f"SELECT cve_id FROM {table} WHERE cve_id = '{cve}'")
        assert rows, f"missing {cve}"
        checked += 1
        if checked >= 5:
            break
    assert checked >= 1
