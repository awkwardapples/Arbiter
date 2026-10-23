# P14: Decision quality and analyst brief (A, backend); analyst console (B, UI)

---

# Lane P14-A: correct decisions, a brief an analyst can act on, an exportable dossier

## A1. Goal

Every decision an analyst sees is **correct, consistent and readable**:

- reason codes never contradict the outcome;
- confidence reflects real evidence coverage;
- counterfactuals are de-duplicated;
- every case carries an **Analyst Brief**: a one-sentence headline, up to four "why" points pairing the vendor's claim with the system of record, and next steps with owners;
- the full drafted action text (clarification email, escalation ticket, approval memo) is included;
- a **decision dossier** (Markdown and HTML) can be exported for the audit file;
- each response reports the **measured workload** the agents did.

## A2. Why it scores

- **Technical:** finding B1–B3 bugs fixed.
- **Product & UX and Impact:** the output is what a TPRM analyst would actually file and send.
- **Demo:** the brief is readable on screen in five seconds.

## A3. Read first

- `R2_00_ASSESSMENT.md` §3 (Technical, UX), §4 (bugs B1–B3)
- Master spec §§7, 8.6
- `02_POLICY.md` §§1, 5
- `app/agents/reporter.py`, `app/policy/engine.py`, `app/confidence.py`, `app/schemas/{report,api}.py`

## A4. Deliverables

| File | Change |
|---|---|
| `app/policy/engine.py` | **B1:** `outcome_reasons` is the reasons of every matching rule **except `always`**, which is listed only when it decided the outcome (i.e. nothing else matched). `record_sha256` changes; replay of *new* records still matches. Add `policy_engine_version: "1.1"` to the record so older stored records replay with old semantics (or document that the case store is reset; the demo store is regenerated anyway) |
| `app/confidence.py` | **B2:** a required control is *covered* only if its `ControlResult.state` is TRUE or FALSE **and** every fact it cites has verified provenance (as defined in master spec §8.6). Add signal `unknown_controls` to the breakdown for display. Re-run `python run.py calibrate` on the calibration split; commit the new `policy/calibration/<version>.json` and `ACTIVE`; zero unsafe approvals must still hold, and the six e2e examples must keep their expected outcomes. If an expected outcome changes, **stop and ask** |
| `app/policy/counterfactuals.py` | **B3:** one counterfactual per control. Merge `evidence_required` and `question_ids` (ordered, de-duplicated); contradiction resolution becomes an item in the same entry |
| `app/labels.py` (new) | Business labels, single source for API, dossier and UI: outcome → label and one-line meaning; reason code → plain English; control id → title (from policy); system → "Contract system (CLM)", "Procurement (ERP)", "Service desk (ITSM)", "Sanctions watchlist (GRC)", "Vendor trust portal", "CISA Known Exploited Vulnerabilities"; question id → question text |
| `app/schemas/report.py` | Additive: `AnalystBrief {headline: str, why: list[BriefPoint], next_steps: list[NextStep], generator: str}`. `BriefPoint {text, claim: EvidenceRef \| None, record: EvidenceRef \| None, citations: list[str]}`. `EvidenceRef {source_label, record_label, field_label, value, quote \| None, provenance_id}`. `NextStep {action, owner_role, due \| None}`. `Report.brief: AnalystBrief`. `Report.drafts: list[Draft]` (email, ticket or memo with **full body text**) |
| `app/agents/reporter.py` | **Deterministic brief** (`template:v2`): plain English, no codes. Example headline: *"Escalate to the TPRM lead: Quillfeather says customer data stays in the EU, but its contract (CTR-30007) puts hosting in the US, and the FortiOS it runs has 15 known-exploited vulnerabilities against a 30-day critical-patch SLA (policy: 14 days)."* Why-points are generated from failing controls, contradictions, DQ flags and guard blocks, each pairing claim versus record with values. Drafts: REQUEST_INFO → vendor email listing each question with *what evidence would satisfy it*; ESCALATE → ITSM ticket body (summary, evidence, risk, requested decision); DECLINE → decline memo for the business owner; APPROVE/AWC → approval memo with conditions. **LLM brief** (deep route): may rewrite `headline` and `why[].text` only. The validator keeps the deterministic evidence refs and citations, rejects any number or name not present in the record, and falls back to `template:v2` |
| `app/schemas/api.py` | Additive: `RunOutput.brief`, `RunOutput.drafts`, `RunOutput.workload {systems_queried: [label], queries: int, rows_read: int, documents_read: int, answers_read: int, claims_extracted: int, claims_grounded: int, contradictions: int, dq_flags: int, guard_blocks: int, model_calls: int, models: [id], elapsed_seconds: float}`. `summary` becomes the brief headline |
| `app/orchestrator.py` | Workload counters filled from executed state (no estimates) |
| `app/dossier.py` (new) | `render(case_bundle, fmt="md"\|"html") -> str`. Sections: header (vendor, decision, tier, residual risk, confidence with unknown controls named); the brief; evidence table (claim versus system of record, with source labels and Zetaris request ids when live); controls (title, state, why); counterfactuals; drafts; approvals and contract state with signature check; precedents; integrity (policy version and hash, calibration version, record hash, replay command, trace id, models served). HTML is self-contained, printable, with no external assets |
| `app/api/routes_cases.py` | `GET /cases/{id}/dossier?format=md\|html` |
| `app/cli/dossier.py` (new) | `python run.py dossier CASE [--format md\|html] [--out FILE]` |

