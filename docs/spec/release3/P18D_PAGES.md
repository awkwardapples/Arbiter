# P18-D: Sources, Provider, New vendor, Memory, Review, Audit, Evaluation (lane `18d`)

Branch `p18d-pages` from `p18-console`, after P18-B part 1 and P18-A are merged there. One PR into `p18-console` by **Sun 25, 17:00 GMT**. Sonnet.

## 1. Goal

The remaining Streamlit pages (design §9), rebuilt in the console's design. Two of them carry sponsor marks and must be good, not just present:

- **Sources:** the Zetaris USL as a diagram.
- **Provider:** the Meterless connection and Nemotron proof. This is the Setup Guide's "Meterless provider connection" shot.

## 2. Read first

- `CLAUDE.md`
- `docs/spec/release3/README.md`
- `docs/spec/release3/P18_00_DESIGN.md` (§3–§5, §9–§12)
- `docs/spec/release3/P18A_STREAM_API.md` §3.3 (endpoints)
- `web/src/ui/**`
- `ui/intake.py`, `ui/sources_view.py`, `ui/provider.py`, `ui/screens.py` (Review, Precedents, Audit and Evaluation pages)
- `ui/presets.json`
- `app/api/routes_meta.py`, `app/api/routes_review.py`

## 3. Deliverables

| Page | Route | Content |
|---|---|---|
| **New vendor** | `/console/new` (also the second tab on Assess) | Port of `ui/intake.py`:<ul><li>criticality, category, data categories, countries, spend, patch SLA;</li><li>the 16 questions from `GET /questions`: Yes / No / Not answered plus an optional "How?" box, or a single text box for the non-yes/no questions;</li><li>document rows and component rows (editable table);</li><li>**Load an example vendor** (the two presets from a copy of `ui/presets.json` at `web/src/features/intake/presets.json`; say in the report that it is a copy);</li><li>client validation that names each problem next to its field;</li><li>an Advanced section with JSON paste.</li></ul>**Start assessment** builds the same `CaseInput` as Streamlit, calls `POST /runs {submission}` and goes to the run view |
| **Sources** | `/console/sources` | <ul><li>Data mode from `/health` ("Zetaris USL vendor_risk, live" or "DuckDB mirror, sample mode").</li><li>**USL diagram:** React Flow with **dagre** layout (left to right) from `GET /usl/model`. One node per table, with its description, primary key and columns (collapsible). Edges for declared foreign keys (solid `record`) and for the two documented undeclared joins, `contract` ↔ `vendor` on `clm_supplier_ref = supplier_ref` and `kev_vuln` matched in `Q_VENDOR_360` (dashed, labelled "joined in the query, not a declared key").</li><li>Clicking a table lists the registry queries that read it (from `GET /registry/queries`, matched on the resolved SQL) with their descriptions and the agents that use them.</li><li>**Data quality:** the 5 rules from `/evidence/parity` (`rules`) grouped by table, with "Invalid rows on contract: CTR-30028 (Zetaris and mirror agree)" from `invalid_by_table`, and the parity summary "416 of 416 registry comparisons matched; 32 of 32 KEV checks" with the date of the parity run.</li><li>The catalogue the Planner reads: `catalogue_tokens` and the compact text in a mono block.</li><li>A link to `docs/ZETARIS_USL.md` on GitHub.</li></ul> |
| **Provider** | `/console/provider` | <ul><li>**Connection** (from `GET /health`): resolved provider; Nightshift status; the Runtime URL host and port **with the token hidden** (the API never returns it; show the words "token hidden"); models seen; the fast and deep routing modes requested.</li><li>**Proof** (from `GET /evidence/nightshift`): a table of lane, sent, routed mode (coerced or not), model served and receipt, plus the proof timestamp.</li><li>**Recent receipts:** the last 10 `model_call` events with a receipt from `GET /cases` → `GET /cases/{id}/trace` (at most 5 cases): agent, purpose, lane, model, latency, receipt id.</li><li>**Deviation note** when any receipt says `mode_coerced`: one sentence plus a link to `docs/evidence/nightshift_deviations.md` on GitHub.</li><li>**Run proof now:** shows the CLI command `python run.py llm proof` with a copy button. The console does not run it.</li></ul> |
| **Memory** | `/console/memory` | <ul><li>Precedents from `GET /memory/precedents`: id, from case and vendor, the control it covers, the conditions, who approved it and their role, the feedback history (helpful or wrong), and whether it is currently eligible.</li><li>One sentence at the top: "A precedent changes a decision only where the policy allows an exception, and only if a TPRM lead approved it."</li><li>Empty state: "No precedents yet. A TPRM lead creates one by reviewing a case."</li></ul> |
| **Review** | `/console/review/:caseId` | Port of the Streamlit review form:<ul><li>reviewer, role (`tprm_analyst` or `tprm_lead`), decision (the five outcomes), rationale (≥ 30 characters), create precedent;</li><li>**Check eligibility** (`?dry_run=true`) shows whether a precedent would be eligible and why;</li><li>**Submit review**, then a toast and a link back to the case.</li></ul> |
| **Audit** | `/console/audit` | <ul><li>`GET /audit/recent?limit=50` as a table: time, kind, case, actor, and hash prefix as an `Identifier`.</li><li>**Verify chain** (`GET /audit/verify`) shows "Audit chain verified: N entries" or "Chain breaks at entry N".</li></ul> |
| **Evaluation** | `/console/evaluation` | From `GET /eval/latest` (added by P19):<ul><li>the live table (Arbiter, baseline, offline) with n, accuracy, unsafe approvals, abstention, contradiction recall, p50 and p95, model calls per case and fallback rate;</li><li>the model ids from the traces;</li><li>"n is small" with the Wilson intervals;</li><li>the baseline status sentence exactly as published (do not restate it in different words);</li><li>a link to `docs/EVALUATION.md`.</li></ul>**This instance:** case counts by outcome, data backend, provider. If `/eval/latest` returns 404 (P19 not merged yet), show "Evaluation results are published in docs/EVALUATION.md" with the link |

