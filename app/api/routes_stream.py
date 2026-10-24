"""POST /runs and its SSE event stream: a run the console can watch while it happens (lane P18-A)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse

from app.errors import NotFound
from app.runhub import RunHub, RunRecord, get_hub
from app.schemas.api import RunRequest

router = APIRouter(prefix="/runs", tags=["runs"])

POLL_S = 1.0
KEEP_ALIVE_S = 10.0

Hub = Annotated[RunHub, Depends(get_hub)]


def _record(hub: RunHub, run_id: str, start: int = 0) -> tuple[list[dict[str, Any]], RunRecord]:
    try:
        return hub.snapshot(run_id, start)
    except KeyError:
        raise NotFound(f"run {run_id} not found") from None


def _case_id(record: RunRecord) -> str | None:
    for event in record.events:
        if event.get("action") == "start_run":
            summary = str(event.get("input_summary", ""))
            return summary.removeprefix("case_id=") if summary.startswith("case_id=") else None
    return None


def _message(event: str, data: dict[str, Any], event_id: int | None = None) -> str:
    head = f"id: {event_id}\n" if event_id is not None else ""
    return f"{head}event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


def _final(record: RunRecord) -> str:
    if record.state == "done" and record.response is not None:
        response = record.response
        return _message(
            "done",
            {
                "run_id": record.run_id,
                "status": response.get("status"),
                "case_id": (response.get("output") or {}).get("case_id"),
                "outcome": (response.get("output") or {}).get("decision"),
                "execution_time_seconds": response.get("execution_time_seconds"),
                "mode": response.get("mode"),
            },
        )
    return _message(
        "error", {"run_id": record.run_id, "message": record.error or "run ended without a result"}
    )


@router.post("", status_code=202)
def start_run(body: RunRequest, hub: Hub) -> dict[str, str]:
    run_id = hub.start(body)
    return {"run_id": run_id, "events_url": f"/runs/{run_id}/events", "status_url": f"/runs/{run_id}"}


@router.get("")
def list_runs(hub: Hub) -> list[dict[str, Any]]:
    return [
        {"run_id": rec.run_id, "state": rec.state, "case_id": _case_id(rec), "started_at": rec.started_at}
        for rec in hub.list_recent()
    ]


@router.get("/{run_id}")
def run_status(run_id: str, hub: Hub) -> dict[str, Any]:
    _events, record = _record(hub, run_id)
    body: dict[str, Any] = {
        "run_id": record.run_id,
        "state": record.state,
        "n_events": len(record.events),
        "started_at": record.started_at,
        "finished_at": record.finished_at,
    }
    if record.response is not None:
        body["response"] = record.response
    if record.error is not None:
        body["error"] = record.error
    return body


@router.get("/{run_id}/events")
def run_events(
    run_id: str,
    hub: Hub,
    last_event_id: str | None = Header(default=None),
    from_index: int = Query(default=0, alias="from", ge=0),
) -> StreamingResponse:
    start = from_index
    if last_event_id is not None and last_event_id.strip().isdigit():
        start = int(last_event_id) + 1
    _record(hub, run_id)  # 404 before the stream starts
    return StreamingResponse(
        _stream(hub, run_id, start),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream(hub: RunHub, run_id: str, start: int) -> AsyncIterator[str]:
    index = start
    loop = asyncio.get_running_loop()
    last_output = loop.time()
    while True:
        try:
            events, record = hub.snapshot(run_id, index)
        except KeyError:
            yield _message("error", {"run_id": run_id, "message": "run is no longer retained"})
            return
        for event in events:
            yield _message("trace", event, index)
            index += 1
            last_output = loop.time()
        if record.state != "running" and index >= len(record.events):
            yield _final(record)
            return
        if not events:
            if loop.time() - last_output >= KEEP_ALIVE_S:
                yield ": keep-alive\n\n"
                last_output = loop.time()
            try:
                await asyncio.to_thread(hub.wait, run_id, index, POLL_S)
            except KeyError:
                continue
