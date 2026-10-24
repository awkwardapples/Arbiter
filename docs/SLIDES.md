# Slide deck outline

Thirteen slides. The deck has not been built yet; build it from this file and export a PDF. Keep on-slide text to about thirty words. Speaker notes hold the file or trace behind each claim. No keys, `.env` or real personal data on any slide.

The one-line description, identical in the README, `metadata.json`, this deck and the submission form:

> Auditable reasoning for third-party vendor onboarding: agents gather cited evidence, a versioned policy decides, and the next action is a signed contract.

Track: Reasoning Architecture. Team: Josh Lennon, solo builder.

## Coverage

Judging rubric:

| Criterion | Weight | Slides |
|---|---:|---|
| Impact (30) | 30 | 2, 3, 12 |
| Technical (20) | 20 | 5, 6, 10, 12 |
| Innovation (15) | 15 | 4, 6, 7 |
| Demo (15) | 15 | 6, 11 (and the video) |
| Product & UX (10) | 10 | 4, 11 |
| Sponsor Tech (10) | 10 | 8, 9, 10 |

The eight required points:

| Required point | Slides |
|---|---|
| 1 Problem and users | 2, 3 |
| 2 Solution | 4, 12 |
| 3 Workflow and architecture | 5, 6, 7 |
| 4 Technical stack | 10 |
| 5 Sponsor use | 8, 9 |
| 6 What was unique | 7, 8, 9 |
| 7 Product visuals | 11 |
| 8 Results and future | 12, 13 |

## 1. Title

**On slide.** Arbiter. Track: Reasoning Architecture. "Auditable reasoning for third-party vendor onboarding: agents gather cited evidence, a versioned policy decides, and the next action is a signed contract." Josh Lennon.

**Visual.** `docs/img/arbiter_logo.png`.

## 2. The problem, in numbers

