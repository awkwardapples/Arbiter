# Judge Q&A preparation

Twenty-five likely questions, each with a two-sentence answer and the file or trace to show. Every answer is backed by a committed file.

## Impact and users

| # | Question | Answer | Show |
|---|---|---|---|
| 1 | Who is the user? | A third-party risk analyst at a 500–5,000-person company who owns vendor onboarding decisions, and the TPRM lead who signs off exceptions. Arbiter assembles and cross-checks the evidence so the analyst reviews exceptions instead of building the file. | `docs/IMPACT.md` §1 |
| 2 | How big is the problem? | Third parties are involved in nearly half of breaches, and most organisations assess only about a third of their vendors while carrying a backlog. The cited figures and sources are in the impact doc. | `docs/IMPACT.md` §2 |
| 3 | How much time does it save? | We have not measured that in a real team, so we show it as an estimate with stated assumptions: roughly 5 to 24 hours a week of the hours the Whistic survey reports. What we did measure is one live onboarding: 12 Zetaris queries, 16 quoted claims and a decision in 159 s. | `docs/IMPACT.md` §3 and §5 |
| 4 | Why onboarding, not continuous monitoring? | Onboarding is the control point: the moment the evidence can be checked before access is granted. Re-checking approved vendors when CISA adds a vulnerability was designed but not shipped, and is listed as future work. | `docs/IMPACT.md` §7 |

## Reasoning architecture

| # | Question | Answer | Show |
|---|---|---|---|
| 5 | Is this really multi-agent, or a pipeline? | The Evaluator can send the Planner back up to twice, and the Challenger can force one re-plan or escalate. In live example 1 both loops fired. | `logs/examples/live/trace-run-83de5da137c0.jsonl` (`needs_revision`, `request_replan`) |
| 6 | Who decides the outcome? | Only the versioned policy engine maps facts to an outcome; models plan, extract, critique and challenge. That keeps the decision deterministic and replayable. | `app/policy/engine.py`, `policy/arbiter_policy.v1.yaml` |
| 7 | What if the model is wrong? | A wrong extraction can only leave a control unverified, which lowers the outcome. In an earlier live attempt that turned an `APPROVE` into `REQUEST_INFO`, the safe direction. | `docs/EVALUATION.md`, "Earlier live example" |
| 8 | What if a model call fails? | Every model step has a deterministic fallback that implements real logic, and the trace labels it `fallback`. In the live eval 5 of 25 calls fell back and all five outcomes still matched their labels. | `docs/EVALUATION.md`; the `fallback` line in `docs/SPONSORS.md` |
| 9 | How do you stop prompt injection from vendor documents? | Vendor answers and documents pass ScoutGuard and PII redaction before any model sees them, and a blocked segment escalates the case. The Oakhaven sample shows a planted instruction being blocked. | `app/guard/scout_guard.py`, `logs/examples/trace-run-ac35d0a215a4.jsonl` |
| 10 | Can the Challenger approve something? | No: it can only accept, ask for one re-plan, or escalate. That is enforced in code, not in a prompt. | `app/agents/challenger.py`, `app/orchestrator.py` |
| 11 | How do actions stay safe? | Every side effect needs an HMAC-signed, unexpired execution contract with the required approvals. The live run's outbox write is in its trace. | `app/actions/contracts.py`, `app/actions/executor.py` |
| 12 | Can you replay a decision? | Yes: the audit log is hash-chained, and replay re-runs the policy on the stored facts and compares. `python run.py replay CASE-0003` replays the live example. | `app/audit/replay.py` |

## Memory

| # | Question | Answer | Show |
|---|---|---|---|
| 13 | What does memory change? | A lead-approved precedent lets the policy apply an exception it explicitly allows; the model never chooses to use it. In the live session, Marrowgate's precedent moved Tessellate to `APPROVE_WITH_CONDITIONS`. | `docs/evidence/memory_session.md` |
| 14 | What stops bad precedents? | Only a `tprm_lead` can create one, and `wrong` feedback or a reset removes its effect. The live session shows each of those blocking it. | `docs/evidence/memory_session.md`, steps 4–6 |
| 15 | Is H-MEM really Meterless's engine? | It is a Python port checked against the 13 upstream conformance vectors, which are vendored with their Apache-2.0 notice. The domain adapter is separate. | `tests/conformance/test_hmem_conformance.py`, `vendor/meterless/` |

## Sponsor technology

| # | Question | Answer | Show |
|---|---|---|---|
| 16 | What does Zetaris do that a database would not? | It federates five REST source systems and the public KEV feed into one semantic layer with descriptions, keys and DQ rules, and the agents query only that layer. The Planner reads the USL model as a 304-token catalogue. | `docs/ZETARIS_USL.md`, `zetaris/sql/03_usl.sql` |
| 17 | Is the Zetaris use real or mocked? | Live runs carry a request id on every query, and the parity run compares 416 registry queries against the mirror, all green. Sample mode is a documented fallback that runs the same query ids on a DuckDB mirror. | `docs/passes/P1-B_parity.json`; `zetaris_request_id` lines in `docs/SPONSORS.md` |
| 18 | Why does the deep lane say Super VL, not Nemotron 3 Super? | Our NVIDIA account is not entitled to Nemotron 3 Super (it returns 404), so the deep lane is bound to Nemotron 3.5 Super VL. Separately, a Nightshift app rule coerces both lanes to auto; Meterless acknowledged it, with a fix targeted for Sunday's release. | `docs/evidence/nightshift_deviations.md`, `docs/evidence/nightshift_proof.json` |
| 19 | How do we know Nemotron actually ran? | Every successful call has a Nightshift compute receipt with the routed model in the trace. The proof file has one receipt per lane: Lightning on fast, Super VL on deep. | `docs/evidence/nightshift_proof.json`, `metadata.json` `model_evidence` |
| 20 | Which steps run on Nemotron? | Planning and challenge request the deep lane; claim extraction and critique request the fast lane. In live example 1 all five successful calls were served by Super VL. | `docs/SPONSORS.md`, "Our agents do real work on Nemotron" |
| 21 | How did you use Cursor? | Each pass ran from `AGENTS.md` and project rules, with a plan, tests first and a stop hook that re-runs the pass gate. Three later passes were done in Claude Code, and the per-pass record says which. | `docs/CURSOR_USAGE.md`, `.cursor/` |

## Results and limits

| # | Question | Answer | Show |
|---|---|---|---|
| 22 | Did you beat the single-prompt baseline? | We could not measure it: every live baseline call returned HTTP 502 because the large prompt was routed to Lightning, which returned empty responses. We report it as unmeasured, not as a win. | `docs/EVALUATION.md`, "Discussion" |
| 23 | Isn't n = 5 too small? | Yes for a precision claim: the Wilson interval on 5/5 is 0.57–1.00. It shows the live path works end to end; the offline 16/16 shows the policy and agents on the full test split. | README eval block |
| 24 | Why is a live case so slow? | The median was 141.8 s, almost all of it model calls through Nightshift; the same case offline takes under a second. Faster routing and fewer re-plans are the obvious levers. | `docs/EVALUATION.md` |
| 25 | What would production need? | Real connectors through Zetaris, SSO and RBAC, document OCR, a policy authoring UI and a much larger labelled evaluation. None of these is claimed as built. | `docs/IMPACT.md` §7 |
