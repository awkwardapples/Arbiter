# Slide deck outline

Ten slides. The playbook's deck table is thirteen slides; this outline is shorter and still covers all eight required points. Build the deck from this file (Slides or PowerPoint) and export a PDF. On-slide text is about thirty words. Speaker notes hold the file or trace. Do not put keys, `.env`, or real personal data on a slide.

The one-line description, identical to the README opening sentence:

> Auditable reasoning for third-party vendor onboarding: agents gather cited evidence, a versioned policy decides, and the next action is a signed contract.

Track everywhere: Reasoning Architecture. Team: Josh Lennon, solo builder.

`metadata.json` uses a longer description. This deck follows the README sentence. Align the form to the same sentence before submit. See `docs/SUBMISSION.md`.

## Coverage

| Required point | Slides |
|---|---|
| 1 Problem and users | 2 |
| 2 Solution | 3 |
| 3 Workflow / architecture | 4, 5, 6 |
| 4 Technical stack | 7 |
| 5 Sponsor use | 7 |
| 6 What was unique | 6, 8 |
| 7 Product visuals | 9 |
| 8 Results and future | 10 |

There is no competitor slide. The old market-research deck is not in this repo. Do not reconstruct it.

## 1. Title

**On slide.** Arbiter. Track: Reasoning Architecture. Auditable reasoning for third-party vendor onboarding: agents gather cited evidence, a versioned policy decides, and the next action is a signed contract. Josh Lennon, solo.

**Notes.** Form fields: project name Arbiter, track Reasoning Architecture, primary contact Josh Lennon. Repository `https://github.com/awkwardapples/Arbiter`.

## 2. Problem and users

**Point 1.**

**On slide.** Verizon DBIR 2026: third parties are involved in 48% of breaches, up from 30%. The user is a third-party risk analyst. The evidence sits in five systems and a questionnaire.

**Notes.** README "Problem and users", with the Verizon PDF and news URLs. The five systems are procurement, contracts, ITSM, a sanctions watchlist, and the vendor trust portal. Also the public CISA KEV catalogue. Do not add a market-size or competitor claim.

## 3. Solution

**Point 2.**

**On slide.** One request, five outcomes: approve, approve with conditions, request information, escalate, or decline. Facts are cited. A counterfactual says what would change the answer. The next action is a signed contract.

**Notes.** README "What Arbiter does". Company data in the repo is synthetic. CISA KEV is public (CC0). Outcome names in code: `APPROVE`, `APPROVE_WITH_CONDITIONS`, `REQUEST_INFO`, `ESCALATE`, `DECLINE`.

## 4. Workflow

**Point 3.**

**On slide.** Models read. The policy decides. The Evaluator can send the Planner back. The Challenger can force one re-plan or an escalation. It cannot approve.

**Notes.** Diagram: `docs/ARCHITECTURE.md`. Decision code: `app/policy/engine.py`. Authority table: README "Agents". Bounds: at most two evaluator loops and one challenger re-plan.

## 5. Reasoning in action

**Point 3.**

**On slide.** Quillfeather, offline sample `run-3d6b7460d393`. The Evaluator sends the plan back (`needs_revision`, `Q_COMPONENT_KEV`). The vendor says EU. The contract system says US. Outcome: ESCALATE.

**Notes.** Trace `logs/examples/trace-run-3d6b7460d393.jsonl`. The query line is `backend=duckdb`. Say that. Do not call this run a live Zetaris query. Challenger line: `CHALLENGE_T1_UNCORROBORATED`. Optional still `docs/img/ui_1.png` shows the same vendor name on a different session (sidebar Data: zetaris, LLM: auto). It is not this run id.

## 6. Memory under governance

**Points 3 and 6.**

**On slide.** The six example runs record `precedents=0`. A precedent can change a later outcome only through a policy exception and a human approval. The Memory page in the capture is empty.

**Notes.** Quillfeather redecide line: `input_summary` `precedents=0` in the same trace. Governed session, when you run one: `python run.py demo-session`. Still: `docs/img/ui_4.png` (CASE-0007, empty list). `docs/img/ui_6.png` is a blank review form, not a submitted precedent. Do not say memory changed Quillfeather.

## 7. Stack and sponsors

**Points 4 and 5.**

**On slide.** Python 3.12, FastAPI, Streamlit, DuckDB, and Docker. Zetaris is the SQL access point. Meterless runs Nightshift, H-MEM, and Scout. NVIDIA Nemotron is the model family. Built in Cursor.

**Notes.** Stack table: README "Tech stack". Sponsor claims and the trace lines that back them: `docs/SPONSORS.md`. Committed examples are `provider: offline` and `backend: duckdb`. Nightshift model ids and Zetaris request ids appear only on a live run. Do not put a key or the Nightshift Providers tab on the slide.

## 8. What was unique

**Point 6.**

**On slide.** The policy decides. The Evaluator re-checks systems of record. Memory moves an outcome only through a policy exception and a human approval. Every action is signed, and the decision replays.

**Notes.** README "Sponsor technology", the paragraph that starts "What is specific to this design". Replay for the committed approve example: `python run.py replay CASE-0003`. `docs/img/ui_3.png` is a match on CASE-0007, a different case.

## 9. Product visuals

**Point 7.**

**On slide.** Six console frames: Queue, Case, Review, Memory, Audit, and Evaluation. The sidebar says Data: zetaris and LLM: auto. These frames are not the six offline example traces.

**Notes.** Files, in the order a judge sees them in the nav:

- `docs/img/ui_1.png` — Queue. Quillfeather ESCALATE T1, Corvid DECLINE T3.
- `docs/img/ui_2.png` — Case Why. DECLINE, sanctions control C11 false, cited facts. No vendor name on the frame.
- `docs/img/ui_6.png` — Review. CASE-0007, empty form.
- `docs/img/ui_4.png` — Memory. CASE-0007, precedent list empty.
- `docs/img/ui_3.png` — Audit. Replay CASE-0007, `match` true.
- `docs/img/ui_5.png` — Evaluation. "Evaluation results are not published yet." Do not read numbers from this frame.

Synthetic vendors only. No secrets in the frames.

## 10. Results, limits, and later work

**Point 8.**

**On slide.** Offline eval, 15 synthetic cases. `arbiter_offline` is 15/15 accurate, with 0 unsafe approvals. The console Evaluation page is unpublished. JDBC connectors, SOC 2 OCR, policy what-if, KEV deltas, and RBAC are later work, not this build.

**Notes.** Source: `eval/results/20261022T080517661769Z/summary.json`, rendered in the README between the eval markers. git sha `a7228be2efe2bca9f004f981db12c1e8dd53704f`. Mode duckdb / offline. No second system is in that file, so do not show a baseline number. Limits also in README "Limitations": simulated systems, small n, no PDF OCR, outbox is local files. The later-work list is not implemented.
