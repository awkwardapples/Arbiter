# Release 3, phase one: the state of `main` at `fd1b19e` (24 Oct 2026, 10:30 BST)

An independent review of `github.com/awkwardapples/Arbiter` after Release 2 (P13, P14-A, P14-B, P15, P17; P16 not built). It checks what works, whether every claim in the README, `docs/SPONSORS.md`, `docs/IMPACT.md` and `metadata.json` is true, and how the entry scores against the judging rubric today.

## 1. Method

1. Fresh clone of `main` (`fd1b19e`, 145 commits; the first commit `b3c720d` is after the window opened).
2. `python scripts/tasks.py verify` on Python 3.12.3 with the pinned requirements.
3. **Judge path**: a second fresh clone with no `.env`, `SAMPLE_MODE=true LLM_PROVIDER=offline python run.py serve`, then all six `input_examples` posted to `/run`, then `demo-session`, `audit-verify`, `replay` and the dossier.
   - Docker image pulls are blocked in my sandbox. The committed `docs/passes/clean-clone-2026-10-24.md` records a Docker pass of all 8 steps on your machine.
4. Every live claim was traced to a committed file:
   - `logs/examples/live/`, `logs/examples/session/`, `eval/results_live/`, `docs/evidence/`, `docs/passes/P1-B_parity.json`;
   - the arithmetic was re-run from the trace lines.
5. The console was read from code and from the committed screenshots. CI status could not be read, because the GitHub API is blocked from my sandbox.

## 2. What works (verified)

| Area | Result | Evidence |
|---|---|---|
| Test suite | **842 passed**, 7 skipped; lint, secret scan and hardcode check clean | `python scripts/tasks.py verify`. One Streamlit AppTest (`test_p10_new_assessment_how_to_use`) timed out at 3 s under load on the first run and passed on rerun; it is a flaky timeout, not a defect |
| Judge path, sample mode | 6/6 outcomes match `input_examples/expected.json`, 0.26–0.44 s each | Fresh clone, no `.env` |
| Analyst output | The Release 2 bugs are fixed: no stray `ALL_REQUIRED_CONTROLS_MET`; confidence names the unverified controls; plain-English briefs; drafts; dossier | Example 2 brief: "Escalate to the TPRM lead: Quillfeather Payroll Cloud Ltd says EU, but its contract (CTR-30007) shows US." |
| Governed memory | `demo-session` 6/6 offline, and 6/6 live (`docs/evidence/memory_session.md`) | Precedent P-0001 moves Tessellate to APPROVE_WITH_CONDITIONS; reset, analyst role and `wrong` feedback all block it |
| Audit | `audit-verify` ok. Replay matches on machine decisions (CASE-0003, CASE-0007) | See B10 for reviewed cases |
| Zetaris USL | Built and activated: `vendor_risk`, 10 tables, descriptions, keys, 5 DQ rules. Parity `query_layer: usl`, `all_green: true`, 416/416. DQ flags `CTR-30028` | `docs/ZETARIS_USL.md`, `docs/passes/P1-B_parity.json` |
| Nemotron through Nightshift | Live example 1: 6 model calls (5 served by Nemotron 3.5 Super VL with receipts, 1 HTTP 502 fallback) and 12 Zetaris queries with request ids. The proof file shows both lanes served by Nemotron | `logs/examples/live/trace-run-83de5da137c0.jsonl`, `docs/evidence/nightshift_proof.json` |
| Agent behaviour in live traces | The Evaluator sends the Planner back. The Challenger's Nemotron call raises `CHALLENGE_UNCORROBORATED_CLAIM` and forces a re-plan. A failed call falls back and is labelled. Every step is logged | Same trace, lines 45, 64, 67 |
| Hero case already ran live | **Quillfeather (VND-0007) ran live in the evaluation:**<ul><li>two Evaluator send-backs;</li><li>the 15-row KEV join through Zetaris;</li><li>the residency contradiction (EU vs US, `CTR-30007`) with its Zetaris request id;</li><li>a Challenger re-plan, then escalation;</li><li>131 s</li></ul> | `eval/results_live/20261024T045916036274Z/traces/trace-run-257c86984507.jsonl` |
| Clean clone with Docker | All 8 steps pass | `docs/passes/clean-clone-2026-10-24.md` |
| Honesty | The lane deviation, the vendor acknowledgement, the unmeasured baseline and the sample-mode framing are all stated plainly | README "Nemotron and Nightshift", `docs/evidence/nightshift_deviations.md` |

