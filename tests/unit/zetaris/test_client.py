"""P1-B Zetaris client tests (P1-T20..P1-T22, P1-T24)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import httpx
import pytest
import respx

from app.config import Settings
from app.data.backend import FallbackBackend
from app.data.duckdb_backend import DuckDBBackend, reset_cache
from app.data.registry import load_registry
from app.data.zetaris import ZetarisBackend, normalise_response
from app.errors import Unauthorized, UpstreamError
from app.tracing import Tracer

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "tests" / "fixtures" / "zetaris_run_response.json"


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("ZETARIS_API_KEY", "test-key-not-real")
    monkeypatch.setenv("ZETARIS_REST_URL", "http://zetaris.test/api/v1.0")
    monkeypatch.setenv("ZETARIS_ORG_ID", "1")
    from app.config import get_settings

    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
def tracer(tmp_path: Path) -> Tracer:
    return Tracer("p1b-test", mode={"data": "zetaris"}, log_dir=str(tmp_path))


@pytest.mark.p1b
def test_p1_t20_request_shape(settings: Settings, tracer: Tracer) -> None:
    """P1-T20: URL, headers, body shape, no trailing semicolon in sql."""
    reg = load_registry()
    backend = ZetarisBackend(settings, reg, tracer)
    captured: dict[str, object] = {}

    def _check(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["headers"] = dict(request.headers)
        body = json.loads(request.content.decode())
        captured["body"] = body
        assert not str(body["sql"]).endswith(";")
        return httpx.Response(
            200,
            json={"headers": ["one"], "data": [["1"]]},
        )

    with respx.mock:
        respx.post("http://zetaris.test/api/v1.0/sql-editor/sqls/run").mock(side_effect=_check)
        backend._execute_with_retry("SELECT 1 AS one", purpose="test")

    assert captured["method"] == "POST"
    assert captured["url"] == "http://zetaris.test/api/v1.0/sql-editor/sqls/run"
    headers = captured["headers"]
    assert headers["authorization"] == "Bearer test-key-not-real"
    assert headers["x-org-id"] == "1"
    assert uuid.UUID(str(headers["x-request-id"]))
    body = captured["body"]
    assert set(body.keys()) == {"queryId", "sql", "source", "limit"}
    assert body["source"] == "SqlEditor"
    assert isinstance(body["queryId"], str)


@pytest.mark.p1b
def test_p1_t21_normaliser_fixture() -> None:
    """P1-T21: fixture shapes normalise with coercion."""
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cols = [
        "vendor_id",
        "legal_name",
        "trading_name",
        "category",
        "requested_service",
        "business_owner",
        "annual_spend_gbp",
        "criticality",
        "data_categories",
        "processing_countries",
        "clm_supplier_ref",
        "onboarding_status",
        "requested_at",
    ]
    pos = normalise_response(raw["vendor_profile_positional"], cols)
    assert pos[0]["vendor_id"] == "VND-0003"
    assert pos[0]["annual_spend_gbp"] == 5000

    dict_rows = normalise_response(raw["vendor_profile_dicts"]["data"], cols)
    assert dict_rows[0]["annual_spend_gbp"] == 5000
    assert dict_rows[0]["dpa_signed"] is True
    assert dict_rows[0]["breach_notification_hours"] == 72

    one = normalise_response(raw["select_one"], ["one", "s"])
    assert one[0]["one"] == 1


@pytest.mark.p1b
def test_p1_t22_retries_fallback_and_unauthorized(settings: Settings, tracer: Tracer, tmp_path: Path) -> None:
    """P1-T22: retries on 5xx, fallback to DuckDB, 401 pins without retry."""
    reset_cache()
    reg = load_registry()
    zbackend = ZetarisBackend(settings, reg, tracer)
    url = "http://zetaris.test/api/v1.0/sql-editor/sqls/run"
    ok = httpx.Response(200, json={"headers": ["one"], "data": [["1"]]})

    with respx.mock:
        respx.post(url).mock(side_effect=[httpx.Response(500), httpx.Response(500), ok])
        rows, _, _ = zbackend._execute_with_retry("SELECT 1 AS one", purpose="retry")
    assert rows[0]["one"] == 1
    trace_lines = (tmp_path / "trace-p1b-test.jsonl").read_text().strip().splitlines()
    retry_events = [json.loads(line) for line in trace_lines if json.loads(line).get("status") == "retrying"]
    assert len(retry_events) == 2

    with respx.mock:
        respx.post(url).mock(return_value=httpx.Response(500))
        with pytest.raises(UpstreamError):
            zbackend._execute_with_retry("SELECT 1 AS one", purpose="fail")

    reset_cache()
    duck = DuckDBBackend()
    fb = FallbackBackend(zbackend, duck, tracer)
    with respx.mock:
        respx.post(url).mock(return_value=httpx.Response(500))
        res = fb.run("Q_VENDOR_PROFILE", {"vendor_id": "VND-0003"})
    assert res.fallback_from == "zetaris"
    assert res.backend == "duckdb"

    calls = {"n": 0}

    def _401(_: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(401, json={"msg": "nope"})

    with respx.mock:
        respx.post(url).mock(side_effect=_401)
        with pytest.raises(Unauthorized):
            zbackend._execute_with_retry("SELECT 1 AS one", purpose="auth")
    assert calls["n"] == 1


@pytest.mark.p1b
def test_p1_t24_no_secrets_in_logs(
    settings: Settings,
    tracer: Tracer,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """P1-T24: traces and logs must not contain the bearer token."""
    reg = load_registry()
    backend = ZetarisBackend(settings, reg, tracer)
    with respx.mock:
        respx.post("http://zetaris.test/api/v1.0/sql-editor/sqls/run").mock(
            return_value=httpx.Response(200, json={"headers": ["one"], "data": [["1"]]})
        )
        backend._execute_with_retry("SELECT 1 AS one", purpose="secret-scan")
    trace_text = (tmp_path / "trace-p1b-test.jsonl").read_text()
    assert "test-key-not-real" not in trace_text
    assert "Bearer test-key-not-real" not in trace_text
    combined = caplog.text + trace_text
    assert "Authorization" not in combined or "test-key-not-real" not in combined
