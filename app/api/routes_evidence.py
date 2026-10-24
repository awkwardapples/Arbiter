"""Read-only data for the web console: registry, USL model, agents, proof, parity, recordings (lane P18-A)."""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml
from fastapi import APIRouter

from app.api.agent_roster import AGENT_ROSTER
from app.config import get_settings
from app.data.duckdb_backend import DuckDBBackend
from app.data.registry import load_registry, table_name
from app.data.usl_model import catalogue_tokens, compact_catalogue, load_model
from app.errors import ArbiterError, NotFound, ParseFailure

router = APIRouter(tags=["evidence"])

ROOT = Path(__file__).resolve().parents[2]
NIGHTSHIFT_PROOF = ROOT / "docs" / "evidence" / "nightshift_proof.json"
PARITY = ROOT / "docs" / "passes" / "P1-B_parity.json"
DQ_RULES = ROOT / "zetaris" / "dq_rules.yaml"

_TABLE_REF = re.compile(r"\{T\.(\w+)\}")
_RUN_ID = re.compile(r"^run-[0-9a-f]{12}$")
_CASE_DIGITS = re.compile(r"^CASE-(\d+)$")

_LANE_FIELDS = (
    "sent_model",
    "response_model",
    "routed_model",
    "requested_mode",
    "routed_mode",
    "mode_coerced",
    "receipt_id",
    "latency_ms",
    "tokens_in",
    "tokens_out",
)
_INT_FIELDS = {"latency_ms", "tokens_in", "tokens_out"}
_DEVIATION_FIELDS = ("kind", "detail", "model", "receipt_ids")

# (glob relative to the repo root, kind, failed). Fixed globs: request input never reaches a path.
_RECORDING_GLOBS: tuple[tuple[str, str, bool], ...] = (
    ("logs/examples/live/trace-run-*.jsonl", "live_example", False),
    ("eval/results_live/*/traces/trace-run-*.jsonl", "live_eval", False),
    ("logs/examples/session/trace-run-*.jsonl", "live_session", False),
    ("logs/examples/sample_mode/trace-run-*.jsonl", "sample_example", False),
    ("logs/examples/live_failed/trace-run-*.jsonl", "live_example", True),
)


# ---- registry and USL ------------------------------------------------------------------------


@router.get("/registry/queries")
def registry_queries() -> list[dict[str, Any]]:
    settings = get_settings()
    backend = "duckdb" if settings.SAMPLE_MODE else "zetaris"
    layer = settings.ZETARIS_QUERY_LAYER
    rows: list[dict[str, Any]] = []
    for qdef in load_registry().values():
        sql = qdef.sql_usl if backend == "zetaris" and layer == "usl" and qdef.sql_usl else qdef.sql
        if qdef.handler or not sql:
            resolved = None
        else:
            resolved = _TABLE_REF.sub(
                lambda m: table_name(m.group(1), backend=backend, layer=layer),  # type: ignore[arg-type]
                sql,
            ).strip()
        rows.append(
            {
                "id": qdef.id,
                "description": qdef.description,
                "systems": list(qdef.systems),
                "control_ids": list(qdef.control_ids),
                "params": [param.model_dump() for param in qdef.params],
                "sql": resolved,
            }
        )
    return rows


@router.get("/usl/model")
def usl_model() -> dict[str, Any]:
    model = load_model()
    return {
        "name": model.name,
        "namespace": model.namespace,
        "tables": [
            {
                "name": table.name,
                "description": table.description,
                "primary_key": table.primary_key,
                "columns": [column.model_dump() for column in table.columns],
                "foreign_keys": [fk.model_dump() for fk in table.foreign_keys],
            }
            for table in model.tables
        ],
        "catalogue_tokens": catalogue_tokens(compact_catalogue(model)),
    }


@router.get("/agents")
def agents() -> list[dict[str, str]]:
    return [dict(row) for row in AGENT_ROSTER]


# ---- committed evidence ----------------------------------------------------------------------


def _typed(field: str, value: Any) -> Any:
    """The proof stores every value as a string; give the console numbers and booleans back."""
    if field in _INT_FIELDS and isinstance(value, str) and value.isdigit():
        return int(value)
    if field == "mode_coerced" and value in {"True", "False"}:
        return value == "True"
    return value


def _host(base_url: object) -> str | None:
    if not isinstance(base_url, str) or not base_url:
        return None
    parts = urlsplit(base_url if "://" in base_url else f"http://{base_url}")
    if not parts.hostname:
        return None
    return f"{parts.hostname}:{parts.port}" if parts.port else parts.hostname


@router.get("/evidence/nightshift")
def nightshift_proof() -> dict[str, Any]:
    if not NIGHTSHIFT_PROOF.is_file():
        raise NotFound("no Nightshift proof is committed")
    raw = json.loads(NIGHTSHIFT_PROOF.read_text(encoding="utf-8"))
    body: dict[str, Any] = {"timestamp": raw.get("timestamp"), "base_url_host": _host(raw.get("base_url"))}
    for lane in ("fast", "deep"):
        source = raw.get(lane)
        if isinstance(source, dict):
            body[lane] = {field: _typed(field, source.get(field)) for field in _LANE_FIELDS}
    deviations = raw.get("deviations") if isinstance(raw.get("deviations"), list) else []
    body["deviations"] = [
        {
            field: [str(rid) for rid in item.get(field) or []] if field == "receipt_ids" else item.get(field)
            for field in _DEVIATION_FIELDS
        }
        for item in deviations
        if isinstance(item, dict)
    ]
    return body


