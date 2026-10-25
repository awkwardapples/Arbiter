"""P18A-T6..T10, T14: read-only console endpoints (recordings, registry, USL, proof, parity, roster)."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from app.api import routes_evidence
from app.api.main import app
from app.data.registry import load_registry

pytestmark = pytest.mark.p18a

ROOT = Path(__file__).resolve().parents[3]

LANE_KEYS = {
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
}
TOP_KEYS = {"timestamp", "base_url_host", "fast", "deep", "deviations"}
DEVIATION_KEYS = {"kind", "detail", "model", "receipt_ids"}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("SAMPLE_MODE", "true")
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    routes_evidence.reset_index()
    yield TestClient(app)
    routes_evidence.reset_index()


def test_p18a_t6_recordings_index(client: TestClient) -> None:
    """P18A-T6: kinds, vendor lookup, no baselines, failed only on request, safe detail lookup."""
    rows = client.get("/recordings").json()
    by_id = {row["run_id"]: row for row in rows}
    assert by_id["run-211916c1544d"]["kind"] == "live_example"  # P20: example 2 live (approved repoint)
    live_eval = by_id["run-257c86984507"]
    assert live_eval["kind"] == "live_eval"
    assert live_eval["vendor_name"] == "Quillfeather Payroll Cloud Ltd"
    assert live_eval["outcome"] == "ESCALATE"
    assert live_eval["case_id"] == "CASE-0007"
    assert live_eval["n_events"] > 0 and live_eval["n_model_calls"] > 0
    assert live_eval["mode"] == {"data": "zetaris", "llm": "meterless"}
    assert live_eval["model_ids"] == sorted(set(live_eval["model_ids"]))
    assert {row["kind"] for row in rows} <= {"live_example", "live_eval", "live_session", "sample_example"}
    assert any(row["kind"] == "sample_example" for row in rows)
    assert any(row["kind"] == "live_session" for row in rows)
    assert all("trace-baseline-" not in row["path"] for row in rows)
    assert all(not row.get("failed") for row in rows)
    assert not any(row["path"].startswith("logs/examples/live_failed/") for row in rows)

    failed = [row for row in client.get("/recordings?include_failed=true").json() if row.get("failed")]
    assert {row["run_id"] for row in failed} == {
        p.stem.removeprefix("trace-") for p in (ROOT / "logs/examples/live_failed").glob("trace-run-*.jsonl")
    }

    detail = client.get("/recordings/run-257c86984507").json()
    assert detail["meta"] == live_eval
    assert len(detail["events"]) == live_eval["n_events"]
    assert detail["events"][0]["action"] == "start_run"

    assert client.get("/recordings/run-../../etc").status_code == 404
    assert client.get("/recordings/run-000000000000").status_code == 404
    assert client.get("/recordings/..%2F..%2Fetc%2Fpasswd").status_code == 404


def test_p18a_t7_registry_queries(client: TestClient) -> None:
    """P18A-T7: every registry id with systems; no `{T.` placeholders survive."""
    response = client.get("/registry/queries")
    assert response.status_code == 200
    rows = response.json()
    assert {row["id"] for row in rows} == set(load_registry())
    for row in rows:
        assert isinstance(row["systems"], list)
        assert set(row) == {"id", "description", "systems", "control_ids", "params", "sql"}
    assert "{T." not in response.text
    profile = next(row for row in rows if row["id"] == "Q_VENDOR_PROFILE")
    assert re.search(r"\bFROM vendor\b", profile["sql"])


def test_p18a_t8_usl_model(client: TestClient) -> None:
    """P18A-T8: 10 tables; vendor_alias.vendor_id → vendor.vendor_id."""
    body = client.get("/usl/model").json()
    assert len(body["tables"]) == 10
    assert body["catalogue_tokens"] > 0
    alias = next(t for t in body["tables"] if t["name"] == "vendor_alias")
    assert {
        "columns": ["vendor_id"],
        "target_table": "vendor",
        "target_columns": ["vendor_id"],
    } in alias["foreign_keys"]


def _keys(obj: Any, path: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield path, key
            yield from _keys(value, f"{path}.{key}" if path else key)
    elif isinstance(obj, list):
        for item in obj:
            yield from _keys(item, path)


def _assert_whitelisted(body: dict[str, Any]) -> None:
    for path, key in _keys(body):
        if path == "":
            assert key in TOP_KEYS, key
        elif path in {"fast", "deep"}:
            assert key in LANE_KEYS, (path, key)
        elif path == "deviations":
            assert key in DEVIATION_KEYS, (path, key)
        else:
            raise AssertionError(f"unexpected nested key {path}.{key}")


def test_p18a_t9_nightshift_whitelist(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """P18A-T9: only whitelisted keys, recursively; a planted Authorization header never leaks."""
    body = client.get("/evidence/nightshift").json()
    _assert_whitelisted(body)
    assert body["base_url_host"] == "localhost:8088"
    assert set(body["fast"]) == LANE_KEYS
    assert body["deviations"]

    proof = json.loads(routes_evidence.NIGHTSHIFT_PROOF.read_text(encoding="utf-8"))
    proof["Authorization"] = "Bearer canary-123"
    proof["fast"]["Authorization"] = "Bearer canary-123"
    proof["fast"]["receipt"]["Authorization"] = "Bearer canary-123"
    proof["deviations"][0]["Authorization"] = "Bearer canary-123"
    planted = tmp_path / "proof.json"
    planted.write_text(json.dumps(proof), encoding="utf-8")
    monkeypatch.setattr(routes_evidence, "NIGHTSHIFT_PROOF", planted)
    response = client.get("/evidence/nightshift")
    assert response.status_code == 200
    assert "Authorization" not in response.text
    assert "canary-123" not in response.text
    _assert_whitelisted(response.json())


def test_p18a_t10_parity(client: TestClient) -> None:
    """P18A-T10: green, CTR-30028 on contract both sides, the 5 DQ rules, 416 query comparisons."""
    body = client.get("/evidence/parity").json()
    assert body["all_green"] is True
    contract = [row for row in body["invalid_by_table"] if row["table"] == "contract"]
    assert len(contract) == 1
    assert contract[0]["zetaris"] == ["CTR-30028"]
    assert contract[0]["mirror"] == ["CTR-30028"]
    assert contract[0]["ok"] is True
    rules = yaml.safe_load((ROOT / "zetaris" / "dq_rules.yaml").read_text(encoding="utf-8"))["rules"]
    assert [r["id"] for r in body["rules"]] == [r["id"] for r in rules]
    assert len(body["rules"]) == 5
    assert body["query_comparisons"]["total"] == 416
    assert body["query_comparisons"]["ok"] == 416
    assert body["kev_checks"]["total"] > 0
    assert body["query_layer"] == "usl"
    assert {"table", "expected", "zetaris", "ok"} <= set(body["table_counts"][0])


def _readme_rows() -> list[list[str]]:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    section = text.split("## How it works", 1)[1]
    rows: list[list[str]] = []
    for line in section.splitlines():
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells[0] == "Name in traces" or set(cells[0]) <= {"-"}:
            continue
        rows.append(cells)
    return rows


def test_p18a_t14_agent_roster_matches_readme(client: TestClient) -> None:
    """P18A-T14: GET /agents equals the README "How it works" table, row by row."""
    expected = [
        {"trace_name": r[0].strip("`"), "kind": r[1], "lane": r[2], "can": r[3], "cannot": r[4]}
        for r in _readme_rows()
    ]
    assert len(expected) == 9
    got = client.get("/agents").json()
    assert [{k: row[k] for k in ("trace_name", "kind", "lane", "can", "cannot")} for row in got] == expected
    assert all(row["name"] for row in got)