## 3. Claims audit

Every quantitative or capability claim in README, SPONSORS, IMPACT, metadata and the demo script was checked. The ones below are **wrong, stale or inconsistent**. Everything else checked was correct, including: USL parity 416/416; 12 queries; the 304-token catalogue; 5 Nemotron calls with receipts; the deviation; memory-session counts (17 calls, 10 ok, 7 fallback); eval figures (5/5, 0 unsafe, 4/4 consistency, 5 of 25 fallbacks, p50 141.8 s); 15 KEV rows for Quillfeather; DQ `CTR-30028`; the cited industry statistics.

| Id | Claim (file) | Finding | Fix |
|---|---|---|---|
| C1 | "12 registry queries through one Zetaris USL, **33 s** of Zetaris time" (`docs/IMPACT.md` §3) | **Wrong.** The trace logs each query twice (`data/query_zetaris` and `*/query_run`, same latency). The 12 queries took **16.6 s** | P19-F1 |
| C2 | "Every decision replays from the audit chain" (README Track 3 table and Responsible AI); "An auditor can replay a case and get the same outcome" (IMPACT §4) | **False for any case a human reviewed.** Replay of CASE-0011 after the lead's review returns `match: false, diff: ["outcome"], record_hash: false` (bug B10) | P19-F2 |
| C3 | `docs/PRIOR_WORK.md` §1: "see docs/CLAUDE_CODE_USAGE.md"; "P0-P13 was written in Cursor" | The file does not exist. README says P0–P14-A in Cursor. There are typos ("completly", "All Application"). This is the declaration the form points to | P19-F3 (you approve the wording) |
| C4 | README: "The brief came from the deterministic template (`generator=template:v1`)" | Imprecise. The **report** is `template:v1`; the **brief** in `output_examples/example_1_output.json` is `template:v2` | P20 doc refresh |
| C5 | `docs/DEMO_SCRIPT.md`: "both live attempts at example 3 failed and Quillfeather is not one of the committed live examples" | Misleading reason. Example 3 is Oakhaven (injection, VND-0015). Quillfeather is example 2: its one live example attempt (`run-ecbcba2a7228`, P15 report) hit a 502 on its only model call and was discarded. A *complete* live Quillfeather run **does** exist, in the eval (`run-257c86984507`), and the script should use it | P20 |
| C6 | README repo map: "`output_examples/`: live output for example 1 and the sample-mode set in `output_examples/sample_mode/`" | **Stale files at the root.** `output_examples/example_2…6_output.json` are the 23 Oct offline outputs from before P14-A. They still show `ALL_REQUIRED_CONTROLS_MET` on ESCALATE and DECLINE: the exact bug Release 2 fixed. A judge opening example 2 sees it. The 12 top-level `logs/examples/*.jsonl` are from the same run | P20-S5 |
| C7 | Console spinner: "takes 2–5 seconds in sample mode, up to 60 seconds live" (`ui/screens.py`) | Wrong. The live p50 is 142 s and the p95 233 s | P19-F5 |
| C8 | Console Evaluation page | Shows the **22 Oct offline** summary (`eval/results/20261022…/summary.md`, labels before the B8 fix), not the published live evaluation. `GET /eval/latest`, which the client calls, does not exist. In Docker (`eval/results` is dockerignored) it says "not published yet" | P19-F4 |
| C9 | README screenshots (`docs/img/ui_*.png`) | The Streamlit "Help agents write better apps" popover and the Deploy button cover the top right of every shot | P18 / P19-F5 |
| C10 | `.cursor/rules/20-integrity.mdc`: "Cursor is the development environment. All code is written and committed through Cursor." `AGENTS.md`: "You are a coding agent in Cursor" | No longer true: P14-B, P15 and P17 were built in Claude Code, which the README discloses | Fixed in the Release 3 import commit |
| C11 | `/health` in sample mode reports `nvidia.deep_model: nvidia/nemotron-3-super-120b-a12b` | The direct-NVIDIA fallback default is the model your account is not entitled to. It is never used, but a judge reading `/health` sees it | P19-F6 |

