# P5: Reviewer console (A) and evaluation harness and calibration (B)

---

# Lane P5-A: Reviewer console (Streamlit, API-only)

## A1. Goal

A TPRM analyst can, without touching a terminal:

- run an assessment (pick a vendor or upload a submission);
- see the prioritised queue;
- understand **why** a decision was made (controls, cited evidence, contradictions, counterfactuals, precedents);
- watch the agents collaborate on a timeline;
- review, override and approve with a rationale;
- see memory and the audit trail.

The UI talks **only** to the API.

## A2. Why it scores

**Product & UX (10)** and the **Demo** visuals. It also makes the reasoning *visible* to judges.

## A3. Read first

- Master spec §8.10
- The API routes from P3, P4-A and P4-B (`/openapi.json`)

## A4. Deliverables

| File | Responsibility |
|---|---|
| `ui/client.py` | A thin `httpx` client for every endpoint (`ARBITER_API_URL`, default `http://localhost:8000`). Errors surface as friendly messages carrying the `ErrorResponse.message` |
| `ui/components.py` | `decision_badge(outcome)` (icon **and** text, never colour alone), `tier_chip`, `confidence_gauge(value, gate, abstained)`, `evidence_chip(provenance)` (system · query id · record key, expandable to the source row), `control_table(controls, facts)`, `timeline(events)` (below), `glossary()` |
| `ui/app.py` | `st.navigation` with the pages below. The sidebar shows mode and provider status from `/health` (data: Zetaris or DuckDB; LLM: Meterless, NVIDIA or offline; models) |
| Page **New assessment** | Vendor picker (from `GET /vendors`), *or* a JSON upload or paste of a `VendorSubmission` with schema validation. A Run button shows a spinner with live state names from the response, then navigates to the case |
| Page **Queue** | Cards sorted by residual risk: badge, vendor, tier, risk, age and status (pending approval or done). Filters: outcome and tier |
| Page **Case** | (1) Decision banner: badge, one-sentence summary, confidence gauge, "abstained" note. (2) **Why**: a controls table (state, rule id, cited facts as evidence chips). (3) Contradictions panel (claim versus system of record, side by side). (4) "What would change this": the counterfactual checklist. (5) Precedents considered or applied. (6) Actions: contract state, required approvals, outbox preview; an Approve or Reject form when pending. (7) **Agent timeline.** (8) Cited report. (9) Raw JSON expanders |
| Page **Review** | Override form: decision, rationale (≥ 30 chars, live counter), mitigations, conditions, and a "create precedent" toggle that shows the policy eligibility hint (from `POST /cases/{id}/review?dry_run=true`) |
| Page **Memory** | Precedent table (id, control, mitigation, confidence, created by and role, age), ledger history per precedent, the retrieval trace for the last run |
| Page **Audit** | Chain verification button and result; a replay button per case showing the diff |
| Page **Evaluation** | Renders the latest `eval/results/*/summary.md` (read through a small `GET /eval/latest` in `routes_meta`, P5-B) |

**Agent timeline.** Built from `GET /cases/{id}/trace`:

- **Graph:** a DOT graph via `st.graphviz_chart`, with nodes for agents and edges for handoffs. Loop edges (EVALUATE → PLAN, CHALLENGE → PLAN) are dashed and labelled with the gap controls.
- **Table:** time, agent, action, target, status (text + icon), summary, provider/model, query id/rows, latency.
- **Filters:** by agent and by status. Zetaris and Meterless events have their own icons so judges can see them.

**Visual rules:**

- Consistent spacing.
- Max content width about 1100 px.
- Readable at 125% zoom.
- Every status has a text label.
- Keyboard-reachable forms.
- A plain-language glossary panel (SoR, KEV, USL, DQ, precedent, counterfactual).

## A5. Acceptance tests (marker `p5a`)

| Id | Test |
|---|---|
| P5-T10 | Static: `ui/` imports nothing from `app.` except `app.schemas` (for typing and validation) |
| P5-T11 | `streamlit.testing.v1.AppTest` smoke test for every page with a fake client (fixtures from real API responses captured from e2e runs): no exceptions; key elements present (badge text, controls table, timeline) |
| P5-T12 | `decision_badge` and the status renderers always include a text label (unit test over all enum values) |
| P5-T13 | The timeline builder turns example 2's real trace into a graph with a dashed EVALUATE→PLAN edge and the correct node set |
| P5-T14 | Uploading an invalid submission shows validation errors and does not call `/run` |

## A6. Verification

```
python run.py serve & python run.py ui     # http://localhost:8501
python scripts/tasks.py verify-pass --pass 5a
```

Save screenshots of every page (synthetic data, no keys) to `docs/img/ui_*.png` for the deck and README.

## A7. Definition of done

- [ ] All pages work against a live API.
- [ ] Screenshots are saved.
- [ ] The report includes the screenshot list and known UX gaps.

## A8. Cut lines (in order)

1. Memory and Audit pages (the endpoints remain).
2. The Evaluation page.
3. Graph view (keep the timeline table).

## A9. Cursor prompt

```
/start-pass 5a
You are implementing lane P5-A of Arbiter: the Streamlit reviewer console. It must talk only to the HTTP API.
Read: AGENTS.md; docs/spec/00_MASTER_SPEC.md §8.10; docs/spec/passes/P5_UI_EVAL.md lane A; the running API's /openapi.json.
Accessibility: never colour-only; text labels on every status; keyboard-reachable forms.
Plan Mode: .cursor/plans/P5-A.md with page wireframes (ASCII), components and tests P5-T10..P5-T14. Wait for approval.
Tests first (marker p5a) → commit → implement until `python scripts/tasks.py verify-pass --pass 5a` is green; then capture screenshots with me.
Finish with docs/passes/P5-A_REPORT.md + docs/cursor-usage/<LABEL>.md; push p5a-ui; delete .cursor/ACTIVE_PASS; stop.
```

