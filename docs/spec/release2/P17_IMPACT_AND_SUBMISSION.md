# P17: Impact case, truthful docs, deck and video materials

Starts when P15 has published live numbers (Sun 25 Oct). The human records the video and builds the deck on Mon 26 from these files.

## 1. Goal

Every document a judge reads makes the same four points, in this order:

1. **Impact:** who, what pain (with cited numbers), and what changes in their day.
2. **The track:** data, knowledge, memory and reasoning turned into reliable decisions and actions. Nemotron lanes, Meterless engines, the tool loop.
3. **Proof:** live traces, Nightshift receipts, Zetaris USL request ids, eval versus baseline, replay.
4. **Honest limits.**

The caveat-first tone of the current README, demo script and slides goes. **Accuracy stays absolute**: every claim maps to a file or a committed trace line (enforced by a test).

## 2. Why it scores

Every criterion: Impact (30) is mostly earned here; Demo (15) is the script; Sponsor Tech asks for visibility "in the demo, the deck and the README".

## 3. Deliverables

### 3.1 `docs/IMPACT.md` (new)

1. **The user and the job.**
   - Persona: a TPRM analyst at a 500–5,000-person company, plus the TPRM lead who signs off.
   - The onboarding decision they own.
2. **The problem in numbers** (cite exactly; sources in `R2_00_ASSESSMENT.md` §5):
   - third parties are involved in 48% of breaches (Verizon DBIR 2026);
   - organisations average 2,643 third parties but assess 36%;
   - 40% have an assessment backlog, mostly from incomplete vendor information (67%);
   - 43% of vendor responses need follow-up or remediation (ProcessUnity/Ponemon 2026, n = 1,465);
   - companies spend 37.4 hours a week assessing vendors, and 94% can't assess every vendor they'd like (Whistic 2025, n = 525);
   - organisations average 12 third-party-caused incidents a year.
3. **Before / after, step by step.** A table for one onboarding:

   | Step | Today (manual) | With Arbiter (measured from live runs) |
   |---|---|---|
   | Collect evidence | Open five systems and the questionnaire | Six systems queried through one Zetaris USL; N queries in M seconds |
   | Read answers and documents | – | K claims extracted with quotes; all grounded |
   | Cross-check against records | Usually skipped | Contradictions found (residency, incidents) |
   | Check exploited vulnerabilities | Rarely done | KEV federated join |
   | Decide | Reviewer judgement | Versioned policy; same answer every time; replayable |
   | Follow up | Write the follow-up email | Drafted with exactly the missing questions and what evidence satisfies them |
   | Record | Write it up | Dossier exported; audit chain |

   The "today" column cites sources or is marked as an assumption. The "with Arbiter" column uses P15 numbers only.
4. **What changes in the analyst's day.**
   - The queue is ordered by residual risk.
   - Only exceptions reach a human.
   - Follow-ups are drafted.
   - Precedents travel between analysts under the lead's governance.
   - Approved vendors are re-checked when CISA adds a vulnerability (P16, if shipped).
5. **Illustrative capacity estimate**, clearly labelled as an estimate. Use the cited 37.4 h/week and an assumption table (minutes saved per step, stated as assumptions with ranges) to show the plausible range of hours returned per week. Never present it as measured.
6. **Reliability results** (from P15): Arbiter versus baseline (unsafe approvals, accuracy, consistency, injection), plus what the baseline got wrong in plain words.
7. **Limits and the path to production:**
   - real connectors via Zetaris (JDBC/REST to procurement and CLM; SOC 2 register);
   - SSO and RBAC;
   - document OCR via NVIDIA NeMo Retriever;
   - policy authoring UI.

### 3.2 `README.md` (rewrite; same honesty, better order)

