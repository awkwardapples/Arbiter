"""Zetaris REST SQL backend (lane P1-B)."""

from __future__ import annotations

import json
import re
import time
import uuid
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_chain,
    wait_fixed,
)

from app.config import Settings, get_settings
from app.data.backend import QueryResult
from app.data.dq import invalid_keys, load_dq_rules
from app.data.registry import QueryDef, load_registry, render, validate_params
from app.errors import Unauthorized, UpstreamError, UpstreamTimeout
from app.tracing import Tracer

_DEGRADED_UNTIL: float = 0.0


def _api_key(settings: Settings) -> str:
    raw = settings.ZETARIS_API_KEY
    if raw is None:
        raise Unauthorized("ZETARIS_API_KEY is not configured")
    key = raw.get_secret_value()
    if not key or key.startswith("your-"):
        raise Unauthorized("ZETARIS_API_KEY is not configured")
    return key


def _strip_sql(sql: str) -> str:
    return sql.strip().rstrip(";")


def _coerce_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("true", "false"):
            return low == "true"
        if re.fullmatch(r"-?\d+", value.strip()):
            return int(value.strip())
        if re.fullmatch(r"-?\d+\.\d+", value.strip()):
            return float(value.strip())
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()):
            return value.strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}T.*", value.strip()):
            return value.strip()[:10]
    return value


def normalise_response(payload: object, columns: list[str]) -> list[dict[str, object]]:
    """Map Zetaris SQL editor shapes to row dicts."""
    if payload is None:
        return []
    if isinstance(payload, list):
        if not payload:
            return []
        if isinstance(payload[0], dict):
            return [{k: _coerce_value(v) for k, v in row.items()} for row in payload]
        if columns and isinstance(payload[0], list | tuple):
            out: list[dict[str, object]] = []
            for row in payload:
                if not isinstance(row, list | tuple):
                    continue
                out.append(
                    {columns[i]: _coerce_value(row[i]) if i < len(row) else None for i in range(len(columns))}
                )
            return out
    if isinstance(payload, dict):
        if "headers" in payload and "data" in payload:
            hdrs = [str(h) for h in payload.get("headers") or columns]
            return normalise_response(payload.get("data"), hdrs or columns)
        cols = payload.get("columns") or columns
        rows = payload.get("rows") or payload.get("data")
        if isinstance(rows, list):
            return normalise_response(rows, [str(c) for c in cols])
    return []


def _should_retry(exc: BaseException) -> bool:
    return isinstance(exc, UpstreamTimeout | UpstreamError)


