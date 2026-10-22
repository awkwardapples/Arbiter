"""Query registry: load queries.yaml, validate params, render safe SQL."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from app.errors import ValidationFailed

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QUERIES = ROOT / "app" / "data" / "queries.yaml"

VENDOR_ID_RE = re.compile(r"^VND-\d{4}$")
ALLOWED_SQL_TOKENS = re.compile(
    r"\b(SELECT|FROM|JOIN|INNER|LEFT|RIGHT|ON|WHERE|AND|OR|NOT|IN|LIKE|"
    r"LOWER|TRIM|CONCAT|COALESCE|CAST|AS|IS|NULL|ORDER|BY|ASC|DESC|DISTINCT|LIMIT)\b",
    re.IGNORECASE,
)
FORBIDDEN_SQL = re.compile(
    r"\b(DATE_TRUNC|STRFTIME|JSON|PARSE|REGEXP|ILIKE|GLOB|LIST|STRUCT|"
    r"UNNEST|GENERATE|READ_|WRITE_|ATTACH|PRAGMA|pg_|spark_|hive_)\b",
    re.IGNORECASE,
)


class ParamSpec(BaseModel):
    name: str
    type: Literal["vendor_id", "date", "string", "string_list", "product_list", "question_ids", "doc_types"]
    required: bool = True


class QueryDef(BaseModel):
    id: str
    description: str
    sql: str | None = None
    handler: str | None = None
    params: list[ParamSpec] = Field(default_factory=list)
    columns: list[str]
    systems: list[str] = Field(default_factory=list)
    control_ids: list[str] = Field(default_factory=list)


def load_registry(path: Path | None = None) -> dict[str, QueryDef]:
    p = path or DEFAULT_QUERIES
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    queries = raw.get("queries") or raw
    out: dict[str, QueryDef] = {}
    for qid, body in queries.items():
        if isinstance(body, dict):
            body = {**body, "id": qid}
            out[qid] = QueryDef.model_validate(body)
    return out


def _normalize_name(value: str) -> str:
    cleaned = "".join(ch for ch in value.lower().strip() if ch.isprintable() and ord(ch) >= 32)
    return cleaned[:120]


def _escape_literal(value: str) -> str:
    return value.replace("'", "''")


def _render_date(value: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValidationFailed("date must be ISO YYYY-MM-DD")
    return f"CAST('{value}' AS DATE)"


def validate_params(
    query_id: str,
    params: dict[str, object],
    registry: dict[str, QueryDef] | None = None,
) -> dict[str, object]:
    reg = registry or load_registry()
    if query_id not in reg:
        raise ValidationFailed(f"unknown query_id: {query_id}")
    qdef = reg[query_id]
    out: dict[str, object] = {}
    provided = dict(params)
    for pspec in qdef.params:
        if pspec.name not in provided:
            if pspec.required:
                raise ValidationFailed(f"missing param {pspec.name} for {query_id}")
            continue
        val = provided.pop(pspec.name)
        out[pspec.name] = _validate_one(pspec, val)
    if provided:
        raise ValidationFailed(f"unexpected params for {query_id}: {sorted(provided)}")
    return out


def _validate_one(pspec: ParamSpec, val: object) -> object:
    if pspec.type == "vendor_id":
        if not isinstance(val, str) or not VENDOR_ID_RE.fullmatch(val):
            raise ValidationFailed("vendor_id must match ^VND-\\d{4}$")
        return val
    if pspec.type == "date":
        if not isinstance(val, str):
            raise ValidationFailed("date must be a string")
        _render_date(val)
        return val
    if pspec.type == "string":
        if not isinstance(val, str):
            raise ValidationFailed("string param required")
        return _normalize_name(val)
    if pspec.type in ("string_list", "product_list", "question_ids", "doc_types"):
        if not isinstance(val, list):
            raise ValidationFailed(f"{pspec.type} must be a list")
        if len(val) > 20:
            raise ValidationFailed("list params may have at most 20 items")
        items: list[str] = []
        for item in val:
            if not isinstance(item, str):
                raise ValidationFailed("list items must be strings")
            if pspec.type == "question_ids" and not re.fullmatch(r"Q\d{2}", item):
                raise ValidationFailed("invalid question_id")
            items.append(item if pspec.type == "question_ids" else _normalize_name(item))
        return items
    raise ValidationFailed(f"unsupported param type {pspec.type}")


def table_name(table: str, *, backend: Literal["duckdb", "zetaris"], layer: Literal["usl", "views"]) -> str:
    if backend == "duckdb":
        return table
    if layer == "views":
        return f"arbiter.{table}_v"
    return f"lightning.metastore.arbiter.vendor_risk.{table}"


def render(
    query_id: str,
    params: dict[str, object],
    *,
    backend: Literal["duckdb", "zetaris"] = "duckdb",
    layer: Literal["usl", "views"] = "usl",
    registry: dict[str, QueryDef] | None = None,
) -> str:
    reg = registry or load_registry()
    qdef = reg[query_id]
    if qdef.handler:
        raise ValidationFailed(f"query {query_id} uses handler {qdef.handler}, not SQL")
    if not qdef.sql:
        raise ValidationFailed(f"query {query_id} has no sql")
    validated = validate_params(query_id, params, reg)
    sql = qdef.sql
    for table in (
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
    ):
        sql = sql.replace(f"{{T.{table}}}", table_name(table, backend=backend, layer=layer))
    for key, val in validated.items():
        token = f":{key}"
        if token not in sql:
            continue
        sql = sql.replace(token, _render_value(val))
    if re.search(r":\w+", sql):
        raise ValidationFailed(f"unbound params remain in rendered SQL for {query_id}")
    return sql


def _render_value(val: object) -> str:
    if isinstance(val, str):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", val):
            return _render_date(val)
        return f"'{_escape_literal(val)}'"
    if isinstance(val, list):
        if not val:
            raise ValidationFailed("list params must not be empty")
        parts = [_render_value(v) for v in val]
        return "(" + ", ".join(parts) + ")"
    raise ValidationFailed("unsupported rendered type")


def assert_ansi_subset(sql: str) -> None:
    if FORBIDDEN_SQL.search(sql):
        raise ValidationFailed("SQL uses forbidden backend-specific functions")
    # Allow punctuation and identifiers; ensure no backticks or double-quotes
    if "`" in sql or '"' in sql:
        raise ValidationFailed("SQL must not use backticks or double quotes")


def watchlist_screen(
    aliases: list[str],
    watchlist: list[dict[str, object]],
    *,
    near_threshold: float = 0.92,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Exact and near matches (02 §4 sanctions facts)."""
    exact: list[dict[str, object]] = []
    near: list[dict[str, object]] = []
    norm_aliases = {_normalize_name(a) for a in aliases if a}
    for entry in watchlist:
        name = str(entry.get("entity_name", ""))
        norm_entity = _normalize_name(name)
        if norm_entity in norm_aliases:
            exact.append(entry)
            continue
        for alias in norm_aliases:
            ratio = SequenceMatcher(None, norm_entity, alias).ratio()
            if ratio >= near_threshold and norm_entity != alias:
                near.append({**entry, "matched_alias": alias, "ratio": ratio})
                break
    return exact, near


def normalize_name(value: str) -> str:
    return _normalize_name(value)