## A5. Acceptance tests (marker `p14a`)

| Id | Test |
|---|---|
| P14A-T1 | No record from the six examples or the 32 label-oracle cases lists `ALL_REQUIRED_CONTROLS_MET` unless the outcome is APPROVE and no other rule matched |
| P14A-T2 | Coverage: a T3 case with C01 UNKNOWN has coverage < 1 and `unknown_controls` containing C01; a fully verified case has coverage 1.0 |
| P14A-T3 | Counterfactuals are unique per control; contradiction text is merged into the control's entry |
| P14A-T4 | Re-calibration keeps zero unsafe approvals on calibration; the e2e expected outcomes are unchanged |
| P14A-T5 | `template:v2` brief for example 2 mentions the vendor name, both residency values (EU and US), the contract id, and the KEV product and count. **No** reason codes, fact ids or query ids appear in `headline` or `why[].text` (regex on `[A-Z_]{6,}`, `F-C\d+`, `Q_[A-Z_]+`) |
| P14A-T6 | Drafts: REQUEST_INFO (example 4) email contains every counterfactual question text; ESCALATE contains a ticket body; DECLINE contains a memo addressed to the business owner |
| P14A-T7 | LLM brief validator: a fake LLM that adds a number not in the record, or a vendor name not in the case, is rejected, and `template:v2` is used (traced `fallback`) |
| P14A-T8 | `workload` counts equal the trace (queries = `query_run` events, model_calls = `model_call` events) |
| P14A-T9 | Dossier md and html for every example: all sections present, no secrets, HTML has no external URLs except citations, replay command included. `GET …/dossier` returns 200 with the right content type |
| P14A-T10 | Label coverage: every outcome, reason code, control id, system and question id in the policy and registry has a label |

## A6. Verification

```bash
python scripts/tasks.py verify-pass --pass 14a
SAMPLE_MODE=true LLM_PROVIDER=offline python run.py assess --input input_examples/example_2.json
python run.py dossier CASE-0007 --format html --out /tmp/dossier.html
```

## A7. Cursor prompt

```
/start-pass 14a
You are implementing P14-A of Arbiter Release 2: decision correctness (bugs B1–B3), the Analyst Brief, full action drafts, workload metrics and the exportable decision dossier.
Read: AGENTS.md; docs/spec/release2/README.md; docs/spec/release2/R2_00_ASSESSMENT.md §§3–4; docs/spec/release2/P14_DECISION_QUALITY_AND_CONSOLE.md lane A; docs/spec/00_MASTER_SPEC.md §§7, 8.6; docs/spec/02_POLICY.md §§1, 5.
The policy still decides; the LLM may only rephrase the brief's headline/why text and is validated against the record. If any e2e expected outcome changes after the confidence fix, set ACTIVE_PASS to blocked and ask.
Plan Mode: .cursor/plans/P14-A.md with files and tests P14A-T1..P14A-T10. Wait for approval.
Tests first (marker p14a) → commit → implement until `python scripts/tasks.py verify-pass --pass 14a` is green.
Finish with docs/passes/P14-A_REPORT.md (before/after brief for examples 2 and 4) + docs/cursor-usage/P14-A.md; push p14a-decision; delete .cursor/ACTIVE_PASS; stop.
```

---

# Lane P14-B: the analyst console a TPRM team would actually use

## B1. Goal

The console reads like a product for a third-party risk analyst, not a debugger.

- Plain-English decision brief first.
- Claim-versus-record evidence cards.
- The next action, with its drafted text, one click away.
- A guided questionnaire intake instead of JSON.
- A *Sources & semantic layer* page showing the Zetaris USL.
- A portfolio summary.
- Provider proof (Nightshift, Nemotron).
- Dossier download.
- Fresh screenshots captured by a script.

## B2. Why it scores

- **Product & UX (10).**
- **Demo (15):** every segment of the video is filmed here.
- **Impact:** the analyst's improved day is visible.

## B3. Read first

- `R2_00_ASSESSMENT.md` §3 (Product & UX)
- P14-A's schemas (`AnalystBrief`, `drafts`, `workload`; merged first)
- P13's `data/usl/vendor_risk.model.json` (if P13 is not merged yet, build against the schema in P13 §5 step 8 and a test fixture)
- The current `ui/screens.py`, `ui/components.py`

## B4. Deliverables

