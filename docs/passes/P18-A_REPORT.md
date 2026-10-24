# P18-A report: streaming and read API for the console

Lane `18a`, branch `p18a-stream`. Plan: `.cursor/plans/P18-A.md`. Built in Claude Code (Opus 5.5).

## What was built

- **`app/runhub.py`.** An in-process run registry.
  - `RunHub.start()` runs the unchanged `app.orchestrator.run()` on a daemon thread. It returns the real `run_id` as soon as the orchestrator asks for its tracer.
  - `HubTracer` subclasses `Tracer`. It writes the JSONL line exactly as before, then hands the same event to the hub under one lock, so the hub's order always matches the file's.
  - At most 2 runs are active. A third start raises `Busy`, which the API returns as 429. The hub keeps the last 50 records and never touches trace files.
- **`app/api/routes_stream.py`.**
  - `POST /runs` returns 202 with `{run_id, events_url, status_url}`.
  - `GET /runs/{id}/events` streams SSE. It resumes from `Last-Event-ID + 1`, or `?from=N`, or 0. It sends `: keep-alive` after 10 s without output and ends with `event: done` or `event: error`. The async generator polls the hub with `asyncio.to_thread(hub.wait, …, 1.0)`.
  - `GET /runs/{id}` and `GET /runs` report a run's state and the recent runs.
- **`app/api/routes_evidence.py`.**
  - `GET /registry/queries` resolves every `{T.<table>}` for the current layer through `registry.table_name()`.
  - `GET /usl/model` returns the USL model.
  - `GET /agents` returns `AGENT_ROSTER` (`app/api/agent_roster.py`).
  - `GET /evidence/nightshift` is built field by field from a whitelist.
  - `GET /evidence/parity` combines the parity file with `dq_rules.yaml`.
  - `GET /recordings` and `GET /recordings/{run_id}` serve committed traces. The index is built from fixed globs on first request. A detail lookup must match `^run-[0-9a-f]{12}$` and be in the index. Each recording's vendor name comes from the DuckDB mirror's `Q_VENDOR_PROFILE`.
- **`app/api/routes_web.py`.** When `web/dist/index.html` exists, it mounts `web/dist` at `/console` and `/` redirects there (307). The mount serves `index.html` for unknown paths, which covers client routes. Without a build, `/` returns the "not built" JSON.
- **`app/api/main.py`.** Two `include_router` lines, `routes_web.install(app)`, and CORS for `http://localhost:5173` only when `ARBITER_DEV_CORS=1`.
- **Three trace events.**
  - `<agent> model_request`: emitted in `_Call.chat()` just before the provider call, for the first attempt and the repair attempt.
  - `EvaluatorAgent contradiction_found`: once per `(key, claim_id)` per run. Values are masked, then cut to 80 characters.
  - `PolicyEngine decide`: emitted after each DECIDE_1 and DECIDE_2 decision, before `Orchestrator redecide`.
- **`.dockerignore`.** `!logs/examples/` and `!logs/examples/**` added after `logs/*`.
- **`scripts/gates/p18a.py`.** Fails if any `.jsonl` under `logs/examples/` or `eval/results_live/` has changed since this branch left `main`, whether committed or not.

## Deviations from the spec (all approved in the plan)

1. **Branch:** `p18a-stream` (the worktree branch), not `p18a-stream-api`.
2. **`ARBITER_DEV_CORS`** is read in `main.py`, because `app/config.py` belongs to lane 19. It moves into `Settings` after P19 merges.
3. **Main wiring:** two `include_router` lines plus `routes_web.install(app)`, not three `include_router` lines. A mount cannot be carried on an `APIRouter`.
4. **Recordings index:** built on first request and cached for the life of the process, not at startup.
5. **Catch-all route:** it is the `StaticFiles` subclass's 404 handler, not a separate `GET /console/{path:path}` route. The behaviour is the same, and assets still win over the fallback.
6. **Nightshift proof types:** the committed proof stores `latency_ms`, `tokens_in`, `tokens_out` and `mode_coerced` as strings. The endpoint returns them as integers and a boolean.

## Existing tests changed

None. No existing test asserts an exact event sequence that the new events break. `check_trace` counts only `model_call` events with a `model` set as proof of live use, so `--require-live` is unaffected.

## Known gaps

- `tests/unit/ui/test_p12.py::test_p12_logo_asset` fails on this branch **and on `main`**. Commit `994d090` ("docs: update Arbiter logo") replaced `docs/img/arbiter_logo.png` with a PNG that has no `tRNS` transparency chunk. Neither the image nor the test belongs to lane 18a, so `verify-pass --pass 18a` fails at the regression step until one of them changes. Every other step is green.
- The 12 root-level `logs/examples/trace-run-*.jsonl` traces (P5-B era, offline) match none of the four recording kinds, so they are not indexed. P20 owns that folder.
- The run hub is in-process. Restarting the server loses streamed-run history, but the trace files and cases remain.
- T5 takes about 12 s of wall time, as the spec requires.

## Commands run

```
.venv/bin/python -m pytest -m p18a -q                     # 15 passed
.venv/bin/python scripts/tasks.py verify-pass --pass 18a  # lint ok; 857 passed, 1 failed (test_p12_logo_asset, pre-existing)
.venv/bin/python scripts/gates/p18a.py                    # 0
.venv/bin/python scripts/tasks.py secret-scan             # 0
.venv/bin/python scripts/tasks.py hardcode-check          # 0
```