## 4. Bugs

| Id | Severity | Bug | File | Fix |
|---|---|---|---|---|
| B10 | Medium (visible in the console and contradicts C2) | A lead's review overwrites the stored outcome with `outcome_reasons: ["HUMAN_REVIEW"]`. Replay re-decides the machine inputs and compares them with the human record, so every reviewed case reports `match: false` | `app/audit/replay.py`, `app/api/routes_review.py` | P19-F2: replay the machine decision, verify the review separately, return `human_override` |
| B11 | Medium | The Evaluation page reads the wrong file (C8) | `ui/screens.py:56` | P19-F4 |
| B12 | Low | The provider sidebar prefers `provider_meta.provider_model` (`meterless/auto`) over the served Nemotron model, so a live run shows "fast → meterless/auto" | `ui/provider.py:_served` | P19-F5 |
| B13 | Low | The first Streamlit AppTest can time out at its 3 s default on a cold start | `tests/unit/ui/test_p10.py` | P19-F7: raise the timeout to 15 s |

## 5. Product gaps that matter for judging (not bugs)

1. **The agents' work is invisible while it happens.** A live run takes 2–4 minutes. The console shows one spinner, then the result. The trace holds exactly what the track and today's judges' note ask to see: critique, send-backs, retries and fallbacks, branching, and shared context. It is only visible afterwards, as text, at the foot of the Case page.
2. **`docker run` gives a judge an API, not a product.** The Dockerfile serves FastAPI only, and the console needs a second process (`python run.py ui`). A judge following the README Quick start gets JSON.
3. **Only one live example** (Pellucid, APPROVE: the least interesting outcome). The flagship Quillfeather shot in the demo script is sample mode, although a live Quillfeather run exists in the eval.
4. **The baseline is unmeasured.** That is honest and acceptable, but it leaves "reliable decisions" without a comparison. The cause, Nightshift lane coercion, has a vendor fix targeted for Sunday's release.
5. **No video, no deck**, and `metadata.json` `demo_video` and `slide_deck` are empty.
6. P16 (monitoring) is not built. It is correctly listed as future work.

## 6. Rubric, criterion by criterion (today)

Scores are my estimate of where a careful judge lands. The ranges reflect what is not yet recorded (the video).

### Impact (30): "Consistency with the challenge statements: how effectively does the solution address a meaningful real-world problem for its intended users?"

**PARTIAL (strong): 21–24.**

What earns marks:
- `docs/IMPACT.md` has a real persona, seven cited statistics, a before/after table built only from live runs, and a labelled 5–24 h/week estimate.
- The README Track 3 mapping table covers every word of the statement.
- Five outcomes come with a drafted next action.

What costs marks:
- One live example, and it is the APPROVE case.
- No measured comparison, because the baseline is unmeasured.
- Synthetic company data, one decision type.
- The "decisions and actions" story is hard to see without a console that shows the agents working.

### Technical (20): "How well is the solution built, including its technical implementation, reliability and architecture?"

**PASS: 15–17.**

What earns marks:
- An explicit state machine with bounded loops and a policy engine that alone decides.
- 842 tests, H-MEM conformance vectors, Scout adversarial cases and signed contracts.
- Hash-chained audit and replay.
- USL parity 416/416, a live eval harness and a clean-clone pass with Docker.

What costs marks:
- Live reliability: 20% of model calls fell back (HTTP 502) and the median is 142 s per case.
- n = 5 live cases.
- B10 replay and the stale root outputs (C6).

### Innovation (15): "How original or creative is the approach to solving the problem?"

**PARTIAL: 10–12.**

The ideas are original:
- models read, the policy decides;
- a Challenger that can only escalate;
- precedents that change outcomes only through policy and a lead's sign-off;
- the USL catalogue as the planner's world model;
- signed action contracts.

What costs marks:
- None of this is *visible* in the product.
- Monitoring was not shipped.

