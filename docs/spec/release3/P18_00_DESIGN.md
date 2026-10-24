# P18 design: the Arbiter console

Shared by lanes 18b, 18c and 18d (and by 18a for the API contract). The design is binding. If something here does not fit the data, set the phase to `blocked` and ask; do not improvise a different look.

## 1. What the console is for

- **Who uses it:**
  - a TPRM analyst deciding whether a SaaS vendor may touch customer data;
  - the TPRM lead who signs off exceptions;
  - this week, hackathon judges watching a video or running `docker run`.
- **Primary job:** start an assessment and *watch the agents reach the decision*: what each one asked, what came back, where they disagreed, what was sent back, and why the policy ruled as it did. Then act on the decision.
- **What it must prove at a glance:** this is a reasoning architecture, not a chatbot.
  - Models plan, read and challenge.
  - Systems of record are checked through Zetaris.
  - A policy rules.
  - Humans sign.
  - Every step is logged and replayable.

## 2. The concept: the bench

An arbiter hears two sides. The run view is laid out that way, and the layout *is* the information:

```
                 ┌───────────── Reasoning engine ─────────────┐
                 │ Meterless Nightshift  ─▶  Nemotron models   │      USL model (Zetaris)
                 └────────────────────────────────────────────┘
 The vendor's word          The bench (agents)                   The company's records
 ┌──────────────┐  Scout  ┌─────────┐      ┌───────────┐       ┌────────────────────┐
 │ Answers      │──guard──│ Evidence│─────▶│ Evaluator │       │ Procurement        │
 │ Documents    │   ▌     └─────────┘      └───────────┘       │ Contracts (CLM)    │
 │ Components   │   ▌         ▲  Planner ◀╌╌╌╌ sent back       │ Service desk (ITSM)│
 └──────────────┘   ▌         └──┘                             │ Watchlist (GRC)    │
                              Challenger ╌╌▶ Planner           │ CISA KEV           │
 ──────────────────────────────── The ruling ────────────────────────────────────────
   Policy engine  ─▶  Memory (H-MEM)  ─▶  Reporter  ─▶  Signed contract  ─▶  Next action
```

- **Left: the vendor's word.** Ochre. This is untrusted: questionnaire answers, documents, declared components, from the trust portal or from an inline submission. Every item passes the Scout guard gate before an agent reads it.
- **Right: the company's records.** Teal. These are the systems of record, reached through the Zetaris USL `vendor_risk` (or the DuckDB mirror in sample mode).
- **Centre: the bench.** The agents. Forward work flows left to right. Send-backs are dashed red arcs that go *backwards*, so a judge sees the loops.
- **Top: the reasoning engine.** Model calls go up to Nightshift, and the Nemotron model that served each call appears as its own node the first time it is used.
- **Bottom: the ruling.** The deterministic policy, then memory, the brief, the signed contract and the next action.
- **The memorable moment.** When the Evaluator finds that a claim and a record disagree, a clash card hangs from the Evaluator. Two red threads run to it, one from the vendor's answer on the left and one from the record on the right. Nothing else in the console is red unless something failed, was blocked, or was sent back.

The canvas starts **empty**:
- only the faint outlines of the three columns, the two bands and the words "Pick a vendor to start an assessment";
- nodes appear the first time an event touches them, so the graph grows with the run;
- a run that never touches CISA KEV never shows the KEV node.

## 3. Tokens

One light theme. Paper and ink suit evidence and rulings, and they record cleanly on video. Do not add a dark theme in this release.

### 3.1 Colour (all text colours ≥ 4.5:1 on every background below; verified)