class ZetarisBackend:
    name = "zetaris"

    def __init__(
        self,
        settings: Settings,
        registry: dict[str, QueryDef],
        tracer: Tracer,
        *,
        agent_name: str = "data",
    ) -> None:
        self._settings = settings
        self._registry = registry
        self._tracer = tracer
        self._agent_name = agent_name

    def run(self, query_id: str, params: dict[str, object]) -> QueryResult:
        t0 = time.perf_counter()
        qdef = self._registry[query_id]
        request_id = uuid.uuid4().hex
        if qdef.handler == "dq_invalid":
            validated = validate_params(query_id, params, self._registry)
            rows = self._dq_invalid_rows(str(validated["vendor_id"]))
        else:
            sql = render(
                query_id,
                params,
                backend="zetaris",
                layer=self._settings.ZETARIS_QUERY_LAYER,
                registry=self._registry,
            )
            if query_id == "Q_KEV_BY_PRODUCTS":
                sql = self._kev_by_products_sql(params)
            rows, request_id, _lat = self._execute_with_retry(sql, purpose=query_id)
            rows = [{c: row.get(c) for c in qdef.columns} for row in rows]
        latency = int((time.perf_counter() - t0) * 1000)
        self._tracer.event(
            self._agent_name,
            "query_zetaris",
            input_summary=f"query_id={query_id}",
            output_summary=f"rows={len(rows)} zetaris_request_id={request_id}",
            status="success",
            query_id=query_id,
            rows=len(rows),
            backend="zetaris",
            latency_ms=latency,
        )
        return QueryResult(
            query_id=query_id,
            rows=rows,
            columns=qdef.columns,
            backend="zetaris",
            request_id=request_id,
            latency_ms=latency,
        )

    def _kev_by_products_sql(self, params: dict[str, object]) -> str:
        validated = validate_params("Q_KEV_BY_PRODUCTS", params, self._registry)
        products = validated.get("products") or []
        if not isinstance(products, list):
            products = []
        clauses = [
            f"lower(product) LIKE concat('%', '{str(p).lower().replace(chr(39), chr(39) + chr(39))}', '%')"
            for p in products
        ]
        where = " OR ".join(clauses) if clauses else "1=0"
        table = (
            "arbiter.kev_vuln_v"
            if self._settings.ZETARIS_QUERY_LAYER == "views"
            else "lightning.metastore.arbiter.vendor_risk.kev_vuln"
        )
        cols = "cve_id, vendor_project, product, vulnerability_name, date_added, due_date, ransomware_use"
        return f"SELECT {cols} FROM {table} WHERE {where} ORDER BY cve_id"

    def _dq_invalid_rows(self, vendor_id: str) -> list[dict[str, object]]:
        out: list[dict[str, object]] = []
        rules = load_dq_rules()
        for rule in rules:
            keys = invalid_keys(self, rule.table, vendor_id=vendor_id, rules=[rule])
            for key in sorted(keys):
                out.append({"rule_id": rule.id, "table_name": rule.table, "record_key": key})
        return out

    def dq_invalid(self, table: str) -> set[str]:
        ns = "lightning.metastore.arbiter.vendor_risk"
        sql = f"SHOW DQ ALL INVALID TABLE {ns}.{table}"
        rows = self.execute_sql(sql, purpose="dq_invalid")
        keys: set[str] = set()
        rule_ids = {r.id for r in load_dq_rules() if r.table == table}
        pk_by_rule = {r.id: r.pk for r in load_dq_rules() if r.table == table}
        for row in rows:
            records_raw = row.get("records") or row.get("RECORDS")
            if records_raw is None:
                continue
            parsed = json.loads(records_raw) if isinstance(records_raw, str) else records_raw
            if isinstance(parsed, dict):
                parsed = [parsed]
            if not isinstance(parsed, list):
                continue
            for rec in parsed:
                if not isinstance(rec, dict):
                    continue
                rule_name = str(rec.get("rule") or rec.get("ruleName") or rec.get("rule_id") or "")
                if rule_ids and rule_name and rule_name not in rule_ids:
                    continue
                pk_field = pk_by_rule.get(rule_name) or next(iter(pk_by_rule.values()), "id")
                val = rec.get(pk_field) or rec.get("record_key")
                if val is not None:
                    keys.add(str(val))
        if not keys and rows:
            for row in rows:
                for k, v in row.items():
                    if v is not None and (
                        str(k).endswith("_id") or k in ("contract_id", "incident_number", "cve_id")
                    ):
                        keys.add(str(v))
        return keys

    def _qualify_dq_sql(self, sql: str) -> str:
        layer = self._settings.ZETARIS_QUERY_LAYER
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
        for table in tables:
            if layer == "views":
                replacement = f"arbiter.{table}_v"
            else:
                replacement = f"lightning.metastore.arbiter.vendor_risk.{table}"
            # A name already behind a dot is a qualified USL or view reference.
            sql = re.sub(rf"(?<!\.)\b{re.escape(table)}\b", replacement, sql)
        return sql

    def execute_sql(self, sql: str, *, purpose: str = "sql") -> list[dict[str, object]]:
        rows, _, _ = self._execute_with_retry(self._qualify_dq_sql(sql), purpose=purpose)
        return rows

    def _execute_with_retry(self, sql: str, *, purpose: str) -> tuple[list[dict[str, object]], str, int]:
        sql = _strip_sql(sql)
        request_id = str(uuid.uuid4())

        def _before_sleep(retry_state: Any) -> None:
            self._tracer.event(
                self._agent_name,
                "query_zetaris",
                input_summary=f"purpose={purpose}",
                output_summary="retry after upstream error",
                status="retrying",
                retry_count=retry_state.attempt_number,
                backend="zetaris",
            )

        @retry(
            retry=retry_if_exception(_should_retry),
            stop=stop_after_attempt(3),
            wait=wait_chain(wait_fixed(1), wait_fixed(3)),
            reraise=True,
            before_sleep=_before_sleep,
        )
        def _post() -> tuple[list[dict[str, object]], str, int]:
            return self._post_once(sql, request_id=request_id, purpose=purpose)

        return _post()

    def _post_once(
        self,
        sql: str,
        *,
        request_id: str,
        purpose: str,
    ) -> tuple[list[dict[str, object]], str, int]:
        settings = self._settings
        url = settings.ZETARIS_REST_URL.rstrip("/") + "/sql-editor/sqls/run"
        body = {
            "queryId": str(uuid.uuid4()),
            "sql": sql,
            "source": "SqlEditor",
            "limit": 1000,
        }
        headers = {
            "Authorization": f"Bearer {_api_key(settings)}",
            "X-Org-ID": str(settings.ZETARIS_ORG_ID),
            "X-Request-ID": request_id,
            "Content-Type": "application/json",
        }
        t0 = time.perf_counter()
        try:
            resp = httpx.post(
                url,
                json=body,
                headers=headers,
                timeout=float(settings.ZETARIS_TIMEOUT_SECONDS),
            )
        except httpx.TimeoutException as exc:
            raise UpstreamTimeout(str(exc)) from exc
        latency = int((time.perf_counter() - t0) * 1000)
        if resp.status_code in (401, 403):
            global _DEGRADED_UNTIL
            _DEGRADED_UNTIL = time.time() + 60
            raise Unauthorized(f"Zetaris HTTP {resp.status_code}")
        if resp.status_code >= 500:
            raise UpstreamError(f"Zetaris HTTP {resp.status_code}")
        if resp.status_code >= 400:
            msg = resp.text[:500]
            raise UpstreamError(f"Zetaris HTTP {resp.status_code}: {msg}")
        payload = resp.json()
        data = payload.get("data") if isinstance(payload, dict) else payload
        hdrs = payload.get("headers") if isinstance(payload, dict) else None
        columns = [str(h) for h in hdrs] if hdrs else []
        rows = normalise_response(data if hdrs is None else payload, columns)
        return rows, request_id, latency


def status(settings: Settings | None = None) -> dict[str, object]:
    settings = settings or get_settings()
    out: dict[str, object] = {
        "reachable": False,
        "degraded": time.time() < _DEGRADED_UNTIL,
        "query_layer": settings.ZETARIS_QUERY_LAYER,
        "source_mode": settings.ZETARIS_SOURCE_MODE,
    }
    try:
        tracer = Tracer("zetaris-status", mode=settings.mode(), log_dir="logs")
        backend = ZetarisBackend(settings, load_registry(), tracer)
        rows, req_id, latency = backend._execute_with_retry("SELECT 1 AS one", purpose="status")
        val = rows[0].get("one") if rows else None
        out.update(
            {
                "reachable": str(val) in ("1", "1.0", 1),
                "select_one": val,
                "zetaris_request_id": req_id,
                "latency_ms": latency,
            }
        )
    except Exception as exc:  # noqa: BLE001 — health probe
        out["error"] = type(exc).__name__
    return out
