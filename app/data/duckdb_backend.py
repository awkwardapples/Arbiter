"""In-memory DuckDB mirror of USL tables (sample mode)."""

from __future__ import annotations

import json
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

import duckdb

from app.data.backend import QueryResult
from app.data.dq import invalid_keys, load_dq_rules
from app.data.registry import load_registry, render, validate_params

ROOT = Path(__file__).resolve().parents[2]
SYSTEMS_DIR = ROOT / "data" / "sample" / "systems"
KEV_PATH = ROOT / "data" / "kev" / "kev_snapshot.json"

_BUILD_CACHE: duckdb.DuckDBPyConnection | None = None


def _load_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("records") or [])


def _build_connection(*, systems_dir: Path, kev_path: Path) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(database=":memory:")
    mapping = {
        "vendor": systems_dir / "procurement_vendors.json",
        "vendor_alias": systems_dir / "procurement_vendor_aliases.json",
        "contract": systems_dir / "clm_contracts.json",
        "incident": systems_dir / "itsm_incidents.json",
        "watchlist_entry": systems_dir / "grc_watchlist.json",
        "submission": systems_dir / "trust_submissions.json",
        "submission_answer": systems_dir / "trust_answers.json",
        "submission_document": systems_dir / "trust_documents.json",
        "vendor_component": systems_dir / "trust_components.json",
    }
    for table, path in mapping.items():
        records = _load_records(path)
        if not records:
            con.execute(f"CREATE TABLE {table} AS SELECT * FROM (SELECT 1 AS _empty WHERE 1=0)")
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
            json.dump(records, tf)
            tmp_path = tf.name
        try:
            con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_json_auto(?)", [tmp_path])
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    kev_rows: list[dict[str, Any]] = []
    if kev_path.is_file():
        kev = json.loads(kev_path.read_text(encoding="utf-8"))
        for v in kev.get("vulnerabilities") or []:
            kev_rows.append(
                {
                    "cve_id": v.get("cveID") or v.get("cve_id"),
                    "vendor_project": v.get("vendorProject") or v.get("vendor_project"),
                    "product": v.get("product"),
                    "vulnerability_name": v.get("vulnerabilityName") or v.get("vulnerability_name"),
                    "date_added": v.get("dateAdded") or v.get("date_added"),
                    "due_date": v.get("dueDate") or v.get("due_date"),
                    "ransomware_use": v.get("knownRansomwareCampaignUse") or v.get("ransomware_use"),
                }
            )
    if kev_rows:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
            json.dump(kev_rows, tf)
            kev_tmp = tf.name
        try:
            con.execute("CREATE TABLE kev_vuln AS SELECT * FROM read_json_auto(?)", [kev_tmp])
        finally:
            Path(kev_tmp).unlink(missing_ok=True)
    else:
        con.execute(
            "CREATE TABLE kev_vuln (cve_id VARCHAR, vendor_project VARCHAR, product VARCHAR, "
            "vulnerability_name VARCHAR, date_added DATE, due_date DATE, ransomware_use VARCHAR)"
        )
    return con


def get_connection(
    *, systems_dir: Path | None = None, kev_path: Path | None = None
) -> duckdb.DuckDBPyConnection:
    global _BUILD_CACHE
    if _BUILD_CACHE is None:
        _BUILD_CACHE = _build_connection(
            systems_dir=systems_dir or SYSTEMS_DIR,
            kev_path=kev_path or KEV_PATH,
        )
    return _BUILD_CACHE


def reset_cache() -> None:
    global _BUILD_CACHE
    _BUILD_CACHE = None


class DuckDBBackend:
    name = "duckdb"

    def __init__(self, *, systems_dir: Path | None = None, kev_path: Path | None = None) -> None:
        self._systems_dir = systems_dir or SYSTEMS_DIR
        self._kev_path = kev_path or KEV_PATH
        self._con = get_connection(systems_dir=self._systems_dir, kev_path=self._kev_path)

    def execute_sql(self, sql: str) -> list[dict[str, object]]:
        cur = self._con.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]

    def run(self, query_id: str, params: dict[str, object]) -> QueryResult:
        t0 = time.perf_counter()
        registry = load_registry()
        qdef = registry[query_id]
        if qdef.handler == "dq_invalid":
            validated = validate_params(query_id, params, registry)
            rows = self._dq_invalid(str(validated["vendor_id"]))
        else:
            sql = render(query_id, params, backend="duckdb", registry=registry)
            if query_id == "Q_KEV_BY_PRODUCTS":
                sql = self._kev_by_products_sql(params, registry)
            rows = self.execute_sql(sql)
        latency = int((time.perf_counter() - t0) * 1000)
        columns = qdef.columns
        normalized = [{c: row.get(c) for c in columns} for row in rows]
        return QueryResult(
            query_id=query_id,
            rows=normalized,
            columns=columns,
            backend="duckdb",
            request_id=uuid.uuid4().hex,
            latency_ms=latency,
        )

    def _kev_by_products_sql(self, params: dict[str, object], registry: dict) -> str:
        validated = validate_params("Q_KEV_BY_PRODUCTS", params, registry)
        products = validated["products"]
        if not isinstance(products, list):
            products = []
        clauses = [
            f"lower(product) LIKE concat('%', '{str(p).lower().replace(chr(39), chr(39) + chr(39))}', '%')"
            for p in products
        ]
        where = " OR ".join(clauses) if clauses else "1=0"
        cols = "cve_id, vendor_project, product, vulnerability_name, date_added, due_date, ransomware_use"
        return f"SELECT {cols} FROM kev_vuln WHERE {where} ORDER BY cve_id"

    def _dq_invalid(self, vendor_id: str) -> list[dict[str, object]]:
        out: list[dict[str, object]] = []
        rules = load_dq_rules()
        for rule in rules:
            keys = invalid_keys(self, rule.table, vendor_id=vendor_id, rules=[rule])
            for key in sorted(keys):
                out.append({"rule_id": rule.id, "table_name": rule.table, "record_key": key})
        return out
