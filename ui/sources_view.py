"""Sources & semantic layer page: the Zetaris USL as committed, plus the parity run (lane P14-B).

Reads two committed artefacts and never contacts Zetaris: data/usl/vendor_risk.model.json
(with table descriptions from zetaris/sql/03_usl.sql) and docs/passes/P1-B_parity.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import streamlit as st

from ui.client import ArbiterAPIError
from ui.session import get_client

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "data" / "usl" / "vendor_risk.model.json"
SQL_PATH = ROOT / "zetaris" / "sql" / "03_usl.sql"
PARITY_PATH = ROOT / "docs" / "passes" / "P1-B_parity.json"
PARITY_LABEL = "as of the P13 parity run (23 Oct 2026)"
MISSING_MESSAGE = (
    "The USL model is not available in this checkout — run `python run.py zetaris parity` to regenerate."
)
_TABLE_DESC = re.compile(r"vendor_risk\.(\w+) SET TABLE DESCRIPTION '([^']*)'")
_TYPE = re.compile(r"[a-z]+(?:\(\d+(?:,\d+)?\))?")


def _data_type(raw: object) -> str:
    match = _TYPE.search(str(raw).strip('"'))
    return match.group(0) if match else str(raw)


def _descriptions() -> dict[str, str]:
    try:
        text = SQL_PATH.read_text(encoding="utf-8")
    except OSError:
        return {}
    return dict(_TABLE_DESC.findall(text))


def load_usl() -> dict[str, Any] | None:
    """The committed model as plain dicts, or None when the file is missing or unreadable."""
    try:
        raw = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict) or not isinstance(raw.get("tables"), list):
        return None
    descriptions = _descriptions()
    tables: list[dict[str, Any]] = []
    for table in raw["tables"]:
        name = str(table["name"])
        columns, primary, foreign = [], [], []
        for column in table.get("columnSpecs", []):
            col = str(column["name"])
            columns.append({"name": col, "type": _data_type(column.get("dataType", ""))})
            if "primaryKey" in column:
                primary.append(col)
            fk = column.get("foreignKey")
            if fk and fk.get("refTable"):
                target = str(fk["refTable"][0]).rsplit(".", 1)[-1]
                foreign.append({"column": col, "target_table": target})
        tables.append(
            {
                "name": name,
                "description": descriptions.get(name, ""),
                "columns": columns,
                "primary_key": primary,
                "foreign_keys": foreign,
            }
        )
    return {"name": str(raw.get("name", "vendor_risk")), "tables": tables}


def usl_dot(model: dict[str, Any]) -> str:
    """Graphviz source: one node per table (primary key listed), one edge per foreign key."""
    lines = [
        "digraph usl {",
        "  rankdir=LR;",
        '  node [shape=box, style="rounded,filled", fillcolor="#eef3fb", fontname="Helvetica"];',
    ]
    for table in model["tables"]:
        keys = "\\n".join(f"key: {col}" for col in table["primary_key"])
        label = f"{table['name']}\\n{keys}" if keys else table["name"]
        lines.append(f'  "{table["name"]}" [label="{label}"];')
    for table in model["tables"]:
        for fk in table["foreign_keys"]:
            lines.append(f'  "{table["name"]}" -> "{fk["target_table"]}" [label="{fk["column"]}"];')
    lines.append("}")
    return "\n".join(lines)


def load_parity() -> dict[str, Any] | None:
    try:
        data = json.loads(PARITY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def data_mode_line(health: dict[str, Any]) -> str:
    data = health.get("data") or {}
    if data.get("backend") == "zetaris":
        layer = (data.get("zetaris") or {}).get("query_layer")
        return "Zetaris unified semantic layer (vendor_risk)" if layer == "usl" else "Zetaris (views)"
    return "DuckDB mirror (sample mode): same query ids and columns as Zetaris"


def _parity_tables(parity: dict[str, Any]) -> None:
    rows = [
        {
            "Table": item["table"],
            "Rows expected": item["expected"],
            "Rows from Zetaris": item["zetaris"],
            "Match": "yes" if item["ok"] else "no",
        }
        for item in parity.get("table_counts", [])
    ]
    st.subheader("Row counts")
    st.caption(f"Row counts {PARITY_LABEL}.")
    st.dataframe(rows, hide_index=True)
    dq = [
        {
            "Table": item["table"],
            "Flagged in DuckDB": ", ".join(item["duckdb"]) or "none",
            "Flagged in Zetaris": ", ".join(item["zetaris"]) or "none",
            "Match": "yes" if item["ok"] else "no",
        }
        for item in parity.get("dq_parity", [])
    ]
    st.subheader(f"Data quality rules ({len(dq)})")
    st.caption(f"Each rule runs in both backends and must flag the same records, {PARITY_LABEL}.")
    st.dataframe(dq, hide_index=True)
    queries = parity.get("query_parity", [])
    passed = sum(1 for item in queries if item.get("ok"))
    verdict = "all green" if parity.get("all_green") else "not all green"
    st.markdown(
        f"**Query parity:** {passed} of {len(queries)} registry queries return identical rows "
        f"(hash-compared) from Zetaris and DuckDB — {verdict}."
    )


def render_sources() -> None:
    st.title("Sources & semantic layer")
    st.caption(
        "Where the evidence comes from: six enterprise systems and the CISA catalogue, one governed model."
    )
    try:
        health = get_client().health()
    except ArbiterAPIError as exc:
        st.error(exc.message)
        return
    st.markdown(f"**Data mode:** {data_mode_line(health)}")
    kev = ((health.get("data") or {}).get("table_counts") or {}).get("kev_vuln")
    if kev is not None:
        st.caption(f"CISA Known Exploited Vulnerabilities snapshot in this API's data mode: {kev} entries.")
    st.subheader("Why a semantic layer")
    st.write(
        "Each system names a vendor differently: a procurement id, a contract supplier reference, "
        "free text in the service desk. The semantic layer states those keys and joins once, with a "
        "description for every table, so agents plan queries against one model instead of six schemas. "
        "Full write-up with measurements: `docs/ZETARIS_USL.md`."
    )
    model = load_usl()
    if model is None:
        st.info(MISSING_MESSAGE)
        return
    st.subheader(f"The model: {len(model['tables'])} tables")
    st.caption("Arrows point from a table to the table it references.")
    st.graphviz_chart(usl_dot(model))
    st.dataframe(
        [
            {
                "Table": t["name"],
                "Key": ", ".join(t["primary_key"]),
                "References": ", ".join(
                    f"{fk['target_table']} (via {fk['column']})" for fk in t["foreign_keys"]
                ),
                "Description": t["description"],
            }
            for t in model["tables"]
        ],
        hide_index=True,
    )
    parity = load_parity()
    if parity is None:
        st.info(MISSING_MESSAGE)
        return
    _parity_tables(parity)