### Demo (15): "How clearly and effectively does the demo show the solution, its functionality, and the value it provides to the intended users?"

**FAIL until recorded. Recorded as `docs/DEMO_SCRIPT.md` stands: 8–10.**

What costs marks:
- The script is honest, but most shots are terminals, JSON and static screenshots.
- The hero case is captioned "sample mode".
- The live shot is an APPROVE with nothing to resolve.
- The required "one real request passing through Nightshift" is a terminal command.

### Product & UX (10): "How intuitive, accessible, and easy to use is the product for its intended users?"

**PARTIAL: 5–6.**

P14-B made the content right:
- brief first;
- claim-versus-record cards;
- editable drafts;
- the questionnaire form.

The surface still reads as a Streamlit prototype:
- the Streamlit popover and Deploy button;
- a two-process start;
- a 2-minute spinner;
- an Evaluation page showing old numbers (C8);
- no console in the Docker image.

### Sponsor Tech (10): "How effectively does the solution use the sponsors' technology … make the integration visible in the demo, the deck and the README."

**PASS: 8–9.**

What earns marks:
- **Zetaris:** the USL built with descriptions, keys and DQ, parity green, and a reflection with measured numbers.
- **Meterless:** Nightshift receipts on every call, the H-MEM port with conformance, and the Scout guard and contracts.
- **NVIDIA:** "Our agents do real work on Nemotron", with a per-step table.

What costs marks:
- KEV is the committed snapshot, not CISA's live feed.
- No screenshot of the USL inside Zetaris.
- Lane coercion; it is the vendor's bug, documented.

### Total today: about **67–78** (midpoint about 72)

## 7. Decision

**The repo is a complete, honest, submittable entry.** It is not the 56–67 entry of 23 Oct.
- Release 2 closed the Zetaris USL gap.
- It fixed the decision-quality bugs.
- It added live proof.

Keep it exactly as the fallback: tag it before any further work (`release3/README.md` §4).

The remaining marks are in **presentation and live breadth**, not architecture:

| Work | Marks it can move | Estimate |
|---|---|---|
| **P18: a web console that shows the agents working**, served by the same FastAPI process, so `docker run` gives a judge the product | Product & UX +2 to +3; Demo +3 to +4 (the video becomes the product working, not terminals); Innovation +1 (the reasoning architecture becomes visible); Impact +0 to +1 (a finished product) | **+6 to +9** |
| **P20: live re-run after Sunday's Nightshift fix**: all six live examples, Quillfeather live as the hero, a measured baseline | Technical +1, Impact +1, Demo +1 | **+2 to +3** |
| **P19: fix C1–C11 and B10–B13** | Protects marks: a judge who finds C1, C2 or C6 discounts every other claim | 0 to +2 |

**Expected after Release 3: about 78–89.**

**Is the UI worth it?** Yes, but only if it is bounded:

- Product & UX is worth 10 points directly. Realistically, a strong console moves it about 3 points.
- The larger effect is on Demo (15), which is judged mostly from the video:
  - The track statement and today's judges' advice ("focus on agent behaviour … it is what shows judges how your agent reached its output") reward *seeing* the critique, send-backs, retries and branching.
  - Arbiter already logs all of it: the committed traces hold 29 distinct agent–action pairs.
  - Today nobody can see it.
- A generic visual rebuild would not be worth the risk. A console whose centrepiece is the live reasoning graph is, because it turns the strongest part of the entry into the first thing a judge sees.

The constraints that make it safe:
1. The Streamlit console stays untouched as the fallback.
2. The web console is additive: a new `web/` folder and new API routes.
3. It merges to `main` only if Gate B passes (Mon 26 Oct, 10:00 GMT).
4. The live re-run and the fixes proceed in parallel and do not depend on it.

**Not recommended:** the Meterless-style 3D orbit as the main view. It is striking but encodes nothing about sequence, loops or claim-versus-record, the things the judges asked to see. It also adds three.js risk and reads poorly in a 1080p video. The design in `P18_00_DESIGN.md` takes Cartograph's idea (a graph that fills in as work happens, and every edge explains itself) and makes it specific to Arbiter: the vendor's word on one side, the company's records on the other, and the agents in between.
