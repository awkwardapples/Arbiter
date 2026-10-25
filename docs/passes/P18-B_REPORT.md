# P18-B report: web console foundation and the live run view

Lane `18b`, branch `p18b-run`. Plan: `.cursor/plans/P18-B.md`. Built in Claude Code (Opus 5.5). Both parts are in PR #34 into `p18-console`. You asked for part 2 to go onto that PR instead of a second one.

## What was built

### Part 1: foundation
- **`web/`.** Vite 7, React 19, TypeScript (strict) and Tailwind 4, with every design §3 token in `@theme` (`src/design/tokens.css`). Fonts are self-hosted with `@fontsource`, Latin subsets for the interface faces. Built to `web/dist/` with base `/console/` and committed. `npm run build` also writes `dist/.source-hash`.
- **Shell (`src/app`).**
  - A rail with the seven pages. The logo sits on an `ink` tile because it is white on transparent.
  - A "Classic console" dialog that explains `python run.py ui`.
  - `PageHeader` and `HealthModeChip`, so every page carries the `/health` chip.
  - A router with every route in the spec. 18c and 18d replace the placeholder pages.
- **API (`src/api`).**
  - `client.ts` turns `ErrorResponse` into a typed `ApiError`.
  - `useRunEvents` wraps EventSource: native `Last-Event-ID` reconnects, zod checks on every payload, and passthrough for unknown fields.
  - TanStack Query hooks for the read routes.
  - Generated `trace.d.ts` and `schema.d.ts`; the latter was regenerated after P18-A merged.
- **Kit (`src/ui`).**
  - Restyled shadcn primitives: Button, Badge, Card, Tabs, Sheet, Dialog, Tooltip, Table, Select, Input, Textarea, Toast.
  - Our own pieces: OutcomeBadge, OutcomeStamp, ModeChip, EmptyState, Identifier, Serif, Callout.
  - Effects: GlowingEffect, BorderBeam, NumberTicker, all honouring `useReducedMotion`.
  - `components.json`.
- **Toolchain.**
  - `tasks.py` gains `web-build` and `web-check`.
  - `check_hardcoding.py` scans `.ts`/`.tsx` under `web/src`, with `__tests__` exempt.
  - `scripts/capture_web.py` takes `--smoke`.
  - `scripts/gates/p18b.py` runs `npm run check`, the dist freshness test, and the smoke when Playwright and a console-serving API answer.

### Part 2: Assess and the run view
- **Assess (`pages/assess`).**
  - The vendor list (`GET /vendors`) with a search box and **Start assessment** (`POST /runs`, then `/runs/:runId`).
  - A New vendor tab that points to 18d's page.
  - **Recorded live runs** (`GET /recordings`), grouped by kind with live kinds first.
- **One pure reducer (`run/reducer.ts`)** implements design §7:
  - nodes appear on first touch, with state rings, counts and fallback tags;
  - edges carry counts, last labels and the travel trigger;
  - send-back and re-plan edges show "n of 2" and "n of 1";
  - clash items come from `contradiction_found`, or from the `evaluate` summary for older traces;
  - also tracked: the stage rail, in-flight model requests, pass §5 counters, the policy ruling and the outcome.
  - The system-to-node mapping comes from the registry (`run/registry.ts`). An unknown event changes only the activity feed.
- **`run/describe.ts`** has a specific sentence for every (agent, action, status) in the 57 committed traces and the new fixture, and a generic fallback for anything else.
- **`run/pacer.ts`** has three modes: live (pass-through), paced (the §6 dwell table, about 20 s for the 73-event sample trace) and recorded (real gaps capped at 3 s, at 1×, 4× or 16×). It also does pause, step to the next moment, seek and skip.
- **The bench (`graph/`).**
  - React Flow with fixed positions (`layout.ts`) and paths computed in the layout: send-backs route above the bench, re-plans below it, clash threads are dotted.
  - Nodes carry their size and handles, so React Flow never waits on measuring.
  - The single active node glows; the travelling dot is skipped under reduced motion.
  - Empty bands and the empty-canvas line.
- **`run/RunCanvas.tsx`** takes `source = live | recorded | events` and adds the stage rail, the canvas, Activity and Inspector tabs, the behaviour strip, the scrubber and the ruling card.
  - **Ruling card.** It shows the brief headline only when the case record's `trace_path` is this run's trace. Otherwise it says "This recording's case record is on the machine that ran it." It never invents a headline.
  - **Inspector.** Provider metadata is shown from the design §11 whitelist only, including in "Show the trace line".
- **Run pages.** `/runs/:runId` plays live, or paced when the first event says DuckDB and offline. `/recordings/:runId` plays recorded. The header shows the vendor, the mode chip, the elapsed time and the run id.

