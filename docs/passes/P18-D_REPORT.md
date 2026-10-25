# P18-D report: the remaining pages

Lane 18d rebuilds the Streamlit pages that P18-B and P18-C do not cover: New vendor, Sources, Provider, Memory, Review, Audit and Evaluation. Branch `p18d-pages`, merged from `p18-console` after PR #34 (P18-B), with a PR into `p18-console`.

## What was built

| Page | Route | What it shows |
|---|---|---|
| New vendor | `/console/new` | A port of `ui/intake.py`. It covers the vendor fields, all 16 questions from `GET /questions` (Yes / No / Not answered plus "How?", or a text box), and document and component rows. **Load an example vendor** fills the form. Validation names each problem next to its field and row. The Advanced section takes pasted JSON. **Start assessment** builds the same `CaseInput` as Streamlit, posts `POST /runs` and opens the run view. |
| Sources | `/console/sources` | The data mode from `/health`, and the USL ERD drawn with React Flow and dagre, left to right. It has 10 table nodes with description, primary key, collapsible columns and row counts from `/health`. The 5 declared foreign keys are solid; the 2 documented undeclared joins are dashed and labelled "joined in the query, not a declared key". Clicking a table lists the registry queries that read it, with the agents that ran them in the latest case. Below the ERD are data quality and parity from `/evidence/parity` (CTR-30028; 416 of 416; 32 of 32), the Planner's compact catalogue with its token estimate, and a link to `docs/ZETARIS_USL.md`. |
| Provider | `/console/provider` | **Connection:** Nightshift host:port with "token hidden", the lanes, and the Nemotron models offered. **Proof:** the committed proof from `/evidence/nightshift`. **Recent receipts:** the last 10 model calls that carry a receipt, across the 5 newest cases. Also the deviation note (lane coerced to auto) and a "Run proof now" copy box. Every value passes a shape check before it renders; anything else is dropped. |
| Memory | `/console/memory` | Each precedent: control, source case, approver and time, how many later cases retrieved it, feedback counts and ledger entries, and memory confidence. Also the governance sentence and the empty state. |
| Review | `/console/review/:caseId` | The lead or analyst review form: decision, role, reviewer, rationale (at least 30 characters), mitigations and conditions. A dry run shows precedent eligibility and the reasons. The precedent controls unlock only when the dry run says eligible, and the result goes stale when the decision or role changes. Submit shows a toast and links back to the case. |
| Audit | `/console/audit` | The 50 newest entries (entry, time, what happened in words, case). **Verify chain** gives "Audit chain verified: N entries." or "Chain breaks at entry N." |
| Evaluation | `/console/evaluation` | `/eval/latest` with the three systems: accuracy, unsafe approvals, abstention, contradiction recall, latency, calls per case and fallback rate. A small-n box gives Wilson intervals. Also the models seen, the published notes word for word, a link to `docs/EVALUATION.md#discussion`, and `baseline_status` when the payload carries it. If the API answers 404, a callout says no evaluation is published. "This instance" lists outcomes by case. |

New shared pieces under `web/src/ui/` (new files only): `Field`/`FieldGroup`, `NativeSelect`, `ToggleChips`, `CopyBlock`, `DocLink`, and the test harness `__tests__/harness.tsx` (`stubApi`, `renderPage`, `fixture`, `fromRepo`). They use the design tokens only; no new colours, fonts or effects.

**Presets:** `web/src/features/intake/presets.json` is a **copy** of `ui/presets.json`, as the pass asks. If one changes, the other must be updated by hand. `presets.d.ts` types the import, because `tsconfig.app.json` (18b-owned) has no `resolveJsonModule`.

## Tests

| Id | Where | Result |
|---|---|---|
| P18D-T1 | `web/src/features/intake/__tests__/intake.test.tsx` | pass: a preset fills all 16 questions; a missing legal name blocks the POST; a valid form posts a `CaseInput` |
| P18D-T2 | `web/src/features/usl/__tests__/usl.test.tsx` | pass: 10 nodes, 5 solid foreign keys, 2 dashed labelled joins, declared edges point left to right, CTR-30028 and the parity summary in DQ, row counts on nodes |
| P18D-T3 | `web/src/pages/provider/__tests__/provider.test.tsx` | pass: host:port with "token hidden", the deviation sentence, and no canary anywhere in the DOM. Canaries are planted in `/health`, the proof and the trace, as new keys, inside existing strings and in lists. |
| P18D-T4 | `web/src/pages/review/__tests__/review.test.tsx` | pass: a rationale under 30 characters blocks submit; the dry run shows eligibility and why |
| P18D-T5 | `web/src/features/audit/__tests__/audit.test.tsx` | pass: the verified sentence and the broken one |
| P18D-T6 | `web/src/features/evaluation/__tests__/evaluation.test.tsx` | pass: the three systems, and the 404 fallback |
| P18D-T7 | `web/src/pages/new/__tests__/parity18d.test.tsx` | pass: one case per design §9 row owned by 18d, each found by test id |

Nine more tests cover:
- per-field validation messages, and the Advanced JSON path;
- the queries panel for a selected table;
- the catalogue token count matching the API's;
- receipts and proof shown as recorded;
- an eligible dry run that unlocks and submits a precedent;
- the audit table;
- `baseline_status` shown word for word.

