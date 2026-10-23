"""USL model loaded from the committed vendor_risk JSON."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel, Field

from app.canon import sha256_hex
from app.errors import ConfigError

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = ROOT / "data" / "usl" / "vendor_risk.model.json"
DEFAULT_SQL = ROOT / "zetaris" / "sql" / "03_usl.sql"

_MODEL_DESC = re.compile(r"UPDATE USL lightning\.metastore\.arbiter\.vendor_risk SET DESCRIPTION '([^']*)'")
_TABLE_DESC = re.compile(
    r"UPDATE USL lightning\.metastore\.arbiter\.vendor_risk\.(\w+) SET TABLE DESCRIPTION '([^']*)'"
)


class UslColumn(BaseModel):
    name: str
    data_type: str
    nullable: bool = True
    description: str = ""


class UslForeignKey(BaseModel):
    columns: list[str]
    target_table: str
    target_columns: list[str]


class UslTable(BaseModel):
    name: str
    description: str = ""
    columns: list[UslColumn] = Field(default_factory=list)
    primary_key: list[str] = Field(default_factory=list)
    foreign_keys: list[UslForeignKey] = Field(default_factory=list)


class UslModel(BaseModel):
    name: str
    namespace: str
    description: str = ""
    tables: list[UslTable]


def load_model(path: Path | None = None) -> UslModel:
    """Parse the committed model. Table descriptions fall back to 03_usl.sql until LOAD USL carries them."""
    model_path = path or DEFAULT_MODEL
    if not model_path.is_file():
        raise ConfigError(f"USL model not found: {model_path}")
    raw = json.loads(model_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigError("USL model JSON must be an object")
    model = _parse_model(raw)
    model_desc, table_desc = _sql_descriptions(DEFAULT_SQL)
    if not model.description and model_desc:
        model.description = model_desc
    for table in model.tables:
        if not table.description and table.name in table_desc:
            table.description = table_desc[table.name]
    return model


def compact_catalogue(model: UslModel) -> str:
    """One line per table: name(pk, fk→table.col): description."""
    lines: list[str] = []
    for table in model.tables:
        parts = [f"{column} pk" for column in table.primary_key]
        for fk in table.foreign_keys:
            source = ", ".join(fk.columns)
            target = fk.target_columns[0] if fk.target_columns else ""
            parts.append(f"{source} fk→{fk.target_table}.{target}")
        lines.append(f"{table.name}({', '.join(parts)}): {table.description}")
    return "\n".join(lines)


def catalogue_tokens(text: str) -> int:
    """Token estimate used by the pass: character length divided by 4."""
    return len(text) // 4


def model_sha256(model: UslModel) -> str:
    return sha256_hex(model.model_dump(mode="json"))


def _sql_descriptions(path: Path) -> tuple[str, dict[str, str]]:
    if not path.is_file():
        return "", {}
    text = path.read_text(encoding="utf-8")
    model = _MODEL_DESC.search(text)
    tables = {match.group(1): match.group(2) for match in _TABLE_DESC.finditer(text)}
    return (model.group(1) if model else ""), tables


def _parse_model(raw: dict[str, object]) -> UslModel:
    namespace = raw.get("namespace")
    if isinstance(namespace, list):
        ns = ".".join(str(part) for part in namespace)
        if not ns.startswith("lightning."):
            ns = f"lightning.{ns}"
    else:
        ns = str(namespace or "lightning.metastore.arbiter")
    tables_raw = raw.get("tables")
    if not isinstance(tables_raw, list):
        raise ConfigError("USL model has no tables")
    tables = [_parse_table(item) for item in tables_raw if isinstance(item, dict)]
    description = raw.get("description") or raw.get("tableDescription") or ""
    return UslModel(
        name=str(raw.get("name") or "vendor_risk"),
        namespace=ns,
        description=str(description),
        tables=tables,
    )


def _parse_table(raw: dict[str, object]) -> UslTable:
    columns_raw = raw.get("columnSpecs") or raw.get("columns") or []
    columns: list[UslColumn] = []
    primary_key: list[str] = []
    foreign_keys: list[UslForeignKey] = []
    if isinstance(columns_raw, list):
        for item in columns_raw:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "")
            columns.append(
                UslColumn(
                    name=name,
                    data_type=_data_type(item.get("dataType") or item.get("type") or ""),
                    nullable="notNull" not in item and item.get("nullable") is not False,
                    description=str(item.get("description") or ""),
                )
            )
            if "primaryKey" in item or item.get("primary_key") is True:
                primary_key.append(name)
            fk = item.get("foreignKey") or item.get("foreign_key")
            if isinstance(fk, dict):
                foreign_keys.append(_foreign_key(name, fk))
    for item in raw.get("foreignKeys") or []:
        if isinstance(item, dict) and "refTable" in item:
            foreign_keys.append(_foreign_key("", item))
    description = raw.get("description") or raw.get("tableDescription") or ""
    return UslTable(
        name=str(raw.get("name") or ""),
        description=str(description),
        columns=columns,
        primary_key=primary_key,
        foreign_keys=foreign_keys,
    )


def _foreign_key(column_name: str, raw: dict[str, object]) -> UslForeignKey:
    ref_tables = raw.get("refTable") or raw.get("target_table") or []
    if isinstance(ref_tables, str):
        ref_tables = [ref_tables]
    target = str(ref_tables[-1]).split(".")[-1] if ref_tables else ""
    ref_columns = raw.get("refColumns") or raw.get("target_columns") or []
    if isinstance(ref_columns, str):
        ref_columns = [ref_columns]
    local = raw.get("columns") or []
    if isinstance(local, str):
        local = [local]
    columns = [str(col) for col in local] if local else ([column_name] if column_name else [])
    return UslForeignKey(
        columns=columns,
        target_table=target,
        target_columns=[str(col) for col in ref_columns],
    )


def _data_type(raw: object) -> str:
    text = str(raw).strip()
    if len(text) >= 2 and text[0] == text[-1] == '"':
        return text[1:-1]
    return text