## 4. Acceptance tests (Vitest with mocked fetch, recorded payloads only; see P18-C §4 for the fixture rule)

| Id | Test |
|---|---|
| P18D-T1 | New vendor: loading a preset fills all 16 questions. Clearing the legal name shows the error by that field and **Start assessment** does not call the API. A valid form posts a body that zod-validates against the generated `CaseInput` type |
| P18D-T2 | Sources: from a recorded `/usl/model` payload, 10 table nodes and 5 declared foreign-key edges render, plus 2 dashed undeclared joins. The DQ section shows `CTR-30028` |
| P18D-T3 | Provider: a `/health` payload with `base_url` renders host and port and the words "token hidden". A proof payload with `mode_coerced: true` renders the deviation sentence. Canary: an `Authorization` or token string placed anywhere in either payload never reaches the DOM |
| P18D-T4 | Review: rationale under 30 characters blocks submit; the dry-run result renders eligibility and the reason |
| P18D-T5 | Audit: the verify result renders both the ok and the broken shape |
| P18D-T6 | Evaluation: renders the three systems from a recorded `/eval/latest` payload, and the 404 fallback |
| P18D-T7 | Parity: every design §9 row owned by 18d has a rendered element (by test id) |

Record the payloads for `/usl/model`, `/evidence/*` and `/eval/latest` from a real sample-mode API with `web/scripts/record-fixtures.mjs`, committed with its output under `web/src/features/**/__tests__/fixtures/`.

## 5. Definition of done

- `npm run check` and `verify-pass --pass 18d` are green.
- Screenshots `docs/img/console_{sources,provider,memory,audit,evaluation,new}.png` at 1440×900.
- The design §9 parity checklist is ticked in the report.

## 6. Claude Code prompt

```
/start-pass 18d
You are implementing P18-D of Arbiter Release 3: the New vendor questionnaire, Sources (USL diagram and DQ), Provider (Nightshift connection and Nemotron proof), Memory, Review, Audit and Evaluation pages in the web console.
Read: CLAUDE.md; docs/spec/release3/README.md; docs/spec/release3/P18_00_DESIGN.md §3–§5 and §9–§12; docs/spec/release3/P18A_STREAM_API.md §3.3; docs/spec/release3/P18D_PAGES.md; web/src/ui; ui/intake.py, ui/sources_view.py, ui/provider.py, ui/screens.py; ui/presets.json; app/api/routes_meta.py and routes_review.py.
Edit only the folders 18d owns (docs/spec/release3/README.md §6) and new files in web/src/ui. Never render a token; the Provider page shows "token hidden".
Plan first: .cursor/plans/P18-D.md with pages, components and tests P18D-T1..T7. Wait for my approval.
Tests first → implement → screenshots → verify-pass 18d green → PR into p18-console.
Finish with docs/passes/P18-D_REPORT.md and docs/cursor-usage/P18-D.md; delete .cursor/ACTIVE_PASS; stop.
```
