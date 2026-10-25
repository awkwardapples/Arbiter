# Slide deck outline

Twenty-three slides: the outline of the submission deck. Keep on-slide text to about thirty words. Speaker notes hold the file or trace behind each claim. No keys, `.env` or real personal data on any slide. Slides 4 and 6 reuse refreshed material from the earlier market-research deck (`docs/PRIOR_WORK.md`).

The one-line description, identical in the README, `metadata.json`, this deck and the submission form:

> Auditable reasoning for third-party vendor onboarding: agents gather cited evidence, a versioned policy decides, and the next action is a signed contract.

Track: Reasoning Architecture. Team: Josh Lennon, solo builder.

## Coverage

Judging rubric:

| Criterion | Weight | Slides |
|---|---:|---|
| Impact (30) | 30 | 2–7, 8, 21 |
| Technical (20) | 20 | 10–14, 16, 21 |
| Innovation (15) | 15 | 11, 12, 14, 18 |
| Demo (15) | 15 | 18, 19 (and the video) |
| Product & UX (10) | 10 | 9, 18–20 |
| Sponsor Tech (10) | 10 | 13, 15, 20 |

The eight required points:

| Required point | Slides |
|---|---|
| 1 Problem and users | 2–7 |
| 2 Solution | 8, 9 |
| 3 Workflow and architecture | 10–14 |
| 4 Technical stack | 16 |
| 5 Sponsor use | 13, 15 |
| 6 What was unique | 11, 12, 14, 17 |
| 7 Product visuals | 18–20 |
| 8 Results and future | 21, 22 |

## 1. Title

**On slide.** Arbiter. Track: Reasoning Architecture. "Auditable reasoning for third-party vendor onboarding: agents gather cited evidence, a versioned policy decides, and the next action is a signed contract." Josh Lennon.

**Visual.** `docs/img/arbiter_logo.png`.

## 2. Third parties are where breaches start

