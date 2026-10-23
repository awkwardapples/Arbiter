# R2-00: Independent assessment of `main` at `fbb5cdc` (23 Oct 2026)

Reviewer: Claude (architect), outside the repo. Method:

- fresh clone and a clean Python 3.12 venv;
- `python scripts/tasks.py verify`;
- the judge path run natively from a fresh clone with **no `.env`** (`SAMPLE_MODE=true`, all six examples posted to `/run`);
- `python run.py demo-session --reset --yes`, `replay` and `audit-verify`;
- the Streamlit console driven headlessly and screenshotted;
- every README / SPONSORS / metadata claim read against code, tests, traces and the P1-B report;
- rubric and requirements taken from the Official Rules, Submission Requirements, Demo Video Guide, Disqualification Checklist, Technical Execution Guide, Strong/Weak examples, the Setup Guide ("What to show judges") and the Opening Ceremony track statement (23 Oct).

## 1. What was verified to work

| Check | Result |
|---|---|
| Test suite | 682 passed, 5 skipped. The single failure is `tests/unit/docker/test_clean_clone.py` when the Docker CLI exists but no daemon runs (see §4, B6) |
| Judge path, native, no `.env`, `SAMPLE_MODE=true` | All six examples return the `expected.json` outcome (APPROVE, ESCALATE, ESCALATE, REQUEST_INFO, DECLINE, APPROVE) in 0.2–0.6 s each. Structured responses and traces are written |
| Governed memory session (offline) | 6/6 steps pass: VND-0011 ESCALATE → lead review creates P-0001 → VND-0012 APPROVE_WITH_CONDITIONS citing P-0001 → reset → ESCALATE → analyst-role precedent rejected → `wrong` feedback retires it |
| Replay / audit chain | `replay CASE-0003` → `match: true` (policy hash, record hash, contract signatures). `audit-verify` → ok |
| Secrets | Secret scan clean. No `.env`/keys tracked |
| H-MEM conformance, Scout set, policy property tests | Green in the suite |
| Commit history | First commit 22 Oct 00:45 UTC (after window). Spec import declared with sha in `docs/PRIOR_WORK.md` |
| Live Nightshift | Real captured fixture `tests/fixtures/meterless_chat.json` (22 Oct 02:41 UTC) |

## 2. Decision

**Not submission-ready. Build Release 2 (passes P13–P17) before recording the video or the deck.**

The engineering core is strong, likely above the field on Technical. But the submission as it stands would lose most of its marks where they are heaviest:

1. **Zetaris USL was never built.** That is now an explicit Zetaris judging requirement: identify sources → onboard → build the USL → reflect on it.
2. **There is no committed evidence of a live run.** No Nemotron model id, Nightshift receipt or Zetaris request id appears in any committed trace, example or eval. That is fatal for the NVIDIA award and weak for Sponsor Tech.
3. **The analyst-facing product shows contradictions and engineer codes.** Impact and UX suffer.
4. **The planned demo, deck and docs are dominated by caveats about missing evidence.** Examples: "precedents=0", "Evaluation page is unpublished", "do not quote a baseline".

All four are fixable in the time left. The architecture does not need to change.

## 3. Rubric, criterion by criterion

### Impact (30): "Consistency with the challenge statements: how effectively does the solution address a meaningful real-world problem for its intended users?"

