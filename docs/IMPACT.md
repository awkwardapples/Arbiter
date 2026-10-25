# Impact

Who Arbiter is for, what it changes in their day, and what is measured versus estimated. Industry figures carry their source; numbers about Arbiter come only from committed runs (`logs/examples/live/`, `eval/results_live/`, `docs/evidence/`).

## 1. The user and the job

- **The analyst.** A third-party risk management (TPRM) analyst at a 500–5,000-person company. A business owner wants a new SaaS vendor that will process customer or employee data. The analyst owns the onboarding decision: approve, approve with conditions, ask for more information, escalate, or decline.
- **The lead.** The TPRM lead signs off exceptions and declines, and decides which past decisions may be reused as precedent.
- **The evidence.** The vendor's questionnaire and documents, plus four internal systems: procurement, the contract system (CLM), the service desk (ITSM) and the sanctions watchlist. Also the public CISA Known Exploited Vulnerabilities (KEV) catalogue.

## 2. The problem in numbers

- Third parties are involved in 48% of breaches.[^dbir]
- Organisations average 2,643 third parties but assess only 36% of them.[^ponemon]
- 40% have an assessment backlog, and 67% of those blame incomplete vendor information.[^ponemon]
- 43% of vendor responses need follow-up or remediation.[^ponemon]
- Organisations average 12 third-party-caused incidents a year.[^ponemon]
- Companies spend 37.4 hours a week assessing vendors.[^whistic]
- 94% cannot assess every vendor they would like to, for lack of resources.[^whistic]

The bottleneck is not the decision itself. It is assembling and cross-checking evidence from systems that do not talk to each other, then chasing the vendor for what is missing.

## 3. Before and after, one onboarding

"Today" is the manual process. Where a step is not covered by a cited source it is marked *assumption*. "With Arbiter" uses only committed live runs: example 2, Quillfeather Payroll Cloud Ltd (`logs/examples/live/trace-run-211916c1544d.jsonl`, 25 October 2026), unless another run is named.

| Step | Today (manual) | With Arbiter (measured from live runs) |
|---|---|---|
| Collect evidence | Open the questionnaire and four internal systems, one by one (*assumption*) | 14 registry queries through one Zetaris USL, 21.9 s of Zetaris time in total, each with a request id |
| Read answers and documents | Read every answer and attachment (*assumption*) | 16 claims extracted from 16 answers, each with a verbatim quote; none discarded at grounding |
| Cross-check against records | Usually skipped (*assumption*); incomplete vendor information is the top backlog cause, cited by 67%[^ponemon] | The Evaluator checks claims against systems of record and found the residency contradiction: the vendor says EU, contract `CTR-30007` says US |
| Check exploited vulnerabilities | Rarely done (*assumption*) | KEV joined to the vendor's declared components inside Zetaris: 15 known-exploited FortiOS vulnerabilities, one query with one request id |
| Decide | Reviewer judgement | Versioned policy (`policy/arbiter_policy.v1.yaml`); 4/4 live consistency repeats identical; every decision replays from the audit log |
| Follow up | Write the follow-up by hand; 43% of responses need one[^ponemon] | Next action drafted with the missing questions and what evidence would satisfy them (`output_examples/`) |
| Record | Write it up (*assumption*) | Brief, dossier export (`app/dossier.py`) and a hash-chained audit entry (`python run.py audit-verify`) |

The live run took 228 s end to end; 206 s of it was model calls through Nightshift. It escalated to the TPRM lead with the ticket drafted. The analyst's time goes on the exceptions the policy sends to a person, not on assembling the file.

## 4. What changes in the analyst's day

- **The queue is ordered by residual risk.** The console's Cases page sorts by residual risk, so the T1 escalation is first (`docs/img/ui_queue.png`).
- **Only exceptions reach a human.** `APPROVE` with every required control verified needs no review. Escalations and declines route to the lead.
- **Follow-ups are drafted.** `REQUEST_INFO` comes with the exact questions and the evidence that would close each one.
- **Precedents travel under governance.** A lead-approved decision becomes a precedent another analyst's case can use, but only where the policy allows the exception. The live memory session (`docs/evidence/memory_session.md`) moved Tessellate to `APPROVE_WITH_CONDITIONS` on Marrowgate's precedent, and blocked it after a reset, an analyst-role precedent, or `wrong` feedback.
- **Every decision is replayable.** An auditor can replay a case and get the same outcome from the same facts.