`npm run check` gives 20 files and 69 tests passing (18b's included). `python scripts/tasks.py verify-pass --pass 18d` is green.

**Fixtures** were recorded by `node web/scripts/record-fixtures.mjs --lane 18d --base http://localhost:8018` from `SAMPLE_MODE=true LLM_PROVIDER=offline python run.py serve`. None are hand-written. `var/` had been cleared while the API was down, so the final set was re-recorded from a **clean `var/`**. As a result:
- Memory has exactly one real precedent (P-0001, from CASE-0011, approved by a TPRM lead, retrieved by a later case, marked helpful).
- Audit has six real entries.

The recorder makes two edits, both about the recording machine rather than Arbiter:
- `models_seen` in `/health` keeps only the `nvidia/` and `meterless/` routes;
- `data.sample_dir` becomes repo-relative.

The 404 fixture for T6 comes from `GET /cases/CASE-does-not-exist`. The sample API has `/eval/latest` published, so its own 404 could not be recorded; the error shape is the API's standard one.

## Parity checklist (design §9, rows owned by 18d)

- [x] **New assessment: questionnaire form.** 16 questions from `/questions` with Yes/No/Not answered plus How?, document and component rows, presets, client validation, JSON under Advanced. Page: New vendor (`/console/new`).
- [x] **Sources and semantic layer.** Data mode, ERD of 10 tables with foreign keys, descriptions, row counts, DQ rules. Page: Sources (React Flow plus dagre; DQ and parity).
- [x] **Review.** Lead or analyst review form, with a dry run for precedent eligibility. Page: Review (`/console/review/:caseId`).
- [x] **Precedents.** List, status, feedback. Page: Memory.
- [x] **Audit.** Recent events, verify chain. Page: Audit.
- [x] **Evaluation.** Offline and live summaries, and this instance's activity. Page: Evaluation (`/eval/latest`).
- [x] **Sidebar provider proof.** Nightshift status, URL with token hidden, served models, last receipt. Page: Provider.

P18D-T7 checks each row by test id.

Screenshots at 1440×900, against the sample API on this branch: `docs/img/console_sources.png`, `console_provider.png`, `console_memory.png`, `console_audit.png`, `console_evaluation.png`, `console_new.png`.

## Deviations and decisions
1. **Provider models.** `/health` lists every model the Nightshift runtime can see, including the recording machine's unrelated local models. The page shows the Nemotron models as badges and counts the rest ("and 69 other routes and models").
2. **Query to agent mapping.** `GET /registry/queries` does not say which agent runs a query. The Sources panel derives it from the latest case's trace (`query_run` events) and says so on the page.
3. **Undeclared joins.** The two documented joins are drawn only when a registry query's SQL actually reads both tables, so the diagram cannot show a join the registry does not make.
4. **Published notes.** The Evaluation page shows the prose lines of `live_markdown` word for word and links to the Discussion section of `docs/EVALUATION.md`. It does not summarise them. `baseline_status` is shown when present; P20 has not added it yet.
5. **Test timeouts.** The intake and review suites run with a 30 s describe timeout. Long text is pasted, not typed key by key. Under load on WSL, typing exceeded 5 s. No assertion changed.
6. **Secret-scan canaries.** The Provider test's canary values start with `example-` and set fields through a variable. The repo's history scan matches `token = <12+ chars>`, and the first shape tripped it. The canaries still cover every place a payload could carry a token.
7. **dagre 3.1.1, not 3.1.2.** 3.1.2 was published the day before this lane, so I skipped it.

## Files outside 18d's list (approved)
- `web/package.json` and `web/package-lock.json` (18b-owned): one additive dependency, `"@dagrejs/dagre": "3.1.1"`, pinned exactly. Nothing else changed.
- `web/scripts/record-fixtures.mjs`: new, with one route list per lane (`LANES["18d"]`) so 18c can add its own without conflicts.
- `web/src/pages/{sources,provider,new,memory,review,audit,evaluation}/index.tsx`: 18b's placeholders, replaced by a one-line re-export as planned.
- `docs/img/console_{sources,provider,memory,audit,evaluation,new}.png` (P20 owns the folder; this lane produces these files).
- `web/dist/**`: rebuilt.

## Follow-up for P19/P20: API gaps (no API files edited)
The pages show what the API serves. These fields would complete them:
- **Memory (`GET /precedents`):**
  - the conditions and mitigations recorded with the precedent;
  - the approver's role (only the email and time are in the ledger);
  - whether the precedent is still eligible under the current policy version.
- **Audit (`GET /audit/recent`):** the actor and a hash prefix per entry. Today it serves seq, time, case and event type.
- **Parity (`GET /evidence/parity`):** the date of the parity run. The spec asks for "with the date of the parity run"; the payload has no timestamp, so the page names the committed file (`docs/passes/P1-B_parity.json`) and shows no date.
- **Registry (`GET /registry/queries`):** which agents use each query. The page derives this from the latest trace for now.
- **`/eval/latest`:** `baseline_status`. The page is ready for it.

## Known gaps
- I watched every page in a browser against the sample API, at 1440×900 only. I did not check them against live Zetaris and Nightshift. The Provider page's live shape is covered by the committed proof and the recorded live trace `run-83de5da137c0`.
- Port 8018 was also used by 18b's smoke for a while. 18b moved to 8028.

## Commands run
```
cd web && npm ci && npm install --save-exact @dagrejs/dagre@3.1.1 && npm run check
SAMPLE_MODE=true LLM_PROVIDER=offline PORT=8018 python run.py serve
node web/scripts/record-fixtures.mjs --lane 18d --base http://localhost:8018
python scripts/tasks.py verify-pass --pass 18d
python <scratch>/shots.py   # Playwright, 1440x900, against http://localhost:8018/console/
```