| Item | Artefact | Verdict | Justification / what's missing |
|---|---|---|---|
| Clear user and real problem | README "Problem and users"; DBIR 2026 citation | **PASS** | TPRM analyst at the onboarding control point; sourced statistic |
| Track 3 consistency ("data, knowledge, memory, reasoning → reliable decisions and actions"; "Nemotron lanes, Meterless engines for memory and long tasks, and the tool loop") | README agents table, ARCHITECTURE | **PARTIAL** | Every word is implemented, but there is no Track-statement mapping in README or slides. Nemotron lanes and memory are not *shown*: the committed runs are offline, with memory off |
| Demonstrated real-world value for the analyst | `output_examples/`, console | **PARTIAL** | Outputs read as rule dumps ("C09 would reach TRUE with Q10, Q11"). There are no quantified workload or time effects, no before/after workflow, and no industry baseline (backlog, follow-up rates, coverage gap) |
| Real product, not a demo (ceremony) | Whole repo | **PARTIAL** | Synthetic world is thin: 2 incidents, 9 documents and 2 components across 32 vendors. "Bring your own vendor" requires hand-written JSON. There is no exportable dossier an analyst would file |
| Reliability claim | `docs/EVALUATION.md` | **FAIL** | Offline only. A single system (no baseline). 15/15 on self-generated data, which reads as tautological. `contradiction_recall` and `failing_control_recall` have *expected = 0*, so the labels are not exercising the hard cases |

*Estimated today: 16–19 / 30.*

### Technical (20): "How well is the solution built, including its technical implementation, reliability and architecture?"

| Item | Artefact | Verdict | Justification / what's missing |
|---|---|---|---|
| Architecture | `app/orchestrator.py` (explicit state machine), `app/policy/engine.py`, typed schemas | **PASS** | Bounded loops, single generator, single data path, signed contracts, replay |
| Implementation quality | 682 tests, CI, ruff, typed pydantic | **PASS** | Unusually thorough for a hackathon |
| Reliability and fallbacks | `FallbackBackend`, `llm_or_fallback`, SAFE_ESCALATE | **PASS** | Verified offline. Live fallback behaviour is unevidenced |
| Decision correctness | `app/policy/engine.py:74`, `app/confidence.py` | **FAIL** | (a) `outcome_reasons` includes the `always` rule, so every ESCALATE/DECLINE also says **"ALL_REQUIRED_CONTROLS_MET"**, and the console shows it. (b) Coverage counts a control as covered if *any* referenced key is verified, so REQUEST_INFO cases show **Confidence 100%**. (c) Counterfactuals are duplicated (C09 twice) |
| LLM path in production use | `app/agents/*` | **PARTIAL** | Code exists with validators, but no committed run shows extraction, critique, challenge or report text produced by Nemotron, or how often validators reject it |
| Reproducibility evidence | `docs/passes/clean-clone-2026-10-2{2,3}.md` | **FAIL (evidence)** | Both committed reports are failures: 22 Oct step 4 trace check; 23 Oct "docker daemon not running". Running the test suite **overwrites** the committed report (test side effect). The native judge path works (verified here) |

*Estimated today: 14–16 / 20.*

### Innovation (15): "How original or creative is the approach to solving the problem?"

| Item | Artefact | Verdict | Justification / what's missing |
|---|---|---|---|
| Neuro-symbolic split (models read, policy decides) | engine and agents | **PASS** | Original in this field |
| Governed memory (H-MEM precedent only via policy exception plus human role) | `app/memory/precedents.py`, `demo-session` | **PARTIAL** | Works, but appears nowhere in examples, slides or the demo plan, which actively says not to claim it |
| Evaluator verifies vendor claims against systems of record | evaluator, facts | **PASS** | Visible in trace `run-3d6b7460d393` |
| Semantic-layer-driven agents | – | **FAIL** | Planner reads a registry catalogue, not the USL model. The ceremony framed the USL's "expressive power in a compact format" as the reason it matters for agents |

*Estimated today: 9–11 / 15.*

### Demo (15): "How clearly and effectively does the demo show the solution, its functionality, and the value it provides to the intended users?"

