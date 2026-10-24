"""In-process run registry: start runs on a thread and keep their trace events for streaming."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, Literal

from pydantic import BaseModel

from app import orchestrator
from app.config import mask_secrets
from app.errors import ArbiterError
from app.schemas.api import RunRequest
from app.schemas.trace import TraceEvent
from app.tracing import Tracer

logger = logging.getLogger("arbiter.runhub")

MAX_ACTIVE = 2
RETAIN = 50
START_TIMEOUT_S = 10.0
BUSY_MESSAGE = "Two assessments are already running. Wait for one to finish."


class Busy(ArbiterError):
    http_status = 429
    error_type = "Busy"


class RunRecord(BaseModel):
    run_id: str
    started_at: datetime
    finished_at: datetime | None = None
    state: Literal["running", "done", "error"]
    events: list[dict[str, Any]]
    response: dict[str, Any] | None = None
    error: str | None = None


class HubTracer(Tracer):
    """A Tracer that also hands each event to the hub, after the JSONL line is written."""

    def __init__(self, run_id: str, *, mode: dict[str, str], log_dir: str = "logs", hub: RunHub) -> None:
        super().__init__(run_id, mode=mode, log_dir=log_dir)
        self._hub = hub
        # Keeps the hub's order identical to the file's when agents trace from several threads.
        self._order = threading.Lock()

    def event(self, *args: Any, **kwargs: Any) -> TraceEvent:
        with self._order:
            evt = super().event(*args, **kwargs)
            self._hub._append(self.run_id, evt.model_dump(mode="json"))
        return evt


class _Start:
    """One start() call: the run id once the orchestrator asks for a tracer, or the thread's error."""

    def __init__(self) -> None:
        self.ready = threading.Event()
        self.claimed = False
        self.run_id: str | None = None
        self.error: BaseException | None = None


class RunHub:
    def __init__(self, *, run_fn: Callable[..., Any] | None = None, log_dir: str = "logs") -> None:
        self._run_fn = run_fn
        self._log_dir = log_dir
        self._cond = threading.Condition()
        self._records: dict[str, RunRecord] = {}
        self._pending = 0

    def start(self, request: RunRequest) -> str:
        with self._cond:
            active = self._pending + sum(rec.state == "running" for rec in self._records.values())
            if active >= MAX_ACTIVE:
                raise Busy(BUSY_MESSAGE, recoverable=True)
            self._pending += 1
        start = _Start()
        thread = threading.Thread(target=self._work, args=(request, start), name="arbiter-run", daemon=True)
        thread.start()
        start.ready.wait(START_TIMEOUT_S)
        if start.run_id is not None:
            return start.run_id
        if isinstance(start.error, ArbiterError):
            raise start.error
        if start.error is not None:
            raise ArbiterError(f"run failed to start: {_describe(start.error)}")
        raise ArbiterError(f"run did not start within {START_TIMEOUT_S:.0f} s", recoverable=True)

    def _work(self, request: RunRequest, start: _Start) -> None:
        tracer: HubTracer | None = None

        def factory(run_id: str, mode: dict[str, str]) -> Tracer:
            nonlocal tracer
            tracer = HubTracer(run_id, mode=mode, log_dir=self._log_dir, hub=self)
            with self._cond:
                self._records[run_id] = RunRecord(
                    run_id=run_id, started_at=datetime.now(UTC), state="running", events=[]
                )
                self._claim(start)
                self._trim()
            start.run_id = run_id
            start.ready.set()
            return tracer

        options = request.options
        run_fn = self._run_fn or orchestrator.run
        try:
            response = run_fn(
                request.case,
                options=orchestrator.RunOptions(
                    sample_mode=None if options is None else options.sample_mode,
                    llm=None if options is None else options.llm,
                ),
                deps=orchestrator.Deps(tracer_factory=factory),
            )
            self._finish(start.run_id, response=response.model_dump(mode="json"))
        except BaseException as exc:  # noqa: BLE001 - every failure must reach the stream
            logger.warning("run %s failed: %s", start.run_id, type(exc).__name__)
            start.error = exc
            self._finish(start.run_id, error=_describe(exc))
        finally:
            with self._cond:
                self._claim(start)
            start.ready.set()
            if tracer is not None:
                tracer.close()

    def _claim(self, start: _Start) -> None:
        # Caller holds the condition. A start leaves `pending` exactly once.
        if not start.claimed:
            start.claimed = True
            self._pending -= 1

    def _finish(
        self, run_id: str | None, *, response: dict[str, Any] | None = None, error: str | None = None
    ) -> None:
        with self._cond:
            record = self._records.get(run_id) if run_id else None
            if record is not None:
                record.finished_at = datetime.now(UTC)
                record.state = "error" if error is not None else "done"
                record.response = response
                record.error = error
                self._trim()
            self._cond.notify_all()

    def _append(self, run_id: str, event: dict[str, Any]) -> None:
        with self._cond:
            record = self._records.get(run_id)
            if record is not None:
                record.events.append(event)
            self._cond.notify_all()

    def _trim(self) -> None:
        # Caller holds the condition. Trace files on disk are never touched.
        finished = [rid for rid, rec in self._records.items() if rec.state != "running"]
        excess = len(self._records) - RETAIN
        for rid in finished[: max(excess, 0)]:
            del self._records[rid]

    def snapshot(self, run_id: str, start: int = 0) -> tuple[list[dict[str, Any]], RunRecord]:
        """Events from index `start`, plus a copy of the record. KeyError for an unknown run."""
        with self._cond:
            record = self._records[run_id]
            return record.events[max(start, 0) :], record.model_copy(update={"events": list(record.events)})

    def wait(self, run_id: str, after: int, timeout: float) -> bool:
        """Block until the run has more than `after` events or has finished; False on timeout."""
        with self._cond:
            record = self._records[run_id]
            return self._cond.wait_for(
                lambda: len(record.events) > after or record.state != "running", timeout
            )

    def list_recent(self, limit: int = 20) -> list[RunRecord]:
        with self._cond:
            records = sorted(self._records.values(), key=lambda rec: rec.started_at, reverse=True)
            return [rec.model_copy(update={"events": list(rec.events)}) for rec in records[:limit]]


def _describe(exc: BaseException) -> str:
    message = exc.message if isinstance(exc, ArbiterError) else str(exc)
    return mask_secrets(f"{type(exc).__name__}: {message}" if message else type(exc).__name__)


@lru_cache(maxsize=1)
def get_hub() -> RunHub:
    """The process-wide hub. Routes depend on it, so tests can override it."""
    return RunHub()