1. Title, badges, one-line description, **demo video link**, quick start (Docker sample mode, three commands).
2. **Why it matters**: three numbers and the user (from IMPACT.md).
3. **Track 3 mapping table**:

   | Track word | Arbiter |
   |---|---|
   | Data | Zetaris USL `vendor_risk`: five systems plus CISA KEV |
   | Knowledge | Versioned policy-as-code |
   | Memory | Meterless H-MEM governed precedents and assessment memory |
   | Reasoning | Planner, Evidence, Evaluator and Challenger tool loop on Nemotron lanes via Nightshift |
   | Reliable | Policy decides; eval versus baseline; replay |
   | Decisions | Five outcomes with briefs |
   | Actions | Signed contracts and approvals; monitoring |

4. **See it work**: live run excerpt (brief, plus trace lines with `zetaris_request_id`, Nemotron `model` and receipt id), plus console screenshots from `scripts/capture_ui.py`.
5. How it works (agents table, loops, policy, memory, guard, contracts).
6. The **Zetaris USL** section (summary of `docs/ZETARIS_USL.md`, with the ERD image).
7. The **Nemotron and Nightshift** section (`docs/evidence/nightshift_proof.json` table; which agent steps run on which lane).
8. Evaluation (generated block).
9. Setup and usage: sample mode first, then live mode, then the commands.
10. Sponsor technology; AI and model usage; data and licensing; third-party licences; limitations; responsible AI; pre-existing components; repo map.

    **AI and model usage must stay exactly true.** Application code was written by Cursor agents. The architecture specs (Release 1 and 2), independent reviews, and the small Release 2 tooling patch (lane ids, markers, opt-in Docker test) were drafted by Claude (Anthropic) outside the repo and applied and committed through Cursor. Say so in one sentence.

### 3.3 Other documents

- **`docs/SPONSORS.md`:** rewrite around live trace lines. **Zetaris** (USL build and reflection link, request ids, DQ). **Meterless** (Nightshift receipts; H-MEM conformance and governed precedents; Scout guard and contracts). **NVIDIA:** a section titled *"Our agents do real work on Nemotron"* listing each LLM step (planning, extraction, critique, challenge, brief), its lane, the model served, and a trace line. **Cursor** (rules, plans, hooks, per-pass reports, parallel worktrees; counts of passes, tests and hook iterations from `docs/cursor-usage/`).
- **`docs/CURSOR_USAGE.md`:** compiled from every `docs/cursor-usage/*.md` (the generator script lives in `scripts/compile_cursor_usage.py`).
- **`metadata.json`:**
  - features only where evidence exists (USL and DQ only if P13 is green);
  - `models` = ids observed in live traces;
  - demo video and deck links;
  - `track_mapping`;
  - `impact` (three cited stats with URLs).
- **`docs/DEMO_SCRIPT.md`:** §4 below, with real run ids.
- **`docs/SLIDES.md`:** §5 below.
- **`docs/QA_PREP.md`:** about 25 judge questions with two-sentence answers and the file or trace to show.
- **`docs/SUBMISSION.md`:** form text (one-line description identical across README, metadata, deck and form; pre-existing components from `docs/PRIOR_WORK.md`; sponsor explanation from SPONSORS).

### 3.4 Video script (target 3:35, hard stop 3:50; the Demo Video Guide's segments)

