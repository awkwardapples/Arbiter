# P18-A: streaming and read API for the console (lane `18a`)

Merges into `main`. It is additive and changes no decision. It is the backend for the web console, and it also makes the trace show three moments it currently hides.

## 1. Goal

1. A run can be **started without blocking**, and its trace events can be **streamed live** to a browser.
2. The console can read everything else it needs over HTTP, so it never touches the filesystem:
   - committed recordings;
   - the query registry with systems;
   - the USL model;
   - the Nightshift proof;
   - the DQ results;
   - the agent roster.
3. The trace records three moments it currently hides, honestly and from code that runs:
   - the moment a model request is **sent** (live calls take 10–45 s, and today nothing is logged until they return);
   - each **contradiction** with its two sides;
   - each **policy decision** with its tier, outcome and failing controls.
4. FastAPI serves the built console at `/console/` when `web/dist/index.html` exists, so `docker run` gives a judge the product.

## 2. Read first

- `AGENTS.md`
- `docs/spec/release3/README.md`
- `docs/spec/release3/P18_00_DESIGN.md` (§5, §6, §7.1, §11)
- `app/tracing.py`
- `app/orchestrator.py`: `run()` and `Deps.tracer_factory` only
- `app/api/routes_run.py`, `app/api/routes_cases.py`, `app/api/main.py`
- `app/llm/generator.py`
- `app/agents/evaluator.py` (the `derive` call)
- `app/data/queries.yaml`, `app/data/usl_model.py`
- `app/state.py` (case id from vendor id)

## 3. Deliverables

### 3.1 `app/runhub.py` (new): in-process run registry

```python
class RunRecord(BaseModel):          # internal
    run_id: str
    started_at: datetime
    finished_at: datetime | None
    state: Literal["running", "done", "error"]
    events: list[dict]               # TraceEvent.model_dump(mode="json"), in order
    response: dict | None            # RunResponse.model_dump(mode="json") when done
    error: str | None

class RunHub:
    def start(self, request: RunRequest) -> str                  # returns run_id; raises Busy if >= MAX_ACTIVE (2)
    def snapshot(self, run_id: str, start: int = 0) -> tuple[list[dict], RunRecord]
    def wait(self, run_id: str, after: int, timeout: float) -> bool   # Condition-based
    def list_recent(self, limit: int = 20) -> list[RunRecord]
```

- `start()` spawns a daemon thread that calls the **unchanged** `app.orchestrator.run(case, options=..., deps=Deps(tracer_factory=factory))`.
- `factory(run_id, mode)` returns `HubTracer(run_id, mode=mode, log_dir="logs", hub=self)`, a subclass of `Tracer`:
  - its `event()` calls `super().event()` (so the JSONL file is written exactly as today);
  - it then appends `evt.model_dump(mode="json")` and notifies.
- `start()` waits up to 10 s for the factory to be called, so it can return the real `run_id`.
- Retention:
  - keep the last 50 records;
  - drop older ones;
  - never delete trace files.
- Thread safety: one `threading.Condition`; no asyncio inside the hub.

### 3.2 `app/api/routes_stream.py` (new)

| Route | Behaviour |
|---|---|
| `POST /runs` | Same body as `POST /run` (`RunRequest`). **202** with `{run_id, events_url, status_url}`. 429 `ErrorResponse` "Two assessments are already running. Wait for one to finish." when busy |
| `GET /runs/{run_id}/events` | `text/event-stream`. Replays buffered events from `Last-Event-ID + 1`, or `?from=N`, or 0, then streams new ones. Message format below. Keep-alive comment every 10 s. Ends after `done` or `error`. 404 for an unknown run id |
| `GET /runs/{run_id}` | `{run_id, state, n_events, started_at, finished_at, response?, error?}` |
| `GET /runs` | Recent runs from the hub: `run_id`, `state`, `case_id` (from the `start_run` event), `started_at` |

SSE messages:

```
id: 17
event: trace
data: {"timestamp": "...", "agent_name": "PlannerAgent", "action": "model_call", ...}

event: done
data: {"run_id": "run-…", "status": "success", "case_id": "CASE-0007", "outcome": "ESCALATE", "execution_time_seconds": 131.4, "mode": {...}}

event: error
data: {"run_id": "run-…", "message": "…"}
```

- `POST /run` is unchanged: same contract, still synchronous. Judges' scripts and the clean-clone check use it.
- The SSE generator is `async` and polls the hub with `await asyncio.to_thread(hub.wait, ...)` in 1 s slices, so it never blocks the event loop.

### 3.3 `app/api/routes_evidence.py` (new): read-only data for the console