## A10. Explain it

1. Which page answers "why was this vendor escalated?", and how does a chip lead back to Zetaris?
2. How does the timeline prove it is not a linear pipeline?
3. What can a reviewer do that the system cannot?
4. How is the UI accessible beyond colour?
5. Why does the UI never import the core package?

---

# Lane P5-B: Evaluation harness, baseline, calibration, publishing

## B1. Goal

Implement `03_EVALUATION.md`:

- labelled runs over the splits for Arbiter, the single-LLM baseline and offline Arbiter;
- the metrics;
- consistency;
- the session test (reusing `demo-session`);
- gate calibration;
- results written to `eval/results/<ts>/`;
- **code-only publishing** to `docs/EVALUATION.md` and the README block.

## B2. Why it scores

It makes "reliable" measurable (Track 3 and Impact), and gives the "versus single-LLM baseline" proof for **Innovation** and **Demo**. Honest reporting protects every criterion.

## B3. Read first

`03_EVALUATION.md` (all of it); master spec §8.6.

## B4. Deliverables

| File | Responsibility |
|---|---|
| `eval/metrics.py` | Pure functions for every metric in 03 §3, plus Wilson intervals |
| `eval/baseline.py` | 03 §2.1 exactly: same backend and queries; `eval/prompts/baseline.md`; one call; `INVALID` on a parse failure |
| `eval/harness.py` | `run(systems, splits, consistency=(K, R), concurrency≤2)`. Runs every case with `ARBITER_MEMORY=off` and a fresh temporary `var/` per case and repeat (03 §3.3), runs cases, and collects outcomes, reasons, tokens, latency, trace paths and fallbacks from the actual run artefacts. Writes `cases.jsonl`, `summary.json`, `summary.md`, `confusion_<system>.csv` and `env.json` (git sha, mode, provider, discovered model ids from traces, split sha, calibration version, KEV catalogVersion) |
| `eval/calibrate.py` | 03 §4: an offline recompute of `decide` over stored inputs with a grid of gates per tier, objective accuracy subject to zero unsafe approvals, conservative ties. Writes a new `policy/calibration/<version>.json` and updates `policy/calibration/ACTIVE` (never overwrites an old version) |
| `eval/report.py` | `render_summary_md(summary)`, `publish(summary)`: regenerate `docs/EVALUATION.md` and replace the README block between `<!-- EVAL:START -->` and `<!-- EVAL:END -->` (P6 creates the markers; until then publish only the docs file) |
| `app/cli/eval.py` | `eval [--split test\|calibration\|inline\|all] [--systems …] [--consistency KxR] [--publish] [--session]` and `calibrate` |
| `app/api/routes_meta.py` ✎ | `GET /eval/latest` only (P4-B owns the file; add this one route as your final commit, after P4-B is merged) |

## B5. Acceptance tests (marker `p5b`)

These are P5-T1…P5-T6 from 03 §7, plus:

| Id | Test |
|---|---|
| P5-T7 | `env.json` model ids are read from trace events (not config); a run whose traces contain `provider=offline` is labelled offline in `summary.md` |
| P5-T8 | `publish` is idempotent and changes nothing outside the markers |

## B6. Run plan (human-attended for live)

1. **Offline full run (CI-sized):** `python run.py eval --split all --systems arbiter_offline,baseline --llm offline`
2. **Calibration (live):** `python run.py eval --split calibration --systems arbiter`, then `python run.py calibrate`
3. **Test (live, once):** `python run.py eval --split test,inline --systems arbiter,baseline,arbiter_offline --consistency 8x3`
4. **Session (live):** `python run.py eval --session`
5. **Publish:** `python run.py eval --publish` (uses the latest complete results)

## B7. Definition of done

- [ ] A live test-split summary exists, or offline-only is documented with the reason.
- [ ] Zero unsafe approvals for `arbiter` on test (if not, **stop and tell me**: this is a design issue, not a tuning issue).
- [ ] The report includes `summary.md` verbatim.

## B8. Cut lines

Ablation; consistency reduced to 4×2; calibration (keep the initial gates and say so).

## B9. Cursor prompt

```
/start-pass 5b
You are implementing lane P5-B of Arbiter: evaluation harness, single-LLM baseline, calibration and code-only publishing.
Read: AGENTS.md; docs/spec/03_EVALUATION.md (all); docs/spec/00_MASTER_SPEC.md §8.6; docs/spec/passes/P5_UI_EVAL.md lane B.
Honesty rules in 03 §6 are binding: numbers only from results files; never tune on the test split; label offline numbers as offline.
Plan Mode: .cursor/plans/P5-B.md with files, metric definitions and tests P5-T1..P5-T8. Wait for approval.
Tests first (marker p5b) → commit → implement until `python scripts/tasks.py verify-pass --pass 5b` is green; then run §B6 with me.
Finish with docs/passes/P5-B_REPORT.md (paste summary.md) + docs/cursor-usage/<LABEL>.md; push p5b-eval; delete .cursor/ACTIVE_PASS; stop.
```

## B10. Explain it

1. Why is the baseline fair, and what is its known weakness?
2. What counts as an "unsafe approval"?
3. Why calibrate only the gates?
4. How can a judge verify the README numbers?
5. Where did Arbiter lose to the baseline, if anywhere, and why?