| Token | Hex | Use |
|---|---|---|
| `paper` | `#F2F4F6` | App background (cool, not cream) |
| `sheet` | `#FFFFFF` | Panels, cards, nodes |
| `well` | `#E9EDF1` | Canvas background, table stripes, inactive chips |
| `ink` | `#16202B` | Text, primary buttons, the policy and ruling |
| `graphite` | `#56616D` | Secondary text |
| `hairline` | `#D3DAE1` | Borders and idle edges (never text) |
| `record` | `#0B6A70` | Systems of record, Zetaris, verified facts |
| `claim` | `#8F5600` | The vendor's word: answers, documents, components; claims not yet verified |
| `reason` | `#3D45A6` | Model calls, Nightshift, Nemotron |
| `clash` | `#B3261E` | Contradictions, failed controls, blocked content, send-backs, errors |
| Outcomes | APPROVE `#1C7444`, APPROVE_WITH_CONDITIONS `#3F6B12`, REQUEST_INFO `#8F5600`, ESCALATE `#A84A05`, DECLINE `#B3261E` | Outcome text, badge borders, the ruling stamp |

Tints for fills are the same hue at 8% on `sheet` (for example `record` at 8% behind a record node). No gradients. No glows except the one active-node treatment in §7.

### 3.2 Type

Self-hosted with `@fontsource` packages, so the console works offline and inside Docker with no network.

| Face | Role |
|---|---|
| **Public Sans** (400, 500, 600, 700) | Everything in the interface. The US Web Design System face: institutional and plain, right for a compliance tool |
| **Source Serif 4** (400, 600) | Only where Arbiter *rules or writes*: the ruling headline, the brief's sentences, drafted messages, the dossier. A judge should feel the change of voice from machine activity to written determination |
| **IBM Plex Mono** (400) | Only real identifiers: run ids, case ids, request ids, receipt ids, hashes, query ids in Technical details. Never decorative labels |

- **Scale:** 13 / 15 / 17 / 21 / 28 / 40 px. Body text is 15/24.
- **Measure:** brief and draft text ≤ 72 characters per line.
- **Weights:** 600 for node titles and table headers, 700 only for the ruling headline.

### 3.3 Space, shape, depth

- **Spacing:** a 4 px base; 8 / 12 / 16 / 24 / 32 / 48.
- **Radius encodes kind:**

  | Element | Radius |
  |---|---|
  | Agents (bench nodes) | 10 px |
  | Data sources | 4 px (record-like) |
  | Reasoning-engine nodes | Full pill |
  | The ruling stamp | 2 px |
  | Panels | 8 px |

- **Depth:** one shadow only, for floating things (drawer, popover, the ruling card): `0 8px 24px rgba(22,32,43,0.12)`. Cards on the page have a hairline border and no shadow.

## 4. Copy rules

- **Sentence case everywhere.**
  - No all-caps labels.
  - No eyebrow labels above headings.
  - No "A · B · C" meta strings: use a short sentence, or separate cells.
  - No "→" appended to buttons.
- **Name things by what the analyst understands.** Examples: "Contracts (CLM)", not `clm`; "Sent back for incident and contract evidence", not `needs_revision`.
  - Codes (C06, Q_VENDOR_INCIDENTS, CHALLENGE_UNCORROBORATED_CLAIM) appear only as secondary text or in Technical details.
- **Buttons say what happens:**

  | Button | Feedback |
  |---|---|
  | "Start assessment" | – |
  | "Open the case" | – |
  | "Approve contract" | Toast: "Contract approved" |
  | "Download dossier" | – |
  | "Replay decision" | Result: "Decision replays identically" or exactly what differs |

- **Errors say what happened and what to do.** For example: "Nightshift did not answer within 180 s. The Planner used its deterministic fallback; the run continues."
- **Empty states invite the next action.** For example: "No cases yet. Start an assessment to see the agents work."
- Reuse the outcome words and meanings from `app/labels.py`, served by the API (`/cases/{id}` and `/questions`). Never re-type them in the frontend.

## 5. Modes and honesty labels (mandatory)

A permanent mode chip at the top right of the run view and the Case page. Its text comes only from the event's `mode` field, `/health`, or the recording's metadata:

