"""Zetaris vs DuckDB parity (01 §8)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.canon import sha256_hex
from app.config import Settings, get_settings
from app.data.duckdb_backend import DuckDBBackend, reset_cache
from app.data.registry import load_registry, validate_params
from app.data.zetaris import ZetarisBackend
from app.tracing import Tracer

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "passes" / "P1-B_parity.json"

SKIP_QUERIES = {"Q_COMPONENT_KEV", "Q_KEV_BY_PRODUCTS"}

SOURCE_TABLES = [
    ("vendor", "procurement_vendors.json"),
    ("vendor_alias", "procurement_vendor_aliases.json"),
    ("contract", "clm_contracts.json"),
    ("incident", "itsm_incidents.json"),
    ("watchlist_entry", "grc_watchlist.json"),
    ("submission", "trust_submissions.json"),
    ("submission_answer", "trust_answers.json"),
    ("submission_document", "trust_documents.json"),
    ("vendor_component", "trust_components.json"),
]

VENDOR_ID_RE = re.compile(r"^VND-\d{4}$")


def _table_count_sql(table: str, layer: str) -> str:
    if layer == "views":
        return f"SELECT COUNT(*) AS c FROM arbiter.{table}_v"
    return f"SELECT COUNT(*) AS c FROM lightning.metastore.arbiter.vendor_risk.{table}"


def _simulator_count(raw_file: str) -> int:
    path = ROOT / "data" / "sample" / "systems" / raw_file
    data = json.loads(path.read_text(encoding="utf-8"))
    return int(data.get("count") or len(data.get("records") or []))


def _canonical_rows(rows: list[dict[str, object]], columns: list[str]) -> str:
    normalized = [{c: row.get(c) for c in columns} for row in rows]
    normalized.sort(key=lambda r: json.dumps(r, sort_keys=True, default=str))
    return sha256_hex(normalized)


def _vendor_ids() -> list[str]:
    path = ROOT / "data" / "sample" / "systems" / "procurement_vendors.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    ids: list[str] = []
    for r in data.get("records") or []:
        vid = str(r.get("vendor_id", ""))
        if VENDOR_ID_RE.match(vid):
            ids.append(vid)
    return ids


def _default_params(qid: str, vendor_id: str) -> dict[str, object]:
    reg = load_registry()
    qdef = reg[qid]
    if not qdef.params:
        return {}
    params: dict[str, object] = {}
    for pspec in qdef.params:
        if pspec.type == "vendor_id":
            params[pspec.name] = vendor_id
        elif pspec.type == "date":
            params[pspec.name] = "2025-01-01"
        elif pspec.type == "string_list":
            params[pspec.name] = ["pellucid forms ltd"]
        elif pspec.type == "product_list":
            params[pspec.name] = ["FortiOS"]
        elif pspec.type == "question_ids":
            params[pspec.name] = ["Q01"]
        elif pspec.type == "doc_types":
            params[pspec.name] = ["soc2_type2_summary"]
        elif pspec.type == "string":
            params[pspec.name] = "test"
    validate_params(qid, params, reg)
    return params


def run_parity(settings: Settings, *, out_path: Path = DEFAULT_OUT) -> dict[str, object]:
    reset_cache()
    duck = DuckDBBackend()
    tracer = Tracer("zetaris-parity", mode=settings.mode(), log_dir=str(ROOT / "logs"))
    zet = ZetarisBackend(settings, load_registry(), tracer)
    layer = settings.ZETARIS_QUERY_LAYER
    report: dict[str, Any] = {
        "query_layer": layer,
        "source_mode": settings.ZETARIS_SOURCE_MODE,
        "table_counts": [],
        "query_parity": [],
        "dq_parity": [],
        "kev_subset": [],
        "all_green": True,
    }

    for table, raw_file in SOURCE_TABLES:
        expected = _simulator_count(raw_file)
        try:
            zrows = zet.execute_sql(_table_count_sql(table, layer))
            zcount = int(zrows[0].get("c") or 0) if zrows else -1
        except Exception as exc:  # noqa: BLE001
            zcount = -1
            report["all_green"] = False
            report["table_counts"].append(
                {"table": table, "expected": expected, "zetaris": zcount, "error": type(exc).__name__}
            )
            continue
        ok = zcount == expected
        if not ok:
            report["all_green"] = False
        report["table_counts"].append({"table": table, "expected": expected, "zetaris": zcount, "ok": ok})

    reg = load_registry()
    for qid, qdef in reg.items():
        if qid in SKIP_QUERIES or qdef.handler:
            continue
        for vendor_id in _vendor_ids():
            params = _default_params(qid, vendor_id)
            try:
                zrows = zet.run(qid, params).rows
                drows = duck.run(qid, params).rows
            except Exception as exc:  # noqa: BLE001
                report["all_green"] = False
                report["query_parity"].append(
                    {"query_id": qid, "vendor_id": vendor_id, "ok": False, "error": type(exc).__name__}
                )
                continue
            zhash = _canonical_rows(zrows, qdef.columns)
            dhash = _canonical_rows(drows, qdef.columns)
            ok = len(zrows) == len(drows) and zhash == dhash
            if not ok:
                report["all_green"] = False
            report["query_parity"].append(
                {
                    "query_id": qid,
                    "vendor_id": vendor_id,
                    "ok": ok,
                    "zetaris_rows": len(zrows),
                    "duckdb_rows": len(drows),
                    "zetaris_hash": zhash,
                    "duckdb_hash": dhash,
                }
            )

    from app.data.dq import invalid_keys, load_dq_rules

    for rule in load_dq_rules():
        try:
            zkeys = zet.dq_invalid(rule.table)
            dkeys = invalid_keys(duck, rule.table)
        except Exception as exc:  # noqa: BLE001
            report["all_green"] = False
            report["dq_parity"].append({"table": rule.table, "ok": False, "error": type(exc).__name__})
            continue
        ok = zkeys == dkeys
        if not ok:
            report["all_green"] = False
        report["dq_parity"].append(
            {"table": rule.table, "ok": ok, "zetaris": sorted(zkeys), "duckdb": sorted(dkeys)}
        )

    kev_path = ROOT / "data" / "kev" / "kev_snapshot.json"
    snapshot = json.loads(kev_path.read_text(encoding="utf-8"))
    catalogue_products = {
        "moveit transfer",
        "fortios",
        "netscaler adc and netscaler gateway",
        "confluence data center and server",
        "endpoint manager mobile (epmm)",
    }
    for vuln in snapshot.get("vulnerabilities") or []:
        product = str(vuln.get("product") or "").lower()
        if not any(p in product for p in catalogue_products):
            continue
        cve = str(vuln.get("cveID") or "")
        esc = cve.replace("'", "''")
        if layer == "views":
            kev_sql = f"SELECT cve_id FROM arbiter.kev_vuln_v WHERE cve_id = '{esc}'"
        else:
            ns = "lightning.metastore.arbiter.vendor_risk.kev_vuln"
            kev_sql = f"SELECT cve_id FROM {ns} WHERE cve_id = '{esc}'"
        live_rows = zet.execute_sql(kev_sql)
        ok = bool(live_rows)
        if not ok:
            report["all_green"] = False
        report["kev_subset"].append({"cve_id": cve, "ok": ok})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    report = run_parity(get_settings())
    green = report.get("all_green")
    print(f"parity all_green={green} (written to docs/passes/P1-B_parity.json)")
    return 0 if green else 1


if __name__ == "__main__":
    raise SystemExit(main())