| Time | Screen | Narration (essence) |
|---|---|---|
| 0:00–0:20 | Title card, then three numbers | "Reasoning Architecture. Third parties are in 48% of breaches; companies assess only 36% of their vendors and 40% have a backlog. Meet the TPRM analyst deciding whether a new SaaS vendor can touch customer data." |
| 0:20–0:40 | Console, New assessment (questionnaire form or vendor picker) | "Arbiter turns that decision into a cited, replayable outcome with the next action drafted. Company data here is synthetic; the vulnerability catalogue is CISA's live feed." |
| 0:40–1:15 | Architecture slide (agents, loops, policy, USL, Nightshift) | "Nemotron agents plan, gather and challenge; a versioned policy decides; H-MEM remembers what humans decided; every action is signed." |
| 1:15–2:05 | **Live run**: Quillfeather case: brief headline, claim-versus-record card (EU versus US), KEV card, timeline with the Evaluator sending the Planner back | "The vendor says EU-only hosting. The Evaluator checks the contract system through Zetaris: US. It also finds FortiOS on CISA's exploited list. Escalate, with the ticket drafted." |
| 2:05–2:30 | **Meterless and Nemotron**: `python run.py llm proof` (Runtime URL shown, token hidden) plus provider proof panel | "One real request through Nightshift: the fast lane is served by Nemotron 3.5 Lightning, the deep lane by Nemotron 3 Super; here is the receipt." |
| 2:30–2:50 | **Zetaris USL**: ERD in Zetaris UI, `Q_VENDOR_360`, DQ result | "Five systems and CISA KEV unified in one semantic layer. The Planner reads this model, a few hundred tokens instead of raw schemas, and a DQ rule caught a DPA marked signed without a date." |
| 2:50–3:15 | **Memory**: Tessellate approved with conditions citing the lead's precedent from Marrowgate; then (if P16) the monitor reopening the MOVEit vendor | "Memory changes decisions only through policy and human sign-off. And when CISA adds a vulnerability, Arbiter remembers who uses it and acts." |
| 3:15–3:35 | Eval table and replay match | "Live on held-out cases: zero unsafe approvals versus N for a single Nemotron prompt with the same data; every decision replays identically. Arbiter: vendor decisions your auditors can replay." |

### 3.5 Slide deck (13 slides; covers all eight required points)

1. Title + track.
2. **Problem with numbers** (point 1).
3. **User and job** (point 1).
4. **Solution: one request, five outcomes, brief + action** (point 2).
5. **Architecture** (point 3).
6. **Reasoning in action** (live trace excerpt) (point 3).
7. **Memory under governance + monitoring** (points 3 and 6).
8. **Zetaris USL: sources → onboard → USL → reflection, with the measured custom-pipeline-versus-USL table** (points 5 and 6).
9. **Meterless + NVIDIA: Nightshift lanes, receipts, which agent steps run on Nemotron** (points 5 and 6).
10. **Technical stack + Cursor workflow** (point 4).
11. **Product visuals** (four console screenshots) (point 7).
12. **Results**: eval versus baseline, workload per case, before/after (points 2 and 8).
13. **Future enhancements and path to production** (point 8).

## 4. Acceptance tests (marker `p17`)

| Id | Test |
|---|---|
| P17-T1 `test_claims` | Every `files` path in `metadata.json` exists. Every feature listed for Zetaris and Meterless maps to an evidence entry (a file plus a committed trace or evidence file). "USL" and "DQ" are listed only if `docs/passes/P1-B_parity.json` has `query_layer == "usl"` and `all_green` |
| P17-T2 | Every trace line quoted in README and SPONSORS exists verbatim in `logs/examples/**` |
| P17-T3 | Every statistic in README, IMPACT and SLIDES has a URL on the same line or in a footnote, from the allowed source list |
| P17-T4 | The one-line description is identical in README, metadata, SLIDES and SUBMISSION |
| P17-T5 | README order of sections per §3.2; the eval block matches the latest summary |
| P17-T6 | `metadata.json` `models` ⊆ model ids found in `logs/examples/live/**` |

## 5. Cursor prompt

```
/start-pass 17
You are implementing P17 of Arbiter Release 2: impact case, truthful README/SPONSORS/metadata, demo script, slide outline and Q&A prep.
Read: AGENTS.md; docs/spec/release2/README.md; docs/spec/release2/R2_00_ASSESSMENT.md (§5 sources); docs/spec/release2/P17_IMPACT_AND_SUBMISSION.md; docs/ZETARIS_USL.md; docs/evidence/*; docs/EVALUATION.md; logs/examples/live/*; docs/cursor-usage/*.
Every claim must map to a file or a committed trace line; numbers come only from committed results; estimates are labelled as estimates with their assumptions; statistics carry their source URL.
Plan Mode: .cursor/plans/P17.md with an outline per document and tests P17-T1..P17-T6. Wait for approval.
Tests first (marker p17) → commit → implement until `python scripts/tasks.py verify-pass --pass 17` is green.
Finish with docs/passes/P17_REPORT.md + docs/cursor-usage/P17.md; push p17-submission; delete .cursor/ACTIVE_PASS; stop.
```
