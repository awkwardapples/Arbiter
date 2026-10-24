# P18-B: web console foundation and the live run view (lane `18b`)

Branch `p18b-run-view` from `p18-console`. **Two PRs into `p18-console`:**
- **Part 1, by Sat 15:30 BST:** scaffold, shell and kit. Lane 18c starts from this.
- **Part 2, by Sun 12:00 GMT:** the run view.

Use Opus. This is the lane the video depends on.

## 1. Goal

- **Part 1:**
  - A Vite, React and TypeScript app in `web/`, built to `web/dist/`.
  - It is served by FastAPI at `/console/` (P18-A), with the design tokens, the app shell, the router (a placeholder for every page), the API client and the component kit.
  - The Python toolchain knows about it: build, check, hardcode scan, freshness test and the smoke script.
- **Part 2:**
  - The **Assess** page and the **run view** of `P18_00_DESIGN.md` §2 and §5–§8: the bench graph fills in as the agents work. It can play live (SSE), paced (sample mode) or recorded (committed traces).
  - The run view is a reusable component, `<RunCanvas>`, so the Case page (18c) can replay any case's trace.

## 2. Read first

- `CLAUDE.md`
- `docs/spec/release3/README.md`
- **`docs/spec/release3/P18_00_DESIGN.md` (all of it)**
- `docs/spec/release3/P18A_STREAM_API.md` §3: the API contract. Build against it; it may not be merged yet, so use committed traces as fixtures until it is.
- `docs/trace_schema.json`
- `logs/examples/live/trace-run-83de5da137c0.jsonl`
- `eval/results_live/20261024T045916036274Z/traces/trace-run-257c86984507.jsonl`
- `logs/examples/sample_mode/trace-run-a90b795279e5.jsonl`
- `ui/` (Streamlit), only to see what each page shows today

## 3. Part 1: foundation