## 5. Illustrative capacity estimate (not measured)

This is an **estimate**, built from one cited figure and stated assumptions. It is **not measured**: Arbiter has not been run in a real TPRM team.

Starting point: companies spend 37.4 hours a week assessing vendors.[^whistic]

| Step | Assumption: analyst minutes saved per onboarding |
|---|---|
| Collect evidence from the systems | 20–40 |
| Read answers and documents for claims | 15–30 |
| Cross-check claims against records | 10–30 |
| Check components against KEV | 5–15 |
| Draft the follow-up or ticket | 10–20 |
| Write up the decision | 10–20 |
| **Total** | **70–155** |

| Assumption | Low | High |
|---|---|---|
| Onboardings per week for the team | 5 | 10 |
| Minutes saved per onboarding (table above) | 70 | 155 |
| Analyst minutes added to review each Arbiter brief | 15 | 10 |

Arithmetic: low = 5 × (70 − 15) = 275 minutes, about 4.6 hours; high = 10 × (155 − 10) = 1,450 minutes, about 24 hours. On these assumptions Arbiter would return roughly **5 to 24 hours a week** of the 37.4 hours cited.[^whistic] The range is wide because the inputs are assumptions; a pilot would replace them with measurements.

## 6. Reliability results

From the live evaluation (`docs/EVALUATION.md`, `eval/results_live/20261024T045916036274Z/summary.json`):

| System | n | Correct | Unsafe approvals | Notes |
|---|---:|---:|---:|---|
| Arbiter, live | 5 | 5/5 | 0/5 | 5 of 25 model calls fell back to deterministic logic (HTTP 502); 4/4 repeats consistent |
| Single-Nemotron baseline, live | 5 | not measured | – | All 9 calls returned HTTP 502 from Nightshift's forced `auto` routing |
| Arbiter, offline | 16 | 16/16 | 0/16 | Full test split, DuckDB mirror, deterministic fallback |

**What the baseline got wrong, in plain words.** Nothing that can be fairly judged. The baseline sends the whole policy and every piece of evidence in one prompt. Nightshift's app rule routed that large prompt to Nemotron 3.5 Lightning, which returned an empty response every time. So its 0/5 measures the routing problem (`docs/evidence/nightshift_deviations.md`), not a single model's judgement, and it is not counted as an Arbiter win.

**What the architecture guarantees regardless.** A model only plans, extracts, critiques and challenges; the policy decides. When a live call failed, the step fell back and the outcome still matched its label. In an earlier live attempt, a weaker extraction left two controls unknown and the outcome dropped to `REQUEST_INFO`. It lowered the outcome; it could not raise it.

Injection: vendor text passes ScoutGuard before any model sees it. In the live run of example 3 (Oakhaven), ScoutGuard blocked the document segment carrying a planted instruction (score 0.92), no model saw it, and the case escalated (`logs/examples/live/trace-run-1b185078f01b.jsonl`).

## 7. Limits and the path to production

- **Real connectors through Zetaris.** Replace the simulator with JDBC and REST sources for procurement and CLM, and a SOC 2 report register. The agents and the registry do not change; only the USL's source tables do.
- **SSO and RBAC.** Today the reviewer roles are strings in the policy. Production needs identity-backed roles for analyst and lead.
- **Document OCR.** Vendor PDFs (SOC 2 reports, certificates) through NVIDIA NeMo Retriever, so claims can be quoted from the documents themselves.
- **Policy authoring UI.** The policy is versioned YAML; a TPRM lead should be able to change a threshold with review and a new version.
- **Re-checking approved vendors.** Watching CISA KEV for new entries that hit an approved vendor's components was designed (P16) but not shipped; it is future work.
- **Bigger evaluation.** Five live cases show the path works; a pilot needs hundreds of real, labelled onboardings.

[^dbir]: Verizon, 2026 Data Breach Investigations Report. https://www.verizon.com/business/resources/Te26/reports/2026-dbir-data-breach-investigations-report.pdf
[^ponemon]: ProcessUnity, State of Third-Party Risk Assessments 2026, reported by Ponemon-Sullivan, n = 1,465. https://ponemonsullivanreport.com/2026/03/state-of-third-party-risk-assessments/
[^whistic]: Whistic, 2025 TPRM Impact Report, n = 525. https://www.whistic.com/resources/blog/2025-impact-report-takeaways
