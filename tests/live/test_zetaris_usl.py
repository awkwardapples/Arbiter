"""P13-T8, P13-T9, P13-T10: live USL activation, DQ, and vendor-360 parity."""

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

ROOT = Path(__file__).resolve().parents[2]
pytestmark = [pytest.mark.p13, pytest.mark.live]

NON_KEV = [
    "vendor_id",
    "contract_status",
    "dpa_signed",
    "hosting_region_clause",
    "breach_notification_hours",
    "patch_sla_critical_days",
    "component_count",
]


@pytest.fixture(scope="module")
def live_backend() -> ZetarisBackend:
    if os.environ.get("ARBITER_LIVE_TESTS") != "1":
        pytest.skip("ARBITER_LIVE_TESTS=1 required")
    settings = get_settings()
    if settings.ZETARIS_API_KEY is None:
        pytest.skip("ZETARIS_API_KEY not configured")
    if settings.ZETARIS_QUERY_LAYER != "usl":
        pytest.fail("ZETARIS_QUERY_LAYER must be usl")
    tracer = Tracer("live-p13", mode=settings.mode(), log_dir=str(ROOT / "logs"))
    return ZetarisBackend(settings, load_registry(), tracer)


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].lstrip("-").isdigit():
        return text[:-2]
    return text[:10] if len(text) >= 10 and text[4:5] == "-" else text


def _kestrel_contract_id() -> str:
    vendors = json.loads((ROOT / "data/sample/systems/procurement_vendors.json").read_text(encoding="utf-8"))
    contracts = json.loads((ROOT / "data/sample/systems/clm_contracts.json").read_text(encoding="utf-8"))
    vendor = next(row for row in vendors["records"] if row["vendor_id"] == "VND-0028")
    contract = next(row for row in contracts["records"] if row["supplier_ref"] == vendor["clm_supplier_ref"])
    return str(contract["contract_id"])


def test_p13_t8_ten_tables_activated(live_backend: ZetarisBackend) -> None:
    """P13-T8: vendor_risk lists 10 activated tables and source counts match."""
    rows = live_backend.execute_sql("SHOW NAMESPACES OR TABLES IN lightning.metastore.arbiter.vendor_risk")
    activated = [row for row in rows if str(row.get("activated")).lower() in {"true", "1"}]
    assert len(activated) == 10
    expected = {
        "vendor": 32,
        "vendor_alias": 64,
        "contract": 32,
        "incident": 2,
        "watchlist_entry": 2,
        "submission": 32,
        "submission_answer": 504,
        "submission_document": 9,
        "vendor_component": 2,
    }
    for table, count in expected.items():
        got = live_backend.execute_sql(
            f"SELECT COUNT(*) AS c FROM lightning.metastore.arbiter.vendor_risk.{table}"
        )
        assert int(got[0]["c"]) == count
    live = live_backend.execute_sql(
        "SELECT COUNT(*) AS c FROM lightning.metastore.arbiter.vendor_risk.kev_vuln"
    )
    snapshot = json.loads((ROOT / "data/kev/kev_snapshot.json").read_text(encoding="utf-8"))
    assert int(live[0]["c"]) >= int(snapshot["count"])


def test_p13_t9_dq_catches_kestrel_contract(live_backend: ZetarisBackend) -> None:
    """P13-T9: contract DQ invalid set includes VND-0028's contract."""
    contract_id = _kestrel_contract_id()
    rows = live_backend.execute_sql(
        "SHOW DQ ALL INVALID TABLE lightning.metastore.arbiter.vendor_risk.contract"
    )
    blob = json.dumps(rows, default=str)
    assert contract_id in blob


def test_p13_t10_vendor_360_superset_parity(live_backend: ZetarisBackend) -> None:
    """P13-T10: non-KEV columns match; live KEV count and date are at least the snapshot."""
    reset_cache()
    duck = DuckDBBackend()
    for n in range(1, 33):
        vendor_id = f"VND-{n:04d}"
        params = {"vendor_id": vendor_id}
        live = live_backend.run("Q_VENDOR_360", params).rows
        sample = duck.run("Q_VENDOR_360", params).rows
        assert len(live) == 1 and len(sample) == 1
        for column in NON_KEV:
            assert _cell(live[0][column]) == _cell(sample[0][column])
        assert int(live[0]["kev_cve_count"]) >= int(sample[0]["kev_cve_count"])
        live_date = _cell(live[0]["latest_kev_date"])
        sample_date = _cell(sample[0]["latest_kev_date"])
        if sample_date:
            assert live_date >= sample_date