| Deliverable | Detail |
|---|---|
| `web/package.json` | Scripts:<ul><li>`dev`: Vite on port 5173 with a proxy to 8000</li><li>`build`: `tsc -b`, then `vite build`, then `node scripts/source-hash.mjs`</li><li>`test`: `vitest run`</li><li>`lint`: ESLint</li><li>`check`: lint, typecheck, test and build</li><li>`gen:api`: `openapi-typescript http://localhost:8000/openapi.json -o src/api/schema.d.ts`</li><li>`gen:trace`: `json2ts ../docs/trace_schema.json > src/api/trace.d.ts`</li></ul>Exact pinned versions; commit `package-lock.json`. `engines.node` ≥ 20.19 |
| `web/vite.config.ts` | `base: "/console/"`; dev proxy for `/runs`, `/cases`, `/contracts`, `/health`, `/vendors`, `/questions`, `/memory`, `/audit`, `/eval`, `/registry`, `/usl`, `/evidence`, `/recordings`, `/agents`, `/openapi.json` |
| `web/src/design/tokens.css` | Every token from design §3 as CSS variables, wired into Tailwind 4 `@theme`. Fonts via `@fontsource/public-sans`, `@fontsource-variable/source-serif-4` and `@fontsource/ibm-plex-mono` |
| `web/src/app/` | Shell:<ul><li>a left rail with Assess, Cases, Memory, Sources, Provider, Audit and Evaluation</li><li>the Arbiter wordmark (`docs/img/arbiter_logo.png`, copied into `web/public/`)</li><li>the mode chip from `GET /health` (design §5)</li><li>a footer link "Classic console", which explains `python run.py ui`</li></ul>Router with routes: `/console/`, `/runs/:runId`, `/recordings/:runId`, `/cases`, `/cases/:caseId`, `/memory`, `/review/:caseId`, `/sources`, `/provider`, `/audit`, `/evaluation`, `/new`. Pages that 18c and 18d own are placeholders that link to the classic console |
| `web/src/api/` | `client.ts`: fetch with JSON, the `ErrorResponse` shape turned into a typed error, and the base URL from `import.meta.env` (default same origin). `useRunEvents(runId)`: an EventSource hook (built-in reconnect with `Last-Event-ID`; zod-validates each event; exposes `events`, `done`, `error`, `connected`). Generated `schema.d.ts` and `trace.d.ts`, committed |
| `web/src/ui/` | Kit, restyled shadcn primitives and our own pieces:<ul><li>shadcn: `Button`, `Badge`, `Card`, `Tabs`, `Sheet`, `Dialog`, `Tooltip`, `Table`, `Select`, `Input`, `Textarea`, `Toast` (sonner)</li><li>our own: `OutcomeBadge`, `OutcomeStamp`, `ModeChip`, `EmptyState`, `Identifier` (mono, copyable), `Serif`, `Callout`</li></ul>Effects from design §10 are wrapped here, for example `ui/effects/GlowingEffect.tsx` |
| `web/scripts/source-hash.mjs` | Writes `web/dist/.source-hash`: sha256 over the sorted paths and contents of `web/src/**`, `web/index.html`, `web/package-lock.json`, `web/vite.config.ts` and `web/tailwind`/`postcss` config if present |
| `scripts/tasks.py` ✎ | `web-build` (`npm ci` if `node_modules` is missing, then `npm run build`, in `web/`) and `web-check` (`npm run check`). Both print a clear message if `node` is missing |
| `scripts/check_hardcoding.py` ✎ | Add `web/src` to the scanned directories for `.ts`/`.tsx` files: the forbidden strings and `VND-\d{4}` / `CASE-\d+` / scenario literals. Exempt only `web/src/**/__tests__/**` |
| `tests/unit/web/test_dist_fresh.py` | `web/dist/index.html` exists. Every asset it references exists. `.source-hash` equals the hash recomputed in Python with the same algorithm |
| `scripts/capture_web.py` (new) | Python Playwright, lazily imported like `scripts/capture_ui.py`. `--base-url` (default `http://localhost:8000`), `--smoke`, `--out docs/img`. Sizes 1440×900 and 1280×720. Refuses to save a screenshot if any secret environment value appears in the page text, as `capture_ui.py` does. Part 1: only checks that the shell loads; part 2 extends it (§5) |
| `scripts/gates/p18b.py` | Runs `npm run check` in `web/` and the dist freshness test |

Commit `web/dist/` at the end of part 1. Open PR 1 into `p18-console`.

## 4. Part 2: Assess and the run view

