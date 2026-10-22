"""Data-quality invalid keys (DuckDB sample path; Zetaris in P1-B)."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

from app.data.backend import DataBackend

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RULES = ROOT / "zetaris" / "dq_rules.yaml"


class DqRule(BaseModel):
    id: str
    table: str
    expr: str
    pk: str


def load_dq_rules(path: Path | None = None) -> list[DqRule]:
    p = path or DEFAULT_RULES
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return [DqRule.model_validate(r) for r in raw.get("rules", [])]


def invalid_keys(
    backend: DataBackend,
    table: str,
    *,
    vendor_id: str | None = None,
    rules: list[DqRule] | None = None,
) -> set[str]:
    """Return primary keys failing DQ on table (optionally scoped to vendor)."""
    rule_list = rules or load_dq_rules()
    keys: set[str] = set()
    for rule in rule_list:
        if rule.table != table:
            continue
        sql = f"SELECT {rule.pk} AS pk FROM {table} WHERE NOT COALESCE(({rule.expr}), FALSE)"
        vendor_scoped = (
            "contract",
            "vendor",
            "submission",
            "submission_answer",
            "submission_document",
            "vendor_component",
        )
        if vendor_id and table in vendor_scoped:
            if table == "contract":
                sql += (
                    " AND supplier_ref IN (SELECT clm_supplier_ref FROM vendor "
                    f"WHERE vendor_id = '{vendor_id}')"
                )
            else:
                sql += f" AND vendor_id = '{vendor_id}'"
        rows = backend.execute_sql(sql)
        keys.update(str(r["pk"]) for r in rows)
    return keys
