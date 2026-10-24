"""P18A-T1..T5: non-blocking runs, SSE trace streaming, resume, busy and keep-alive."""

from __future__ import annotations

import json
import threading
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.runhub import RunHub, get_hub
from tests.e2e.support import EXAMPLES, offline_env

pytestmark = pytest.mark.p18a
__all__ = ["offline_env"]


@pytest.fixture
def hub(offline_env: Path) -> Iterator[RunHub]:
    del offline_env
    fresh = RunHub()
    app.dependency_overrides[get_hub] = lambda: fresh
    yield fresh
    app.dependency_overrides.pop(get_hub, None)


def _body(name: str = "example_2.json") -> dict[str, Any]:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def parse_sse(text: str) -> list[dict[str, Any]]:
    """Split a raw SSE body into messages: {id, event, data} plus comment lines as {comment}."""
    messages: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for line in text.split("\n"):
        if line == "":
            if current:
                messages.append(current)
                current = {}
            continue
        if line.startswith(":"):
            messages.append({"comment": line[1:].strip()})
            continue
        field, _, value = line.partition(": ")
        if field == "data":
            current["data"] = json.loads(value)
        elif field == "id":
            current["id"] = int(value)
        else:
            current[field] = value
    if current:
        messages.append(current)
    return messages


def _stream(client: TestClient, url: str, headers: dict[str, str] | None = None) -> str:
    with client.stream("GET", url, headers=headers or {}) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        return "".join(response.iter_text())


def _start_example(client: TestClient) -> str:
    started = time.monotonic()
    response = client.post("/runs", json=_body())
    assert time.monotonic() - started < 5.0
    assert response.status_code == 202
    body = response.json()
    run_id = body["run_id"]
    assert body["events_url"] == f"/runs/{run_id}/events"
    assert body["status_url"] == f"/runs/{run_id}"
    return run_id


def test_p18a_t1_t2_t3_stream_matches_trace_and_resumes(hub: RunHub, offline_env: Path) -> None:
    """P18A-T1/T2/T3: 202 fast, ≥20 trace events then done ESCALATE; equal to the JSONL; resume by id."""
    del hub
    client = TestClient(app)
    run_id = _start_example(client)

    messages = parse_sse(_stream(client, f"/runs/{run_id}/events"))
    traces = [m for m in messages if m.get("event") == "trace"]
    finals = [m for m in messages if m.get("event") in {"done", "error"}]
    assert len(traces) >= 20
    assert len(finals) == 1 and finals[0]["event"] == "done"
    assert messages[-1] is finals[0]
    done = finals[0]["data"]
    assert done["run_id"] == run_id
    assert done["outcome"] == "ESCALATE"
    assert done["status"] in {"success", "partial_success", "escalated"}
    assert done["mode"] == {"data": "duckdb", "llm": "offline"}
    assert client.get(f"/cases/{done['case_id']}").status_code == 200

    # T2: identical to the trace file, line for line.
    lines = (offline_env / "logs" / f"trace-{run_id}.jsonl").read_text(encoding="utf-8").splitlines()
    on_disk = [json.loads(line) for line in lines if line.strip()]
    assert [m["data"] for m in traces] == on_disk
    assert [m["id"] for m in traces] == list(range(len(traces)))

    # T3: reconnect with Last-Event-ID: 9.
    resumed = parse_sse(_stream(client, f"/runs/{run_id}/events", {"Last-Event-ID": "9"}))
    rtraces = [m for m in resumed if m.get("event") == "trace"]
    ids = [m["id"] for m in rtraces]
    assert ids[0] == 10
    assert ids == sorted(set(ids))
    spans = [m["data"]["span_id"] for m in rtraces]
    assert len(spans) == len(set(spans))
    assert len(rtraces) == len(traces) - 10
    assert resumed[-1]["event"] == "done"

    # ?from=N is the same resume without the header.
    via_query = parse_sse(_stream(client, f"/runs/{run_id}/events?from=10"))
    assert [m["id"] for m in via_query if m.get("event") == "trace"] == ids

    status = client.get(f"/runs/{run_id}").json()
    assert status["state"] == "done"
    assert status["n_events"] == len(traces)
    assert status["response"]["run_id"] == run_id
    listed = client.get("/runs").json()
    assert listed[0]["run_id"] == run_id
    assert listed[0]["case_id"] == done["case_id"]
    assert client.get("/runs/run-000000000000/events").status_code == 404
    assert client.get("/runs/run-000000000000").status_code == 404


def _blocking_stub(release: threading.Event, *, sleep_s: float = 0.0):
    def stub(case: Any, *, options: Any, deps: Any) -> Any:
        tracer = deps.tracer_factory(f"run-{uuid.uuid4().hex[:12]}", {})
        if sleep_s:
            time.sleep(sleep_s)
        tracer.event("Orchestrator", "start_run", input_summary="case_id=CASE-STUB", output_summary="stub")
        release.wait(30)
        raise RuntimeError("stub finished")

    return stub


def test_p18a_t4_third_concurrent_run_is_busy(hub: RunHub, monkeypatch: pytest.MonkeyPatch) -> None:
    """P18A-T4: two runs in flight; the third POST /runs is 429 with the ErrorResponse shape."""
    del hub
    release = threading.Event()
    monkeypatch.setattr("app.orchestrator.run", _blocking_stub(release))
    client = TestClient(app)
    try:
        assert client.post("/runs", json=_body()).status_code == 202
        assert client.post("/runs", json=_body()).status_code == 202
        third = client.post("/runs", json=_body())
        assert third.status_code == 429
        body = third.json()
        assert body["status"] == "error"
        assert "run_id" in body
        assert body["error"]["type"] == "Busy"
        assert body["error"]["recoverable"] is True
        assert body["error"]["message"] == "Two assessments are already running. Wait for one to finish."
    finally:
        release.set()


def test_p18a_t5_keep_alive_comment_before_first_event(hub: RunHub, monkeypatch: pytest.MonkeyPatch) -> None:
    """P18A-T5: a run silent for 12 s gets a `:` keep-alive comment before its first trace event."""
    del hub
    release = threading.Event()
    release.set()
    monkeypatch.setattr("app.orchestrator.run", _blocking_stub(release, sleep_s=12.0))
    client = TestClient(app)
    run_id = client.post("/runs", json=_body()).json()["run_id"]
    raw = _stream(client, f"/runs/{run_id}/events")
    lines = raw.split("\n")
    first_event = next(i for i, line in enumerate(lines) if line == "event: trace")
    assert any(line.startswith(":") for line in lines[:first_event])
    messages = parse_sse(raw)
    assert messages[-1]["event"] == "error"
    assert messages[-1]["data"]["run_id"] == run_id