| Item | Artefact | Verdict | Justification / what's missing |
|---|---|---|---|
| Video | – | **FAIL (not recorded)** | – |
| Script | `docs/DEMO_SCRIPT.md` | **FAIL** | Built around offline JSON traces and stills from other sessions, with "do not say" columns. It shows no live Nightshift request, no Zetaris request id, no memory changing a decision, and no eval comparison |
| Setup Guide "What to show judges" (app solving a problem, Meterless provider connection, one real request through Nightshift returning a result, Runtime URL shown with keys hidden) | – | **FAIL** | No artefact yet. `run.py preflight` exists but no proof capture |

*Estimated if recorded from the current script: 7–9 / 15.*

### Product & UX (10): "How intuitive, accessible, and easy to use is the product for its intended users?"

| Item | Artefact | Verdict | Justification / what's missing |
|---|---|---|---|
| Console structure | `ui/` (New assessment, Cases, Case, Review, Precedents, Audit, Evaluation) | **PASS** | Clean, consistent, keyboard-reachable |
| Language for the intended user | Case page | **FAIL** | SCREAMING_CASE reason codes, the contradictory "ALL_REQUIRED_CONTROLS_MET", fact ids (`F-C01-1`), and evidence chips like `trust_portal · Q_SUBMISSION_ANSWERS · answer_id=…`. There is no plain-English headline or "why" |
| Next action in the flow | Case page | **PARTIAL** | Contract state shown; the drafted email or ticket text is not front and centre |
| Own-vendor intake | New assessment | **PARTIAL** | JSON paste; no questionnaire form |
| Screenshots | `docs/img/ui_*.png` | **PARTIAL** | From the P5-A era (dark theme, older copy). Not the current console |

*Estimated today: 5–6 / 10.*

### Sponsor Tech (10): "How effectively does the solution use the sponsors' technology … make the integration visible in the demo, the deck and the README."

| Sponsor | Requirement | Artefact | Verdict | Justification / what's missing |
|---|---|---|---|---|
| Zetaris | Required; judges want sources identified → onboarded → **USL built** → reflection; custom pipeline vs USL | `zetaris/sql/*`, `docs/passes/P1-B_REPORT.md` | **FAIL** | REST tables and views work (parity 384/384). **`COMPILE USL` failed once and was not retried.** Zetaris DQ was never registered (DQ parity 0/5). KEV in Zetaris reads the repo's snapshot, not CISA's feed. No reflection document. `metadata.json` lists "USL model vendor_risk" and "DQ rules", and `docs/SPONSORS.md` says the sources are "compiled into the USL". Those are **overclaims** today, an integrity risk under AI Usage Policy §4.4 |
| Meterless | Required; Nightshift as primary provider; engines | `app/llm/providers/meterless.py`, `app/memory/hmem/`, Scout subset | **PARTIAL** | Strong code and conformance. No committed live trace. `METERLESS_MODEL_DEEP` points at a raw model id rather than a routing mode |
| NVIDIA (Nemotron award) | "Make it clear your agent does real work using the Nemotron model" | `tests/fixtures/meterless_chat.json` | **PARTIAL** | The only evidence is a 2-line `{"ok": true}` fixture. In it Nightshift **coerced the deep request to `auto` → Nemotron 3.5 Lightning** (`mode_coerced: true`, `routed_mode: auto`), so the Super lane was never used. The README admits no model id appears in any trace |
| Cursor | Used as dev environment | `.cursor/`, `docs/cursor-usage/`, plans, pass reports | **PASS** | Exemplary evidence |

*Estimated today: 5–6 / 10.*

**Estimated total as-is: about 56–67 / 100.** After Release 2 the realistic range is about 78–86. The biggest swings are Sponsor Tech (+3), Demo (+5), Impact (+5), UX (+3) and Innovation (+2).

## 4. Other checks requested