| Route | Returns | Source |
|---|---|---|
| `GET /registry/queries` | `[{id, description, systems, control_ids, params, sql}]`. `sql` is resolved for the current layer (USL table names in live USL mode; DuckDB names in sample mode) | `app/data/queries.yaml` via the existing registry loader |
| `GET /usl/model` | `{name, namespace, tables: [{name, description, primary_key, columns, foreign_keys}], catalogue_tokens}` | `app/data/usl_model.py` (`load_model()`, `compact_catalogue()`) |
| `GET /agents` | `[{name, trace_name, kind, lane, can, cannot}]` for the nine agents in the README "How it works" table | New constant in `app/api/agent_roster.py`. A test asserts it matches the README table row by row |
| `GET /evidence/nightshift` | The committed proof, **whitelisted fields only**: per lane `sent_model`, `response_model`, `routed_model`, `requested_mode`, `routed_mode`, `mode_coerced`, `receipt_id`, `latency_ms`, `tokens_in`, `tokens_out`; plus `timestamp`, `base_url_host` (host and port only) and the `deviations` details | `docs/evidence/nightshift_proof.json` |
| `GET /evidence/parity` | `{query_layer, source_mode, all_green, table_counts: [{table, expected, zetaris, ok}], rules: [{id, table, expr, pk}], invalid_by_table: [{table, zetaris, mirror, ok}], query_comparisons: {total, ok}, kev_checks: {total, ok}}`. The parity file records invalid keys **per table**, not per rule. Do not invent per-rule counts; the console says "Invalid rows on contract: CTR-30028" and lists the rules on that table | `docs/passes/P1-B_parity.json` plus `zetaris/dq_rules.yaml` |
| `GET /recordings` | Committed traces the console can replay: `[{run_id, kind, path, case_id, vendor_name, outcome, duration_s, recorded_at, mode, model_ids, n_events, n_model_calls, n_fallbacks, n_queries}]`. `kind` is one of `live_example` (`logs/examples/live/`), `live_eval` (`eval/results_live/*/traces/trace-run-*.jsonl`; never `trace-baseline-*`), `live_session` (`logs/examples/session/trace-run-*`) or `sample_example` (`logs/examples/sample_mode/`). `logs/examples/live_failed/` appears only with `?include_failed=true`, with `failed: true` | Files on disk, indexed once at startup |
| `GET /recordings/{run_id}` | `{meta, events}` | Same index. Run id must match `^run-[0-9a-f]{12}$` **and** be in the index. Never build a path from the request |

- **Vendor name for a recording:**
  - derive the vendor id from the case id with the inverse of `app/state.py`'s rule;
  - read `legal_name` with the DuckDB mirror's `Q_VENDOR_PROFILE`;
  - inline cases show "Inline submission".
  - This is a lookup, not branching on ids.

### 3.4 `app/api/routes_web.py` (new): serve the console

- If `web/dist/index.html` exists:
  - mount `web/dist` at `/console` (`StaticFiles(html=True)`);
  - add a catch-all `GET /console/{path:path}` that returns `index.html` for client routes;
  - `GET /` returns a 307 redirect to `/console/`.
- If it does not exist: `GET /` returns `{"console": "not built", "api_docs": "/docs", "classic_console": "python run.py ui"}`.
- API routes keep their paths.
- **Dev CORS:** when `ARBITER_DEV_CORS=1`, allow origin `http://localhost:5173` only.

### 3.5 Three new trace events (honest logging; additive)

| Event | Where | Fields |
|---|---|---|
| `<agent> model_request` | `app/llm/generator.py`, immediately before the provider HTTP call, only when a tracer is passed | `agent_name` = the same `agent_name` the following `model_call` uses; `status: success`; `input_summary: "purpose=<p> route=<r> attempt=<n> prompt_chars=<c>"`; `output_summary: "sent to <provider>"`; `provider`, `route`, `purpose` set; `model` null |
| `EvaluatorAgent contradiction_found` | `app/agents/evaluator.py`, after `derive(...)`, once for each contradiction **not already reported in this run** (key plus claim id) | `input_summary: "key=<key> control=<C09>"`; `output_summary: "vendor=<claim_value> record=<sor_value> system=<system> record_key=<record_key>"`; `target_agent: null`; `status: success` |
| `PolicyEngine decide` | `app/orchestrator.py`, after each `_decide(...)` (DECIDE_1 and DECIDE_2) | `input_summary: "facts=<n> contradictions=<m> precedents=<k>"`; `output_summary: "outcome=<O> tier=<T> failing=<C05,C09> unknown=<C05>"`; `status: success` |

- **Values that would contain vendor text.** Pass contradiction values through the existing `mask_secrets` (the tracer already does this). Truncate each value to 80 characters.
- **Committed traces.** Never edit existing committed traces. New events appear only in new runs.
- **Existing tests:**
  - Update any existing test that asserts an exact event sequence, adding the new events to its expectation, and list each one in the report.
  - Never delete an assertion.