**On slide.** Third parties are involved in 48% of breaches (Verizon 2026 DBIR, https://www.verizon.com/business/resources/Te26/reports/2026-dbir-data-breach-investigations-report.pdf).

**Notes.** `docs/IMPACT.md` §2.

## 3. Nobody can assess them all

**On slide.** 2,643 third parties on average; only 36% assessed; 40% have a backlog (ProcessUnity / Ponemon-Sullivan 2026, https://ponemonsullivanreport.com/2026/03/state-of-third-party-risk-assessments/).

**Notes.** Sample size n = 1,465 (https://ponemonsullivanreport.com/2026/03/state-of-third-party-risk-assessments/). Keep the short source name on the slide and the URL in a footer.

## 4. The user and the job

**On slide.** A TPRM analyst at a 500–5,000-person company decides whether a new SaaS vendor may touch customer data. The TPRM lead signs off the exceptions.

**Notes.** Refreshed from the earlier research deck (`docs/PRIOR_WORK.md`). Persona: `docs/IMPACT.md` §1.

## 5. Today's workflow

**On slide.** A questionnaire, four internal systems and CISA's exploited-vulnerability list, opened one by one. Companies spend 37.4 hours a week assessing vendors (Whistic 2025, https://www.whistic.com/resources/blog/2025-impact-report-takeaways).

**Notes.** The "today" column of `docs/IMPACT.md` §3 marks which steps are assumptions.

## 6. What existing tools do

**On slide.** Questionnaire portals collect answers; security-rating feeds score the outside. Neither checks the vendor's answers against the company's own contracts, tickets and inventories.

**Notes.** Refreshed from the earlier research deck (`docs/PRIOR_WORK.md`). Name no competitor that is not in that deck.

## 7. The gap

**On slide.** The hard part is not the decision. It is assembling and cross-checking evidence from systems that do not talk to each other, then proving later why the decision was made.

**Notes.** `docs/IMPACT.md` §2, last paragraph.

## 8. The solution: one request, five outcomes

**On slide.** One onboarding request in. Out: `APPROVE`, `APPROVE_WITH_CONDITIONS`, `REQUEST_INFO`, `ESCALATE` or `DECLINE`, with a cited plain-English brief and the next action drafted under a signed contract.

**Notes.** All six inputs land on their labelled outcome, live (examples 2–5) or in sample mode (`output_examples/`).

## 9. The brief and the next action

**On slide.** "Escalate to the TPRM lead: Quillfeather Payroll Cloud Ltd says EU, but its contract (CTR-30007) shows US." Claim versus record, the KEV finding, the drafted ticket.

**Visual.** `docs/img/console_case_decision.png`.

**Notes.** Live example 2, `output_examples/example_2_output.json` (`run-211916c1544d`).

## 10. Architecture

**On slide.** Zetaris USL → Planner → Evidence (ScoutGuard) → Evaluator ⇄ Planner → policy engine → H-MEM precedents → Challenger → brief → signed contract. Models via Nightshift. The policy decides.

**Visual.** The state-machine diagram from `docs/ARCHITECTURE.md`.

## 11. Agents that check each other

**On slide.** The Evaluator sends the Planner back when evidence is missing (at most twice). The Challenger attacks the candidate decision and can only re-plan or escalate.

**Notes.** Live example 2: two send-backs, then a Challenger re-plan and escalation (`logs/examples/live/trace-run-211916c1544d.jsonl`, `needs_revision`, `request_replan`).

## 12. Models read; the policy decides

**On slide.** Nemotron plans, extracts quoted claims, critiques and challenges. A versioned policy (`arbiter_policy.v1`) maps facts to the outcome. A worse extraction can lower an outcome, never raise it.

**Notes.** `app/policy/engine.py`, `policy/arbiter_policy.v1.yaml`. The trace's `decide` line names the failing and unknown controls.

## 13. Zetaris USL: one place to ask

**On slide.** Five systems and CISA KEV in one Unified Semantic Layer, `vendor_risk`. The Planner reads it as a 304-token catalogue. A DQ rule catches a DPA marked signed without a date. Parity 416/416.

**Visual.** `docs/img/console_sources.png`; `docs/img/zetaris_1.png`.

**Notes.** `docs/ZETARIS_USL.md`; `docs/passes/P1-B_parity.json` (`query_layer: usl`, `all_green: true`); DQ: `CTR-30028`.

## 14. Memory under governance

**On slide.** A lead-approved precedent from Marrowgate lets Tessellate be approved with conditions. Reset memory, or let an analyst set the precedent, and it escalates. Memory changes outcomes only through policy.

**Visual.** The six-step table from `docs/evidence/memory_session.md` (6/6, live).

**Notes.** `logs/examples/session/trace-run-a1c914808974.jsonl` (`precedent_applied`).

## 15. Sponsor technology

**On slide.** Zetaris: the USL, DQ and the federated KEV join. Meterless: Nightshift receipts on every call, H-MEM, the Scout guard and signed contracts. NVIDIA: Nemotron 3.5 Super VL and Lightning do the reasoning steps.

**Visual.** The proof table from `docs/evidence/nightshift_proof.json`: `rcpt_req_936ew345` (fast, Lightning) and `rcpt_req_wu3r6jyf` (deep, Super VL).

**Notes.** Deviation, said plainly: Super 3 120B is not entitled on this account (404), and a Nightshift app rule still coerces both lanes to `auto`; Meterless acknowledged it and the fix had not reached this build on 25 October (`docs/evidence/nightshift_deviations.md`). Per-step table: `docs/SPONSORS.md`.

## 16. Built to be trusted

**On slide.** Vendor text is data: ScoutGuard blocks injection before any model sees it. No action without an HMAC-signed contract. Every decision replays from a hash-chained audit log.

**Notes.** Live example 3 (Oakhaven): a planted instruction blocked (`logs/examples/live/trace-run-1b185078f01b.jsonl`). Stack: Python 3.12, FastAPI, pydantic, DuckDB mirror, React console; no agent framework, an explicit state machine. Built pass by pass with plans, tests first and a verify hook (`docs/CURSOR_USAGE.md`).

## 17. Honest by construction

**On slide.** When a model call fails, the step falls back to deterministic logic and the trace says `fallback`. Sample mode is labelled. Every number in the deck comes from a committed file.

**Notes.** Live example 2 has one labelled HTTP 502 fallback; the outcome still matched its label.

## 18. The bench: watching the agents work

**On slide.** The live run, as it happens: agents, the records they read, every send-back and every contradiction.

**Visual.** `docs/img/console_run_mid.png` (bench mid-run).

**Notes.** The graph is the trace, streamed (`/runs/{run_id}/events`); recordings are labelled with their date.

## 19. The ruling

**On slide.** The policy rules Escalate. The brief, the claim-versus-record card and the drafted ticket are one click away.

**Visual.** `docs/img/console_live_ruling.png`.

## 20. Sources and provider

**On slide.** The USL as the agents see it; the Nightshift lanes with their latest receipts, Runtime URL shown, token hidden.

**Visual.** `docs/img/console_sources.png`, `docs/img/console_provider.png`.

## 21. Results

**On slide.** Live: 10/10 correct on ten held-out cases, 0 unsafe approvals, 4/4 consistent. 10 of 21 model calls fell back and every decision still matched. Offline: 16/16. Single-prompt baseline: not measurable through the routing bug.

**Visual.** `docs/img/console_evaluation.png`; the before/after table from `docs/IMPACT.md` §3.

**Notes.** `eval/results_live/20261025T153035975818Z/summary.json`; `docs/EVALUATION.md`. Ten live cases give a Wilson 95% interval of 0.72–1.00. Six of the ten cases had no successful model call; say so if asked. Do not present the baseline 0/10 as a win, or the lower median as a speed-up. The capacity range in `docs/IMPACT.md` §5 is an estimate; label it so if shown.

## 22. Limits and next

**On slide.** Limits: synthetic company data, one decision type, small live n, Nightshift lane routing still coerced. Future work: real connectors through Zetaris, SSO and RBAC, document OCR, a policy authoring UI, and monitoring approved vendors when CISA adds a vulnerability.

**Notes.** Monitoring (P16) was designed but not shipped; it is future work only. `docs/IMPACT.md` §7.

## 23. Close

**On slide.** Arbiter: vendor decisions your auditors can replay. Repository, video and the one-line description.

**Visual.** `docs/img/arbiter_logo.png`.