@router.get("/evidence/parity")
def parity() -> dict[str, Any]:
    raw = json.loads(PARITY.read_text(encoding="utf-8"))
    rules = (yaml.safe_load(DQ_RULES.read_text(encoding="utf-8")) or {}).get("rules") or []
    by_table: dict[str, dict[str, Any]] = {}
    # The parity file repeats a table once per rule on it; it records invalid keys per table, not per rule.
    for row in raw.get("dq_parity") or []:
        by_table.setdefault(
            row["table"],
            {
                "table": row["table"],
                "zetaris": list(row.get("zetaris") or []),
                "mirror": list(row.get("duckdb") or []),
                "ok": bool(row.get("ok")),
            },
        )
    queries = raw.get("query_parity") or []
    kev = raw.get("kev_subset") or []
    return {
        "query_layer": raw.get("query_layer"),
        "source_mode": raw.get("source_mode"),
        "all_green": bool(raw.get("all_green")),
        "table_counts": [
            {key: row.get(key) for key in ("table", "expected", "zetaris", "ok")}
            for row in raw.get("table_counts") or []
        ],
        "rules": [{key: rule.get(key) for key in ("id", "table", "expr", "pk")} for rule in rules],
        "invalid_by_table": list(by_table.values()),
        "query_comparisons": {"total": len(queries), "ok": sum(bool(row.get("ok")) for row in queries)},
        "kev_checks": {"total": len(kev), "ok": sum(bool(row.get("ok")) for row in kev)},
    }


# ---- recordings ------------------------------------------------------------------------------

_index: dict[str, dict[str, Any]] | None = None
_index_lock = threading.Lock()


def reset_index() -> None:
    global _index
    with _index_lock:
        _index = None


def _read_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ParseFailure(f"recording line is not JSON: {exc}") from exc
    return events


def _vendor_name(case_id: str | None, cache: dict[str, str | None]) -> str | None:
    """The inverse of `app.state.case_id_for`, then `legal_name` from the DuckDB mirror."""
    if case_id is None:
        return None
    if case_id not in cache:
        match = _CASE_DIGITS.match(case_id)
        if match is None:
            cache[case_id] = "Inline submission"
        else:
            try:
                result = DuckDBBackend().run("Q_VENDOR_PROFILE", {"vendor_id": f"VND-{match.group(1)}"})
                rows = result.rows
            except ArbiterError:
                rows = []
            cache[case_id] = str(rows[0]["legal_name"]) if rows and rows[0].get("legal_name") else None
    return cache[case_id]


def _seconds(start: str, end: str) -> float:
    def parse(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    return round((parse(end) - parse(start)).total_seconds(), 3)


def _meta(path: Path, kind: str, failed: bool, vendors: dict[str, str | None]) -> dict[str, Any]:
    events = _read_events(path)
    first = events[0] if events else {}
    start = next((e for e in events if e.get("action") == "start_run"), None)
    complete = next((e for e in events if e.get("action") == "complete_run"), None)
    case_summary = str(start.get("input_summary", "")) if start else ""
    case_id = case_summary.removeprefix("case_id=") if case_summary.startswith("case_id=") else None
    outcome_text = str(complete.get("output_summary", "")) if complete else ""
    calls = [e for e in events if e.get("action") == "model_call"]
    meta: dict[str, Any] = {
        "run_id": path.stem.removeprefix("trace-"),
        "kind": kind,
        "path": path.relative_to(ROOT).as_posix(),
        "case_id": case_id,
        "vendor_name": _vendor_name(case_id, vendors),
        "outcome": outcome_text.split()[0] if outcome_text.split() else None,
        "duration_s": _seconds(events[0]["timestamp"], events[-1]["timestamp"]) if events else None,
        "recorded_at": first.get("timestamp"),
        "mode": first.get("mode"),
        "model_ids": sorted({str(e["model"]) for e in calls if e.get("model")}),
        "n_events": len(events),
        "n_model_calls": len(calls),
        "n_fallbacks": sum(e.get("status") == "fallback" for e in events),
        "n_queries": sum(e.get("action") == "query_run" for e in events),
    }
    if failed:
        meta["failed"] = True
    return meta


def _recordings() -> dict[str, dict[str, Any]]:
    global _index
    with _index_lock:
        if _index is None:
            index: dict[str, dict[str, Any]] = {}
            vendors: dict[str, str | None] = {}
            for pattern, kind, failed in _RECORDING_GLOBS:
                for path in sorted(ROOT.glob(pattern)):
                    run_id = path.stem.removeprefix("trace-")
                    if _RUN_ID.match(run_id) and run_id not in index:
                        index[run_id] = {"file": path, "meta": _meta(path, kind, failed, vendors)}
            _index = index
        return _index


@router.get("/recordings")
def list_recordings(include_failed: bool = False) -> list[dict[str, Any]]:
    return [
        entry["meta"] for entry in _recordings().values() if include_failed or not entry["meta"].get("failed")
    ]


@router.get("/recordings/{run_id}")
def get_recording(run_id: str) -> dict[str, Any]:
    entry = _recordings().get(run_id) if _RUN_ID.match(run_id) else None
    if entry is None:
        raise NotFound(f"recording {run_id} not found")
    return {"meta": entry["meta"], "events": _read_events(entry["file"])}