## Tests
| Id | Where | Result |
|---|---|---|
| P18B-T1–T3 | `web/src/run/__tests__/reducer.{live,eval,sample}.test.ts` | pass (counters exactly as §6) |
| P18B-T4 | `describe.test.ts`: 57 trace files plus the fixture; no line starts with a code; no generic line for a known pair | pass |
| P18B-T5 | `pacer.test.ts` (fake timers) | pass |
| P18B-T6 | `inspector.test.tsx`: canaries never in the DOM, before or after "Show the trace line" | pass |
| P18B-T7 | `runcanvas.motion.test.tsx`: no `[data-travel]` under reduced motion | pass |
| P18B-T8 | `clash.newschema.test.ts` on `fixtures/trace-run-5568c241c8e3.jsonl`, copied verbatim from a real sample run through `POST /runs` on `p18-console` at ca0ce51 | pass |
| P18B-T9 | `tests/unit/web/test_dist_fresh.py` | pass |
| P18B-T10 | `tests/unit/web/test_hardcode_web.py` | pass |
| P18B-T11 | `python scripts/capture_web.py --smoke`, run by the gate against `SAMPLE_MODE=true LLM_PROVIDER=offline python run.py serve` on this branch | pass |

Also tested: the client error shape, zod validation of every live trace line, the whitelist keys, the mode chip text, the `TraceEvent` fields the reducer reads, and the history scanner fix.

The smoke:
1. starts Quillfeather from Assess;
2. checks the stamp reads Escalate and the clash card mentions EU and US;
3. opens `/console/cases/CASE-0007`;
4. watches `run-257c86984507` at 16× from Recorded live runs, checking Escalate and "Recorded live run".

Screenshots: `docs/img/console_run_empty.png`, `console_run_mid.png`, `console_run_ruling.png`, `console_run_recorded.png` (1440×900).

## Deviations and decisions
1. **Branch:** `p18b-run`, not `p18b-run-view` (plan §6.1). `p18-console` was created from `main` and moved forward to `main` before PR #34.
2. **One PR, as asked:** part 2 went onto PR #34.
3. **Outcome words:** no route serves `app/labels.py`'s outcome words, so `ui/outcome.ts` formats the code in sentence case. "REQUEST_INFO" shows as "Request info", not "Request information". `outcomeWord()` takes a `label` once a route serves it.
4. **Edge and node components:** one `BenchEdgeView` serves the four edge types (`forward`, `sendback`, `replan`, `thread`), and one `BenchNodeCard` serves every non-clash node type. Styling varies by type, so separate files would only repeat code.
5. **Effects:** ported by hand after Aceternity's Glowing Effect and Magic UI's Border Beam and Number Ticker. They use the token colours and do nothing under reduced motion. No other library components are used.
6. **Recordings stay honest:**
   - Some `live_eval` recordings ran in DuckDB/offline mode. Assess lists them apart, under "Recordings of sample-mode runs".
   - Their chip reads "Recorded sample-mode run" and they play paced, not at millisecond gaps.
   - A recording's chip says "live" only when its events say Zetaris and Meterless.
7. **The in-flight pill** says "waiting for Nightshift", not "Nemotron". A `model_request` does not yet name the model that will serve it.
8. **Fallback count** follows `GET /recordings`: every event with `status == "fallback"`. One failed call plus its `plan_fallback` counts as 2.
9. **"Hide panel" toggle:** at 1280×720 the fixed 1200×720 canvas renders small, so the Activity/Inspector panel can be hidden. It is open by default, and selecting anything reopens it.
10. **Activity feed:** `data query_zetaris` lines repeat the agent's `query_run` line, so they are folded out of the feed. They still show under the Zetaris queries filter, and the counter counts them.
11. **Vitest timeout** raised to 20 s. The jsdom React tests took about 6.5 s on this WSL machine under load. No assertion changed.

## Files outside 18b's list (approved)
- `.secrets-allowlist`: `web/dist/assets/*` (generated vendor bundle; `web/src` stays scanned).
- `scripts/scan_secrets.py`: `scan_history` now tracks `--- a/<path>`, so a deleted file's lines are attributed to that file rather than the file before it. The parsing moved into `scan_patch()`, tested in `tests/unit/web/test_scan_history.py`. This clears the false positive from deleted `web/dist/assets/*` bundles for 18b, 18c and `p18-console`. Commit `fix(scanner): …`.
- `docs/img/console_run_*.png`: the spec's smoke writes these four files only.

## Known gaps and findings for other lanes
- **Backend, lane 18a or the data layer.** In sample mode, concurrent requests share one DuckDB connection. While a run is in progress, `GET /vendors` and `GET /health` can fail with `duckdb ResourceInUseException: connection is busy …` and answer 500. The console retries those reads three times with backoff, and the gate's probe retries too. The fix belongs in the backend: a cursor per request.
- **`routes_web.install` checks for `web/dist/index.html` once, at startup.** A server started while `dist` was being rebuilt serves "not built" until restarted.
- **Not watched yet:** a live run against Zetaris and Nightshift in the console (definition of done §7, attended). I watched a sample run and `run-257c86984507` recorded, in a browser, at 1440×900 and 1280×720.
- **Control names in words:** the API does not serve control titles, so the policy and clash text show control codes as secondary text ("Affects control C09").
- **Zetaris request id on the clash card:** `contradiction_found` does not carry it, so the card shows the record key only.

## Commands run
```
cd web && npm ci && npm run check
python scripts/tasks.py verify-pass --pass 18b
SAMPLE_MODE=true LLM_PROVIDER=offline PORT=8028 python run.py serve
python scripts/capture_web.py --smoke --base-url http://localhost:8028
```
