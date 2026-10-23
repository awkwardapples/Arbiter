"""P13-T7: Q_VENDOR_360 on the DuckDB mirror."""

from __future__ import annotations

import pytest

from app.data.duckdb_backend import DuckDBBackend, reset_cache

COLUMNS = [
    "vendor_id",
    "contract_status",
    "dpa_signed",
    "hosting_region_clause",
    "breach_notification_hours",
    "patch_sla_critical_days",
    "component_count",
    "kev_cve_count",
    "latest_kev_date",
]


@pytest.mark.p13
def test_p13_t7_vendor_360_matches_component_kev() -> None:
    """P13-T7: one row per vendor; component and KEV counts match the existing queries."""
    reset_cache()
    db = DuckDBBackend()
    for n in range(1, 33):
        vendor_id = f"VND-{n:04d}"
        result = db.run("Q_VENDOR_360", {"vendor_id": vendor_id})
        assert result.columns == COLUMNS
        assert len(result.rows) == 1
        row = result.rows[0]
        components = db.run("Q_VENDOR_COMPONENTS", {"vendor_id": vendor_id})
        kev = db.run("Q_COMPONENT_KEV", {"vendor_id": vendor_id})
        cves = [r["cve_id"] for r in kev.rows]
        dates = [r["date_added"] for r in kev.rows if r.get("date_added") is not None]
        assert row["component_count"] == len(components.rows)
        assert row["kev_cve_count"] == len(set(cves))
        assert row["latest_kev_date"] == (max(dates) if dates else None)