### 3.6 Packaging

`.dockerignore`: keep `logs/*` but add `!logs/examples/` and `!logs/examples/**`, so recordings are in the image. `eval/results_live` is already included. Add a test that parses `.dockerignore` and asserts this.

## 4. Acceptance tests (marker `p18a`)

| Id | Test |
|---|---|
| P18A-T1 | Sample mode, TestClient: `POST /runs` with example 2's body returns 202 within 5 s. The SSE stream yields ≥ 20 `trace` events, then `done` with `outcome == "ESCALATE"` and a `case_id` that `GET /cases/{id}` returns |
| P18A-T2 | The streamed events equal the lines of `logs/trace-<run_id>.jsonl` (same `span_id`s, same order) |
| P18A-T3 | Resume: reconnecting with `Last-Event-ID: 9` yields events from index 10 onwards with no duplicates |
| P18A-T4 | Busy: with a monkeypatched slow `run`, a third concurrent `POST /runs` returns 429 with the `ErrorResponse` shape |
| P18A-T5 | Keep-alive: with a monkeypatched run that sleeps 12 s before its first event, the raw stream contains a `:` comment line before the first event |
| P18A-T6 | `GET /recordings` lists `run-83de5da137c0` as `live_example` and `run-257c86984507` as `live_eval` (vendor "Quillfeather Payroll Cloud Ltd", outcome ESCALATE), no `trace-baseline-*`, and no `live_failed` unless asked. `GET /recordings/run-../../etc` and an unindexed id both return 404 |
| P18A-T7 | `GET /registry/queries`: every id in `queries.yaml` is present with `systems`. The response contains no `{T.` placeholders |
| P18A-T8 | `GET /usl/model`: 10 tables; `vendor_alias.vendor_id` has a foreign key to `vendor.vendor_id` |
| P18A-T9 | `GET /evidence/nightshift` contains only whitelisted keys, recursively. With a temporary proof file containing `"Authorization": "Bearer canary-123"`, the response contains neither string |
| P18A-T10 | `GET /evidence/parity`: `all_green` true; `invalid_by_table` has `contract` with `CTR-30028` on both sides; `rules` has the 5 rules from `zetaris/dq_rules.yaml`; `query_comparisons.total == 416` |
| P18A-T11 | Static: with a temporary `web/dist/index.html`, `/` redirects to `/console/`, `/console/cases/CASE-0007` returns the HTML, and `/cases` still returns JSON. Without it, `/` returns the "not built" JSON |
| P18A-T12 | Trace events, sample mode, example 2: one `contradiction_found` (`key=residency.regions`, vendor EU, record US) and ≥ 1 `PolicyEngine decide` with `outcome=ESCALATE`. With a respx-mocked Nightshift (fixture from `tests/fixtures/`), every `model_call` is preceded by a `model_request` with the same `agent_name` and `purpose` |
| P18A-T13 | `.dockerignore` keeps `logs/examples/**` |
| P18A-T14 | `GET /agents` matches the README "How it works" table (names, lanes, can, cannot) |
| P18A-T15 | `check_trace --require-collaboration` still passes on a new sample-mode trace that contains the new events |

## 5. Definition of done

- `python scripts/tasks.py verify-pass --pass 18a` is green, and so is the full `verify`.
- `POST /run` behaviour and the six example outcomes are unchanged (the e2e tests prove it).
- The report lists every existing test that changed and why.

## 6. Claude Code prompt

```
/start-pass 18a
You are implementing P18-A of Arbiter Release 3: a non-blocking run API with live SSE trace streaming, read-only endpoints for the web console, three new honest trace events, and static serving of web/dist.
Read: CLAUDE.md; docs/spec/release3/README.md; docs/spec/release3/P18_00_DESIGN.md §5–§7.1 and §11; docs/spec/release3/P18A_STREAM_API.md; app/tracing.py; app/orchestrator.py (run() and Deps only); app/api/*.py; app/llm/generator.py; app/agents/evaluator.py; app/data/queries.yaml; app/data/usl_model.py; app/state.py.
Change no decision logic. POST /run stays synchronous and unchanged. Never edit committed traces.
Plan first: .cursor/plans/P18-A.md with files, interfaces and tests P18A-T1..T15. Wait for my approval.
Then tests first (marker p18a) → commit → implement until `python scripts/tasks.py verify-pass --pass 18a` is green.
Finish with docs/passes/P18-A_REPORT.md and docs/cursor-usage/P18-A.md (tool: Claude Code); push p18a-stream-api; open a PR into main; delete .cursor/ACTIVE_PASS; stop.
```