**On slide.**
- Third parties are involved in 48% of breaches (Verizon 2026 DBIR, https://www.verizon.com/business/resources/Te26/reports/2026-dbir-data-breach-investigations-report.pdf)
- 2,643 third parties on average; only 36% assessed; 40% have a backlog (https://ponemonsullivanreport.com/2026/03/state-of-third-party-risk-assessments/)
- 37.4 hours a week spent assessing vendors (https://www.whistic.com/resources/blog/2025-impact-report-takeaways)

**Notes.** Sources and sample sizes are in `docs/IMPACT.md` §2 (Ponemon-Sullivan n = 1,465, https://ponemonsullivanreport.com/2026/03/state-of-third-party-risk-assessments/; Whistic n = 525, https://www.whistic.com/resources/blog/2025-impact-report-takeaways). Show the short source names on the slide and keep the URLs in the notes or a footer.

## 3. The user and the job

**On slide.** A TPRM analyst decides whether a new SaaS vendor may touch customer data. The evidence is spread across a questionnaire, four internal systems and CISA's exploited-vulnerability list. The TPRM lead signs off exceptions.

**Notes.** `docs/IMPACT.md` §1 and §3 (the before/after table). The "today" column marks what is an assumption.

## 4. The solution: one request, five outcomes, brief and action

**On slide.** One onboarding request in. Out: `APPROVE`, `APPROVE_WITH_CONDITIONS`, `REQUEST_INFO`, `ESCALATE` or `DECLINE`, with a cited plain-English brief and the next action drafted under a signed contract.

**Visual.** `docs/img/ui_case.png` (Quillfeather: claim versus record card, KEV bullet). Caption it "sample mode".

**Notes.** `output_examples/sample_mode/example_2_output.json`; the live example is `output_examples/example_1_output.json` (`APPROVE`).

## 5. Architecture

**On slide.** Zetaris USL → Planner → Evidence (ScoutGuard) → Evaluator ⇄ Planner → policy engine → H-MEM precedents → Challenger → brief → signed contract. Models via Nightshift. The policy decides.

**Visual.** The state-machine diagram from `docs/ARCHITECTURE.md`.

**Notes.** Bounds: Evaluator → Planner at most twice, Challenger → Planner once; 600 s budget; every model step has a labelled deterministic fallback (`app/orchestrator.py`).

## 6. Reasoning in action (live trace)

**On slide.** Live run, Pellucid Forms: 12 Zetaris queries, 5 Nemotron calls with receipts, Evaluator sends the Planner back, Challenger asks for a re-plan, policy approves. 159 seconds.

**Visual.** Four trace lines from `logs/examples/live/trace-run-83de5da137c0.jsonl`: a `query_zetaris` line with its `zetaris_request_id`, the Planner `model_call` (`rcpt_req_ltd0d684`), the Evaluator `needs_revision`, the Challenger `request_replan`. The same lines are quoted in `docs/SPONSORS.md`.

**Notes.** One call returned HTTP 502 and fell back; say so if asked. The outcome still matched its label.

## 7. Memory under governance

**On slide.** A lead-approved precedent from Marrowgate lets Tessellate be approved with conditions. Reset memory, or let an analyst set the precedent, and it escalates. Memory changes outcomes only through policy.

**Visual.** The six-step table from `docs/evidence/memory_session.md` (6/6, live).

**Notes.** `logs/examples/session/trace-run-a1c914808974.jsonl` (`precedent_applied`), `app/memory/precedents.py`, `policy/arbiter_policy.v1.yaml`. Monitoring is not on this slide: it was not shipped (see slide 13).

## 8. Zetaris USL

**On slide.** Sources → Lightning REST tables → SchemaStore views → USL `vendor_risk` → agents. One query path; DQ in the layer; 416/416 parity.

**Visual.** `docs/img/zetaris_1.png`, `docs/img/zetaris_3.png`, and the measured comparison from `docs/ZETARIS_USL.md` §4:

| Custom pipeline (mirror) | USL |
|---|---|
| `app/data/duckdb_backend.py` 162 lines plus `app/data/dq.py` 61 lines | `zetaris/sql/03_usl.sql` 81 lines plus `zetaris/dq_rules.yaml` 22 lines |
| One `Q_VENDOR_360` call: 37 ms | One `Q_VENDOR_360` call: 5220 ms (one HTTP round trip, not warmed) |
| Planner reads names only: 275 tokens | Planner reads the USL catalogue with keys and descriptions: 304 tokens |

**Notes.** Parity: `docs/passes/P1-B_parity.json` (`query_layer: usl`, `all_green: true`). DQ: `CTR-30028`, a DPA marked signed with no date. Capture a USL ERD from the Zetaris UI for this slide if possible; none is committed.

## 9. Meterless and NVIDIA

**On slide.** Every model call through Nightshift, with a receipt. Fast lane → Nemotron 3.5 Lightning; deep lane → Nemotron 3.5 Super VL. Plan, extract, critique and challenge run on Nemotron. H-MEM precedents; Scout guard and signed contracts.

**Visual.** The proof table from `docs/evidence/nightshift_proof.json`: `rcpt_req_924f14pn` (fast, Lightning) and `rcpt_req_p412l7ql` (deep, Super VL).

**Notes.** Deviation, said plainly: Super 3 120B is not entitled on this account (404), and a Nightshift app rule coerces both lanes to `auto`; Meterless acknowledged it, fix targeted for Sunday's release (`docs/evidence/nightshift_deviations.md`). Per-step table: `docs/SPONSORS.md`, "Our agents do real work on Nemotron".

## 10. Technical stack and how it was built

**On slide.** Python 3.12, FastAPI, pydantic, DuckDB mirror, Streamlit console. Zetaris REST SQL, Meterless Nightshift, Nemotron. No agent framework: an explicit state machine. Built pass by pass with plans, tests first and a verify hook.

**Notes.** Cursor: `AGENTS.md`, `.cursor/rules/`, `.cursor/commands/`, `.cursor/hooks.json` (stop hook re-runs `verify-pass`), `.cursor/plans/`, parallel worktrees. The per-pass tool and model table is `docs/CURSOR_USAGE.md`: 17 passes in Cursor, three (P14-B, P15, P17) in Claude Code, one not recorded.

## 11. Product visuals

**On slide.** The reviewer console: queue by residual risk, the case brief with claim versus record, the drafted next action, governed precedents.

**Visual.** `docs/img/ui_queue.png`, `docs/img/ui_case.png`, `docs/img/ui_case_next_action.png`, `docs/img/ui_memory.png`. Re-capture with `scripts/capture_ui.py` first and dismiss the Streamlit popup in the committed stills.

**Notes.** Synthetic vendors only. The sidebar shows the Nightshift Runtime URL with the token hidden.

## 12. Results

**On slide.** Live: 5/5 correct, 0 unsafe approvals, 4/4 consistent; 5 of 25 model calls fell back and the decisions still matched. Offline: 16/16. Single-prompt baseline: not measurable through the routing bug.

**Visual.** The eval table from the README block; the workload for one live case (12 queries, 16 quoted claims, 5 model calls, 159 s); the before/after table from `docs/IMPACT.md` §3.

**Notes.** `eval/results_live/20261024T045916036274Z/summary.json`; `docs/EVALUATION.md`. Five live cases give a Wilson 95% interval of 0.57–1.00. Do not present the baseline 0/5 as a win. The capacity range in `docs/IMPACT.md` §5 is an estimate; label it so if shown.

## 13. Future work and the path to production

**On slide.** Future work: real connectors through Zetaris (procurement, CLM, SOC 2 register). SSO and RBAC. Document OCR with NVIDIA NeMo Retriever. Policy authoring UI. Monitoring approved vendors when CISA adds a vulnerability.

**Notes.** Monitoring (P16) was designed but not shipped; it is future work only. `docs/IMPACT.md` §7.