| Area | Requirement |
|---|---|
| **Case page** (top to bottom) | (1) Header: vendor, decision badge with label and meaning, tier, residual risk, confidence with *"2 controls unverified: C01 MFA, C04 encryption"* instead of a bare %. (2) **Brief**: headline as a callout; up to four why-points, each a two-column **claim card versus record card** (source label, record, field, value, quote), with discrepancies highlighted in text and colour. (3) **Next action panel**: the draft's subject and body in an editable text area, *Copy* and *Download .txt*; for pending contracts, Approve or Reject with role select and rationale (≥ 30 chars), which calls `/contracts/{id}/approve`; for executed actions, the outbox file name. (4) **Controls** table with business titles and status labels; fact and query ids only inside a *Technical details* expander. (5) **What would change this decision** (de-duplicated counterfactuals as a checklist). (6) **Precedents considered** (applied or rejected, with the failed criteria in words). (7) **Agent timeline** (existing; keep, with stage labels in words). (8) **Workload** strip: *"Checked 6 systems, 11 queries, 16 answers, 2 documents, 1 contradiction found, in 38 s with 9 Nemotron calls"*. (9) *Download dossier* (HTML and Markdown) |
| **New assessment** | Two tabs. *Existing vendor*: picker with name and status. *New vendor questionnaire*: form fields (legal and trading name, service, criticality, spend, data categories, countries), the 16 questionnaire questions as text areas with their help text, optional document text paste (type, issued, expires), declared components (vendor/product/version rows), and a *Load an example vendor* preset selector. Client-side validation. The submit shows staged progress, then opens the case. JSON paste stays as an *Advanced* expander |
| **Cases** (portfolio) | Metrics row: total, by outcome, pending approvals, median run time. Table with business labels, row click opens the case, filters |
| **Sources & semantic layer** (new) | Data mode (Zetaris USL / DuckDB mirror); USL ERD rendered from the model JSON (graphviz: tables, PK, FK edges, descriptions on hover or in a table); per-table row counts and DQ status from `/health`; KEV catalogue version; a short "why a semantic layer" explainer linking `docs/ZETARIS_USL.md` |
| **Provider proof** (sidebar or in the header) | `Nightshift: online · http://127.0.0.1:8088/v1 · token hidden`; models served on the last run (from trace), e.g. `fast → nvidia/nemotron-3.5-lightning-30b-a3b`, `deep → nvidia/nemotron-3-super-120b-a12b`; last receipt id. In sample mode: *"Offline fallback (deterministic). Live runs use Meterless Nightshift → NVIDIA Nemotron."* |
| **Precedents, Review, Audit, Evaluation** | Business language; Review explains eligibility in words; Evaluation renders the comparison table (arbiter live / baseline / offline) when P15 publishes it |
| **Copy rules** | No SCREAMING_CASE codes, `F-…`, `Q_…` or `answer_id=` outside *Technical details* expanders. All labels come from the API (`app/labels.py` via responses) |
| `scripts/capture_ui.py` (new) | Playwright (Chromium; the browser path is configurable) drives the console against a running API and writes `docs/img/ui_<page>.png` at 1440×1000 for: brief (example 2), next action (example 4 email), questionnaire form, cases portfolio, sources and USL, precedents after `demo-session`, audit replay. Waits for Streamlit idle. Never captures the sidebar token. Not part of CI |

## B5. Acceptance tests (marker `p14b`)

| Id | Test |
|---|---|
| P14B-T1 | AppTest smoke for every page with the fake client (fixtures recorded from real P14-A responses) |
| P14B-T2 | Copy rule: the rendered text of the Case page outside `Technical details` contains no `[A-Z_]{6,}` code, `F-C\d`, `Q_` or `answer_id=` |
| P14B-T3 | The Next action panel shows the full draft body; Approve calls the client with role and rationale; a short rationale is refused client-side |
| P14B-T4 | The questionnaire form builds a `VendorSubmission` that validates with the API schema; presets fill all 16 answers; invalid input does not call `/run` |
| P14B-T5 | The Sources page renders an ERD with 10 nodes and the FK edges from the model fixture |
| P14B-T6 | Provider proof shows the served model ids from a live-trace fixture and the offline label for an offline fixture; the token is never rendered |
| P14B-T7 | The workload strip sentence is built from `workload` fields only |
| P14B-T8 | The dossier download buttons call the dossier endpoint for both formats |

## B6. Cursor prompt

```
/start-pass 14b
You are implementing P14-B of Arbiter Release 2: the analyst console a TPRM team would actually use.
Read: AGENTS.md; docs/spec/release2/README.md; docs/spec/release2/R2_00_ASSESSMENT.md §3 (Product & UX); docs/spec/release2/P14_DECISION_QUALITY_AND_CONSOLE.md lane B; app/schemas/report.py and app/schemas/api.py (P14-A additions); data/usl/vendor_risk.model.json if present.
The UI talks only to the API. Business language everywhere; technical ids only inside "Technical details" expanders. Never render secrets.
Plan Mode: .cursor/plans/P14-B.md with ASCII wireframes per page and tests P14B-T1..P14B-T8. Wait for approval.
Tests first (marker p14b) → commit → implement until `python scripts/tasks.py verify-pass --pass 14b` is green; then run scripts/capture_ui.py with me.
Finish with docs/passes/P14-B_REPORT.md (screenshot list) + docs/cursor-usage/P14-B.md; push p14b-console; delete .cursor/ACTIVE_PASS; stop.
```
