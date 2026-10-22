"""Data layer health (table counts; Zetaris delegated when present)."""

from __future__ import annotations

import importlib

from app.config import Settings, get_settings
from app.data.duckdb_backend import SYSTEMS_DIR, DuckDBBackend


def check(settings: Settings | None = None) -> dict[str, object]:
    settings = settings or get_settings()
    backend = DuckDBBackend()
    tables = [
        "vendor",
        "vendor_alias",
        "contract",
        "incident",
        "watchlist_entry",
        "submission",
        "submission_answer",
        "submission_document",
        "vendor_component",
        "kev_vuln",
    ]
    counts: dict[str, int] = {}
    for table in tables:
        rows = backend.execute_sql(f"SELECT COUNT(*) AS c FROM {table}")
        counts[table] = int(rows[0]["c"]) if rows else 0
    out: dict[str, object] = {
        "backend": "duckdb",
        "sample_dir": str(SYSTEMS_DIR),
        "table_counts": counts,
    }
    try:
        mod = importlib.import_module("app.data.zetaris")
        if hasattr(mod, "status"):
            out["zetaris"] = mod.status(settings)
    except Exception as exc:  # noqa: BLE001 — status probe only
        out["zetaris"] = {"error": type(exc).__name__}
    return out