| Situation | Chip text | Extra |
|---|---|---|
| `mode.data == "zetaris"` and model calls with `provider == "meterless"` | "Live: Zetaris USL and Meterless Nightshift" | Elapsed time is real time |
| `mode.data == "duckdb"` and `llm == "offline"` | "Sample mode: DuckDB mirror, deterministic fallback" | Plus "Paced for viewing" while the pacer slows playback (§6) |
| A recording | "Recorded live run, 24 Oct 2026 05:10 UTC" (from the first event's timestamp) | Plus the trace file path in the inspector, and a speed control |
| Mixed (some calls fell back) | Live chip plus a clash-coloured count "2 fallbacks" | Each fallback is marked on its node |

- **Never animate a model node in sample mode.** The reasoning band shows one node, "Deterministic fallback (no model call)", in `graphite`.
- **Never show a Nemotron node unless an event's `model` field names it.**
- If any receipt has `app_policy.mode_coerced == "True"`, the Nightshift node carries a small note: "Lane coerced to auto by a Nightshift app rule". The inspector links to `docs/evidence/nightshift_deviations.md` on GitHub.

## 6. Playback: live, paced and recorded

All three paths feed **one** pure reducer: `reduce(state, event) -> state` (`web/src/run/reducer.ts`). The only difference between them is when events arrive.

- **Live:** events arrive over SSE (`GET /runs/{run_id}/events`, P18-A) and are applied as they come.
- **In-flight indicator.** A `model_request` event (P18-A) starts a pill on the edge to Nightshift. The pill counts seconds ("Planner is waiting for Nemotron: 23 s") and stops when the matching `model_call` arrives. Live model calls take 10–45 s, so this is what keeps the screen alive.
- **Paced:** sample mode delivers all events in under a second. The pacer holds each event for a minimum dwell before applying the next, then shows "Skip to result":

  | Event | Dwell |
  |---|---|
  | `transition` | 350 ms |
  | `plan`, `evaluate`, `challenge`, `request_replan` | 700 ms |
  | query events | 250 ms |
  | `guard_segment` | 40 ms (batched visually) |
  | everything else | 150 ms |

  A sample run therefore plays in about 15–25 s.
- **Recorded:** `GET /recordings/{run_id}` returns committed live traces (P18-A). Default speed is 4×, using the real gaps between timestamps, capped at 3 s per gap. The user can choose 1×, 4× or 16×, or step to the next moment.
  - A *moment* is any event with a target agent, a non-success status, a `contradiction_found`, a `decide`, or a `complete_run`.
- **Scrubber.** A timeline at the foot of the canvas, with ticks for moments (red ticks for send-backs and fallbacks). Dragging re-runs the reducer from zero to that index. The reducer is pure and cheap (a live run is about 100 events).

## 7. The bench graph

React Flow (`@xyflow/react` 12). Node positions are fixed: the layout is semantic, so do not use automatic layout here. Dagre is used only for the USL ERD on the Sources page.

### 7.1 Nodes

Canvas 1200×720 logical units, `fitView` with padding. The left column is x 0–220, ScoutGuard x 260, the bench x 400–760, the records column x 920–1160, the reasoning band y 0–90 and the ruling band y 620–720.

| Node id | Label | Second line (role) | Kind | Appears on |
|---|---|---|---|---|
| `vendor.answers` | Questionnaire answers | The vendor's word | vendor | First query of `Q_SUBMISSION_ANSWERS`, an inline submission, or the first `guard_segment` with `ans-` |
| `vendor.documents` | Documents | The vendor's word | vendor | `Q_SUBMISSION_DOCUMENTS`, or a `guard_segment` with `doc-` |
| `vendor.components` | Declared software | The vendor's word | vendor | `Q_VENDOR_COMPONENTS` or `Q_KEV_BY_PRODUCTS` |
| `guard` | Scout guard | Screens vendor text | gate | First `guard_segment` |
| `planner` | Planner | Chooses what to check | agent | `PlannerAgent` |
| `evidence` | Evidence | Gathers and extracts claims | agent | `EvidenceAgent` |
| `evaluator` | Evaluator | Checks claims against records | agent | `EvaluatorAgent` |
| `challenger` | Challenger | Attacks the decision | agent | `ChallengerAgent` |
| `rec.procurement` | Procurement | System of record | source | A query whose systems include `procurement` |
| `rec.clm` | Contracts (CLM) | System of record | source | `clm` |
| `rec.itsm` | Service desk (ITSM) | System of record | source | `itsm` |
| `rec.grc` | Watchlist (GRC) | System of record | source | `grc_watchlist` |
| `rec.kev` | CISA KEV | Public catalogue | source | `cisa_kev` |
| `usl` | USL vendor_risk | Zetaris semantic layer | source | `usl_catalogue`, or the first `backend=zetaris` query. In sample mode: "DuckDB mirror" |
| `engine` | Meterless Nightshift | Routes every model call | engine | First `model_request` or `model_call`. In sample mode: "Deterministic fallback (no model call)" |
| `model:<id>` | Human name from `winning_route.label`, else the id (for example "Nemotron 3.5 Super VL 120B") | "nvidia" | engine | First `model_call` whose `model` is that id |
| `policy` | Policy engine | Decides; never a model | ruling | `decide` or `redecide` or `transition DECIDE_1` |
| `memory` | Memory (H-MEM) | Lead-approved precedents | ruling | `memory_check` |
| `reporter` | Reporter | Writes the brief | ruling | `ReporterAgent` |
| `contract` | Signed contract | Scout execution contract | ruling | `execute_action` |
| `outcome` | The ruling | (outcome word) | ruling | `complete_run` |

**Mapping query systems to nodes.**
- `trust_portal` maps to the `vendor.*` node for that query.
- The other systems map to `rec.*`.
- The mapping comes from `GET /registry/queries` (P18-A), never from a hard-coded list in the frontend. The table above names the expected results so the tests can check them.

**Node anatomy (`sheet` card, 176×64):**
- a lucide icon;
- the label (600 weight);
- the role (13 px graphite);
- a **state ring** on the left edge (4 px), one of:
  - idle `hairline`;
  - active: kind colour, with a slow 1.6 s pulse;
  - done: kind colour, solid;
  - fallback: `claim` with a "fell back" tag;
  - blocked or failed: `clash`.
- A count badge (for example "3 plans", "16 claims", "4 queries") appears after the first event.

**Active node treatment.** Only the node currently working gets the Aceternity *Glowing Effect* border, recoloured to its kind colour at 40% and disabled under reduced motion. Exactly one node glows at a time; that is the "where are we now" cue.

### 7.2 Edges

| Edge | Style | Label (hover pill; persistent count) |
|---|---|---|
| Forward work (`target_agent` set and status success) | Solid 1.5 px, kind colour of the target | Plain sentence plus count, for example "Plan with 7 queries" |
| Query: `evidence`/`planner` → source | Solid `record` (or `claim` for vendor nodes) | "Q_VENDOR_CONTRACT: 1 row, 1.7 s, request id 2cc0…" |
| Agent → `engine` → `model:*` | Solid `reason` | "Plan (deep lane): 14.2 s, 3,368 → 3,148 tokens, receipt rcpt_req_ltd0d684" |
| **Send-back**: Evaluator → Planner (`evaluate` with `needs_revision`) | **Dashed `clash`, routed above the bench** | "Sent back for incident and contract evidence (C06, C09)", plus a loop count "1 of 2" |
| **Re-plan**: Challenger → Planner (`request_replan`) | **Dashed `clash`, routed below the bench** | "Challenger: an approval rests on an uncorroborated claim. Re-plan (1 of 1)" |
| Clash threads (`contradiction_found`) | Dotted `clash` from the vendor node and from the record node to the clash card | "Residency: vendor says EU, contract CTR-30007 says US" |
| Guard | `claim` → `guard` → `evidence`; blocked segments in `clash` | "16 answers screened, 16 passed" or "1 document blocked (score 0.92)" |
| Ruling chain | Solid `ink` | "34 facts, 1 contradiction, tier T1" and so on |

- **Travel.** When an event fires, a 6 px dot travels along its edge. Its duration is min(latency, 1200 ms) × playback speed, and it is replaced by a 200 ms highlight under reduced motion.
- **Thickness.** Edges thicken slightly with use (1.5 → 3 px over 10 traversals), so the busiest paths are visible at the end.

### 7.3 The clash card

- **Live and sample runs.** It is anchored under the Evaluator and created by `contradiction_found` events (P18-A). It shows each contradiction as:
  - claim: the vendor's value and the answer it came from;
  - record: the system's value, its record key and its Zetaris request id;
  - the control it affects, in words.
- **Recorded traces from before P18-A** have no `contradiction_found` events. The card is created from the `evaluate` summary ("1 contradictions") with the text "1 contradiction found; details in the case record". Do not invent the values.

### 7.4 The ruling

- **When:** on `complete_run`, the single orchestrated moment of the console.
- **The stamp:** the ruling card rises over the ruling band (240 ms) with the outcome word in its colour as a 2 px-radius stamp.
  - The Magic UI *Border Beam* runs once around the card (1.2 s), then stops.
  - Under reduced motion it appears instantly.
- **The headline:** the brief headline in Source Serif 4. Fetch it with `GET /cases/{case_id}`; the case id comes from `start_run` or the SSE `done` event.
- **Facts:** time taken, model calls, Zetaris queries and fallbacks.
- **Buttons:** "Open the case" (primary) and "Watch again".

### 7.5 Around the canvas

- **Stage rail** (top; the run genuinely is a sequence, so numbered steps are right):
  - Intake, Plan, Gather, Evaluate, Decide, Memory, Challenge, Report, Contract, Execute, Done, from `transition` events.
  - A step visited more than once shows "×3".
  - A `SAFE_ESCALATE` turns the rail `clash` from that point.
- **Right panel (380 px), two tabs:**
  - **Activity:** one plain sentence per event (§8), grouped under stage headings, auto-scrolling, with the newest at the bottom. Guard segments collapse to one line per batch. Clicking a line selects its node or edge.
  - **Inspector:** the selected node or edge.
    - Agents: what it can and cannot do (from the README agents table, served by `GET /agents`, P18-A), then each of its events in this run.
    - Model calls: lane requested, model served, coerced or not, latency, tokens, receipt id, `no_think`.
    - Queries: what the query is for, the systems, rows, latency, the Zetaris request id, and the SQL resolved against the USL (from `/registry/queries`).
    - Policy: tier, outcome, failing controls in words.
    - At the foot: "Show the trace line", which reveals the raw JSON of the selected event.
- **Behaviour strip** (bottom). Six counters that answer the judges' brief directly. Each counter is a button that filters the Activity tab:

  | Counter | Counts |
  |---|---|
  | Critiques | `critique`, `evaluate`, `challenge` |
  | Sent back | `needs_revision`, `request_replan` |
  | Retries and fallbacks | `retry_count > 0`, `retrying`, `fallback`, `*_fallback` |
  | Shared context reads | `usl_catalogue`, `memory_check`, `retrieve_precedents` |
  | Model calls on Nemotron | `model_call` with a model |
  | Zetaris queries | `query_zetaris`; in sample mode "Mirror queries" |

  Numbers tick up with Magic UI *Number Ticker*, or plain under reduced motion.

## 8. Plain-English activity lines

`web/src/run/describe.ts`: `describe(event, registry) -> {text, detail?, tone}`. It must produce a sentence for **every** (agent, action) pair found in the committed traces (P18-B test T4), and a generic fallback for anything new. Examples from the live trace `run-83de5da137c0`; the `contradiction_found` and `decide` lines show what the new P18-A events will produce for Quillfeather:

| Event | Sentence |
|---|---|
| `Orchestrator start_run` | Started the assessment of CASE-0003 with a 600 s budget. |
| `PlannerAgent usl_catalogue` | The Planner read the semantic layer's model (304 tokens). |
| `PlannerAgent model_request` | The Planner asked Nemotron for a plan (deep lane). |
| `PlannerAgent model_call` (success) | Nemotron 3.5 Super VL answered in 14.2 s with a valid plan. |
| `PlannerAgent plan_corrected` | The policy re-added 3 required checks the model left out. |
| `PlannerAgent plan` | The Planner sent 7 queries to Evidence. |
| `data query_zetaris` | Contracts (CLM): 1 row in 1.7 s through Zetaris. |
| `ScoutGuard guard_segment` (batched) | The Scout guard screened 16 answers: all passed. |
| `EvidenceAgent extract_claims` | Evidence extracted 16 claims from 15 answers, each with a quote. |
| `EvaluatorAgent evaluate` (`needs_revision`) | The Evaluator sent the plan back: incident history and the contract are missing. |
| `EvaluatorAgent contradiction_found` | The vendor says EU; the contract system says US. |
| `PolicyEngine decide` | The policy ruled Escalate at tier T1: data residency failed. |
| `ChallengerAgent request_replan` | The Challenger asked for a re-plan: an approval rests on a claim nothing corroborates. |
| `PlannerAgent model_call` (fallback) | Nightshift returned an error (HTTP 502), so the Planner used its deterministic fallback. |
| `ActionExecutor execute_action` | The approval was written to the outbox under signed contract ctr-2326…. |
| `Orchestrator complete_run` | Decided Approve in 2 min 39 s. |

**Rules:**
- Control and query codes go in `detail`, never at the start of `text`.
- Numbers come from the event.
- If a summary cannot be parsed, fall back to "<Agent> <action>: <output_summary>".

## 9. Parity checklist (every Streamlit capability must exist in the web console, or stay reachable in Streamlit at Gate A)

| Streamlit (today) | Web page | Lane |
|---|---|---|
| New assessment: existing vendor picker | Assess: vendor list (`GET /vendors`) with search; Start assessment | 18b |
| New assessment: questionnaire form (16 questions from `/questions`, Yes/No/Not answered plus How?, document and component rows, presets, client validation, JSON under Advanced) | Assess: New vendor tab | 18d |
| Run progress | The live run view (replaces the spinner) | 18b |
| Cases: totals per outcome, waiting for approval, filters by outcome and tier, sort by residual risk, open case | Cases | 18c |
| Case header: outcome label and meaning, tier, residual risk, confidence sentence with unverified controls | Case: Decision | 18c |
| Brief headline, why-points, claim-versus-record cards (mismatch in red), KEV point | Case: Decision | 18c |
| Next action: recipient, subject, editable body, Copy, Download .txt | Case: Decision | 18c |
| Contract approval (role, name, rationale ≥ 30 characters, Approve or Reject) and the executed or outbox state | Case: Decision | 18c |
| Controls in business terms; what would change the decision; precedents considered | Case: Evidence | 18c |
| Agent timeline in words; workload sentence | Case: Agent activity (the bench, replaying `/cases/{id}/trace`) | 18c (uses 18b's run view component) |
| Dossier download (HTML and Markdown) | Case: Audit trail | 18c |
| Replay | Case: Audit trail ("Replay decision", shows the human override after P19) | 18c |
| Technical details (reason codes, control table with evidence chips, contradictions, counterfactuals, contracts, raw JSON) | Case: Technical details | 18c |
| Sources and semantic layer (data mode, ERD of 10 tables with FKs, descriptions, row counts, DQ rules) | Sources (React Flow plus dagre ERD; DQ table) | 18d |
| Review (lead or analyst review form, dry run for precedent eligibility) | Review (also reachable from the Case page) | 18d |
| Precedents (list, status, feedback) | Memory | 18d |
| Audit (recent events, verify chain) | Audit | 18d |
| Evaluation (offline and live summaries; this instance's activity) | Evaluation (`/eval/latest` from P19) | 18d |
| Sidebar provider proof (Nightshift status, URL with token hidden, served models, last receipt) | Provider (status from `/health`, proof from `/evidence/nightshift`, recent receipts from traces) | 18d |

## 10. Components

Base: **shadcn/ui** (Radix), restyled to the tokens. Effects come from the 21st.dev and Aceternity plugins you have installed in Claude Code. **Use at most these, only where listed, recoloured to tokens:**

| Component | Source | Where | Why |
|---|---|---|---|
| Sidebar | Aceternity *Sidebar* (or the shadcn sidebar) | App navigation | Collapsible rail; labels always visible at ≥ 1280 px |
| Glowing Effect | Aceternity | The single active bench node | "Where are we now" |
| Border Beam | Magic UI (21st.dev) | The ruling card, once | The one orchestrated moment |
| Number Ticker | Magic UI (21st.dev) | Behaviour strip | Counts visibly change as agents work |
| Timeline | Aceternity *Timeline* | Case: Audit trail (contracts, approvals, replays) | A real sequence |
| Tracing Beam | Aceternity | Case: Decision, beside the brief and why-points while scrolling | Ties long reasoning to its place |
| Animated Tabs | Aceternity | Case page tabs | Shows which view you are in |

**Do not use:**
- backgrounds (Aurora, Beams, Meteors, Sparkles, Shooting Stars, Vortex);
- 3D cards;
- text effects (Typewriter, Encrypted Text);
- the Globe;
- dark or gradient defaults.

If a component cannot be recoloured to the tokens, leave it out.

## 11. Engineering

- **Stack:**
  - Vite and React 19 with TypeScript (strict);
  - Tailwind CSS 4 with the tokens as CSS variables;
  - shadcn/ui;
  - `@xyflow/react` 12;
  - `motion` (Framer Motion);
  - TanStack Query;
  - React Router (base path `/console/`);
  - zod for runtime validation of SSE payloads;
  - lucide-react;
  - `@fontsource` packages;
  - Vitest with Testing Library;
  - ESLint.
  - Pin exact versions and commit `package-lock.json`. Requires Node ≥ 20.19 (check with `node -v`).
- **Types:**
  - `npm run gen:api` writes `web/src/api/schema.d.ts` from FastAPI's `/openapi.json` (`openapi-typescript`).
  - The `TraceEvent` type is generated from `docs/trace_schema.json` (`json-schema-to-typescript`).
  - Both generated files are committed. A Vitest test fails if a field the reducer reads is missing from the generated type.
- **Folders:**

  | Folder | Contents | Owner |
  |---|---|---|
  | `web/src/app` | Shell, router, providers | 18b |
  | `web/src/design` | Tokens CSS, fonts | 18b |
  | `web/src/api` | Client, SSE hook, generated types | 18b |
  | `web/src/run` | Reducer, describe, pacer, counters | 18b |
  | `web/src/graph` | Nodes, edges, layout | 18b |
  | `web/src/ui` | Component kit | 18b creates; 18c and 18d add files only |
  | `web/src/pages/<page>` | Pages | Per §9 |
  | `web/src/features/<area>` | Page-specific components | Per §9 |

- **Serving:**
  - `npm run build` writes `web/dist/` with base `/console/`.
  - FastAPI serves it at `/console/` and redirects `/` to it (P18-A `routes_web.py`).
  - `web/dist/` is committed.
  - `npm run build` also writes `web/dist/.source-hash`: a sha256 of `web/src/**`, `index.html`, `package-lock.json` and the Vite config. `tests/unit/web/test_dist_fresh.py` fails if it does not match the source.
- **Dev:** `npm run dev` on port 5173, proxying `/runs`, `/cases`, `/health` and the rest to `http://localhost:8000`.
- **Security in the browser:**
  - The console never sees a token: the API never returns one.
  - Provider metadata is rendered from a **whitelist** of keys:
    - `requested_model`, `routed_model`, `receipt_id`, `decision_id`, `mode`;
    - `winning_route.label`, `winning_route.model`;
    - `app_policy.requested_mode`, `app_policy.routed_mode`, `app_policy.mode_coerced`;
    - `cost.actual_usd`, `no_think`.
  - A test renders a payload containing `Authorization` and `METERLESS_RUNTIME_TOKEN` canaries and asserts that neither string is in the DOM.
- **Integrity:**
  - The frontend never branches on vendor ids, case ids or scenario codes.
  - It never reads `output_examples/`, `input_examples/expected.json` or `data/evals/`.
  - `scripts/check_hardcoding.py` scans `web/src` (P18-B).
  - Recordings are labelled as recordings everywhere (§5).
- **Quality floor:**
  - Keyboard: React Flow nodes are focusable; Enter opens the inspector.
  - Visible focus rings in `ink`.
  - `prefers-reduced-motion` respected.
  - Works at 1280×720 (the video) and 1440×900.
  - Below 1024 px the run view stacks the canvas above the Activity tab.
  - Lighthouse accessibility ≥ 90 on Cases and Case.

## 12. Screens (wireframes)

**Assess** (default route `/console/`):

```
┌ rail ┐┌ Assess a vendor ─────────────────────────────────────────── mode chip ┐
│Assess││ [Existing vendor] [New vendor]    search ▢                           │
│Cases ││ Quillfeather Payroll Cloud Ltd   software, high criticality  [Start]  │
│Memory││ Pellucid Forms Ltd               …                          [Start]  │
│Source││ ─────────────────────────────────────────────────────────────────── │
│Provid││ Recorded live runs                                                   │
│Audit ││ Quillfeather: Escalate, 2 min 11 s, 24 Oct 05:10 UTC        [Watch]  │
│Eval  ││ Pellucid: Approve, 2 min 39 s, 24 Oct 04:41 UTC             [Watch]  │
└──────┘└──────────────────────────────────────────────────────────────────────┘
```

**Run** (`/console/runs/:runId`, or `/console/recordings/:runId`): §2 diagram plus the stage rail on top, the Activity/Inspector panel on the right, and the behaviour strip and scrubber at the bottom.

**Case** (`/console/cases/:caseId`), with tabs Decision, Evidence, Agent activity, Audit trail and Technical details:

```
 Quillfeather Payroll Cloud Ltd                                   mode chip
 [ESCALATE stamp]  Tier T1   Residual risk 100   Confidence 75%: one control unverified (current SOC 2 or ISO 27001)
 ┌ Brief (serif) ──────────────────────────────┐ ┌ Next action ─────────────┐
 │ Escalate to the TPRM lead: the vendor says   │ │ To: TPRM lead            │
 │ EU, but its contract (CTR-30007) shows US.   │ │ Subject …                │
 │  claim card  ≠  record card                  │ │ body (editable, serif)   │
 │  • FortiOS: 15 known-exploited …             │ │ [Copy] [Download]        │
 └──────────────────────────────────────────────┘ │ Contract: pending lead   │
                                                  │ [Approve contract]       │
                                                  └──────────────────────────┘
```

**Cases:** a one-sentence summary ("7 cases. 3 need the TPRM lead, 1 is waiting for the vendor."), filter chips with counts, then a table sorted by residual risk with outcome badges. Not a row of big-number tiles.