| Deliverable | Detail |
|---|---|
| `pages/assess/` | **Assess** (`/console/`), wireframe in design §12:<ul><li>"Existing vendor": `GET /vendors` with a search box, one row per vendor (name, category, criticality) and **Start assessment**, which does `POST /runs {vendor_id}` and navigates to `/runs/:runId`</li><li>"New vendor": a placeholder for 18d's form</li><li>**Recorded live runs**: `GET /recordings`, live kinds first, grouped by kind, each with vendor, outcome badge, duration, time (UTC) and **Watch**, which navigates to `/recordings/:runId`</li></ul>Empty state if there are no vendors: "No vendors found. Is the API running in sample mode?" |
| `run/reducer.ts` | Pure `reduce(state, event) -> state` implementing the design §7 tables:<ul><li>nodes appear on first touch; node state rings and counts</li><li>edges with counts, last label and travel trigger</li><li>back-edges with loop counts</li><li>clash items</li><li>stage rail</li><li>in-flight model requests</li><li>counters (definition in §6 below)</li><li>the outcome</li></ul>Takes a `registry` (query id → systems) as a parameter. Unknown events: no crash; the event goes to the activity feed only |
| `run/describe.ts` | Design §8. Every (agent, action) in the committed traces has a specific sentence |
| `run/pacer.ts` | Design §6. Three modes: live (pass-through), paced (dwell table), recorded (scaled real gaps, capped at 3 s, speeds 1×/4×/16×). Pause, step to the next moment, seek to an index. The **Skip to result** button seeks to the end |
| `graph/` | React Flow canvas with fixed positions (design §7.1):<ul><li>custom node types `agent`, `source`, `vendor`, `gate`, `engine`, `ruling`, `clash`</li><li>custom edge types `forward`, `sendback` (routed above), `replan` (routed below), `thread` (dotted), with the travelling dot (respects reduced motion)</li><li>empty-canvas outlines and the line "Pick a vendor to start an assessment"</li></ul> |
| `run/RunCanvas.tsx` | Exported component: `<RunCanvas source={{kind:"live",runId} \| {kind:"recorded",runId} \| {kind:"events",events,mode}} />`. Contains the stage rail, canvas, right panel (Activity / Inspector), behaviour strip, scrubber and ruling card. 18c uses `kind:"events"` with `GET /cases/{id}/trace` |
| `pages/run/` | `/runs/:runId` (live, or paced when the first event's mode is DuckDB/offline) and `/recordings/:runId` (recorded). The header shows the vendor name, mode chip, elapsed time and the run id (Identifier) |
| Ruling card | Design §7.4. On `done` or `complete_run`, fetches `GET /cases/{case_id}` for the brief headline. **Open the case** goes to `/cases/:caseId`. For a recording, if the case is not in this instance's store, the card says "This recording's case record is on the machine that ran it" and shows the outcome from `complete_run`. It never invents a headline |
| Inspector | Design §7.5, with whitelisted provider fields only (design §11). "Show the trace line" reveals the event's raw JSON, with `provider_meta` filtered through the same whitelist |
| `scripts/capture_web.py --smoke` | With the API running in sample mode:<ol><li>open `/console/`;</li><li>start Quillfeather;</li><li>wait for the ruling;</li><li>assert the stamp reads "Escalate" and the clash card mentions EU and US;</li><li>open the case;</li><li>open Recorded live runs, watch `run-257c86984507` at 16×, and assert the ruling reads Escalate and the mode chip says "Recorded live run".</li></ol>Saves `docs/img/console_run_*.png` |

## 5. Counters (design §7.5), exact definitions

| Counter | Counts events where |
|---|---|
| Critiques | `action ∈ {critique, evaluate, challenge}` |
| Sent back | (`action == evaluate` and `status == needs_revision`) or `action == request_replan` |
| Retries and fallbacks | `action == model_call` or `action` starts with `query`, and (`status ∈ {fallback, retrying}` or `retry_count > 0`) |
| Shared context reads | `action ∈ {usl_catalogue, memory_check, retrieve_precedents}` |
| Model calls on Nemotron | `action == model_call` and `model` is set |
| Zetaris queries | `action == query_zetaris` |
| Mirror queries (sample mode) | `action == query_run` and `backend == duckdb` |

## 6. Acceptance tests (Vitest, plus Python for `web/dist`; marker `p18b` for the Python ones)

Fixtures are the committed files read from the repo with `fs` (paths relative to `web/`). Never copy, edit or hand-write a trace.

| Id | Test |
|---|---|
| P18B-T1 | Reducer on `logs/examples/live/trace-run-83de5da137c0.jsonl`:<ul><li>counters `{critiques: 5, sent_back: 2, retries_fallbacks: 1, shared_context: 5, model_calls: 5, zetaris: 12}`</li><li>one model node, `nvidia/nemotron-3.5-super-vl-120b-a12b`</li><li>the Planner node ends with a fallback marker</li><li>one `sendback` edge (Evaluator → Planner, count 1) and one `replan` edge (Challenger → Planner, count 1)</li><li>outcome APPROVE</li><li>stage rail Plan ×3</li></ul> |
| P18B-T2 | Reducer on `eval/results_live/20261024T045916036274Z/traces/trace-run-257c86984507.jsonl`:<ul><li>counters `{critiques: 6, sent_back: 3, retries_fallbacks: 1, shared_context: 4, model_calls: 3, zetaris: 14}`</li><li>a `rec.kev` node exists and its edge label mentions 15 rows</li><li>`sendback` count 2 and `replan` count 1</li><li>one clash item created from the `evaluate` summary with the "details in the case record" text (this trace predates `contradiction_found`)</li><li>outcome ESCALATE</li></ul> |
| P18B-T3 | Reducer on `logs/examples/sample_mode/trace-run-a90b795279e5.jsonl`:<ul><li>no `model:*` node</li><li>the engine node reads "Deterministic fallback (no model call)"</li><li>the data hub reads "DuckDB mirror"</li><li>`mirror: 14`</li><li>mode chip text is the sample-mode text</li></ul> |
| P18B-T4 | `describe()` returns a sentence that does not start with a code (regex `^[A-Z]{1,3}\d\|^Q_\|^[A-Z_]{6,}`) for every event in every file under `logs/examples/**` and `eval/results_live/**/traces/trace-run-*`. An unknown action returns the generic form |
| P18B-T5 | Pacer: a sample trace of 73 events in paced mode plays in 10–30 s (fake timers). Recorded mode at 4× plays `run-83de5da137c0` in ≤ 60 s. Skip-to-result reaches the final state |
| P18B-T6 | Whitelist canary: rendering the Inspector for an event whose `provider_meta` includes `Authorization: Bearer canary-xyz` and `METERLESS_RUNTIME_TOKEN: canary-abc` puts neither canary in the DOM |
| P18B-T7 | `<RunCanvas>` renders under `prefers-reduced-motion: reduce` with no travelling dots (no element with `data-travel`) |
| P18B-T8 | A new-schema event sequence (the P18-A `contradiction_found` from a sample run, captured once P18-A is merged and committed as a fixture under `web/src/run/__tests__/fixtures/`, generated by a real run, never hand-written) creates a clash card with both values and both threads |
| P18B-T9 (Python) | `tests/unit/web/test_dist_fresh.py` (part 1 deliverable) |
| P18B-T10 (Python) | The hardcode check scans `web/src`: a temporary file with `VND-0007` fails it; the real tree passes |
| P18B-T11 | `scripts/capture_web.py --smoke` passes. Run by the gate when Playwright and a server are available; otherwise the gate prints the exact command for you to run |

## 7. Definition of done

- `npm run check` is green, and `python scripts/tasks.py verify-pass --pass 18b` is green.
- The smoke test passes against `SAMPLE_MODE=true LLM_PROVIDER=offline python run.py serve` (with P18-A merged into `p18-console`).
- **You have watched, in a browser:**
  - a sample run;
  - `run-257c86984507` recorded;
  - one live run against Zetaris and Nightshift.
- The report includes three screenshots: empty, mid-run, ruling.

## 8. Claude Code prompt

```
/start-pass 18b
You are implementing P18-B of Arbiter Release 3: the web console foundation (part 1) and the live run view (part 2).
Read: CLAUDE.md; docs/spec/release3/README.md; docs/spec/release3/P18_00_DESIGN.md (all); docs/spec/release3/P18A_STREAM_API.md §3; docs/spec/release3/P18B_RUN_VIEW.md; docs/trace_schema.json; the three traces named in §2.
The design document is binding: tokens, type, copy rules, honesty labels, the fixed bench layout. Use the 21st.dev / Aceternity / Magic UI components listed in design §10 only, recoloured to the tokens; nothing else from those libraries.
Plan first: .cursor/plans/P18-B.md with the part 1 and part 2 file lists, component tree, reducer state shape, and tests P18B-T1..T11. Wait for my approval.
Part 1: tests first → scaffold → build web/dist → verify-pass 18b green → PR 1 into p18-console. Tell me, and wait for "continue".
Part 2: tests first → implement → run the smoke → screenshots → verify-pass 18b green → PR 2 into p18-console.
Finish with docs/passes/P18-B_REPORT.md and docs/cursor-usage/P18-B.md (tool: Claude Code); delete .cursor/ACTIVE_PASS; stop.
```