| Check | Verdict | Notes |
|---|---|---|
| Pre-existing declaration (`docs/PRIOR_WORK.md`) vs form | **PASS** | Covers design docs (with import sha `b3c720d`), prior prototype (no code), research slides, third-party material, and no pre-window data. Paste §§1–5 into the form verbatim. Add a line for the Zetaris *getting-started* guides if any are copied in (currently none) |
| Sponsor attribution present and specific | **PARTIAL** | Files and lines are named, but every live claim is caveated as "not in this file". USL/DQ are overclaimed (above) |
| Reproducibility (docker run, clone + run) | **PARTIAL** | The native judge path works from a fresh clone with no `.env` (verified). Docker: the CI job exists and the 22 Oct report shows build + 6/6 examples, but **no committed passing report**. The test overwrites the committed evidence file (B5). I could not build here (Docker Hub blocked from my sandbox) |
| README claims backed by file, test or trace | **PARTIAL** | The agent loop, replay, guard, fallbacks and sample mode are backed. Not backed: "compiled into the USL" (SPONSORS), "USL model vendor_risk" / "DQ rules" (metadata), deep lane = Nemotron Super (contradicted by the fixture), and Zetaris "SQL access point" in live mode (true only for views; no live trace committed) |
| Rubric items not in the repo | – | Demo video; slide deck; live evidence; USL; USL reflection; Track-statement mapping; quantified impact; Nightshift "one real request" proof; baseline comparison; analyst-readable output |

### Bugs found (all assigned in Release 2)

| Id | Where | Bug | Pass |
|---|---|---|---|
| B1 | `app/policy/engine.py:74` | `always` rule's `ALL_REQUIRED_CONTROLS_MET` is appended to every outcome's reasons | 14a |
| B2 | `app/confidence.py` (`covered = … any(...)`) | Coverage is true if any referenced key is verified, so UNKNOWN controls count as covered | 14a |
| B3 | counterfactuals | Duplicate entries per control (C09 twice) | 14a |
| B4 | `zetaris/sql/03_usl.sql` | `ACTIVATE`/`REGISTER DQ`/`RUN DQ` use unqualified names; the verified Zetaris examples use `lightning.metastore.<ns>.<usl>.<table>` | 13 |
| B5 | `tests/unit/docker/test_clean_clone.py` | Writes into committed `docs/passes/clean-clone-*.md` | 15 |
| B6 | same test | Runs (and fails) when the docker CLI exists but no daemon is reachable; should skip | 15 |
| B7 | Nightshift app rule for `arbiter` | Deep requests coerced to `auto` (Lightning) | 15 (human, Nightshift Console) |
| B8 | `data/evals/labels.jsonl`, `data/evals/splits.json` | `expected_failing_controls` is empty for **all 32** labels. `expected_contradiction_keys` is set only for VND-0007 and VND-0023 (S07 incident contradictions unlabelled). **Both S06 vendors landed in the calibration split**, so the test split has no contradiction case and recall metrics are undefined | 15 |
| B9 | Docs | USL/DQ overclaims in `docs/SPONSORS.md`, `metadata.json`, `docs/ARCHITECTURE.md` | 13 makes them true; 17 verifies |

## 5. Sources used for the Impact case (verified 23 Oct 2026)

- Verizon 2026 DBIR (third-party involvement 48%), as cited in the README.
- Whistic, *2025 TPRM Impact Report* (n = 525): the average company spends **37.4 hours per week** assessing vendors; **94%** don't assess all the vendors they'd like for lack of resources; **84%** of assessment responses need follow-up; 94% would use AI to summarise documents such as SOC 2 reports. https://www.whistic.com/resources/blog/2025-impact-report-takeaways
- ProcessUnity *State of Third-Party Risk Assessments 2026*, reported by Ponemon-Sullivan (n = 1,465): organisations average **2,643 third parties** and assess **36%**; **40%** have an assessment backlog (incomplete vendor information 67%, lack of response 64%, limited resources 62%); **43%** of responses need follow-up or remediation; average **12 third-party-caused incidents** a year; **60%** say an assessment takes 4 months to over a year end to end. https://ponemonsullivanreport.com/2026/03/state-of-third-party-risk-assessments/
