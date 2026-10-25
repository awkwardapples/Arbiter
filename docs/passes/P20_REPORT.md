# P20 report: live re-run after the Nightshift fix, then the documents

Branch `p20-submit` (approved in place of `p20-live`). Human-attended on 25 October 2026, with the Zetaris USL and Meterless Nightshift (Console v1.2.1) running on the development machine. Built in Claude Code (Claude Opus 5.5) from `.cursor/plans/P20.md`, the spec `docs/spec/release3/P20_LIVE_RERUN.md` and the human's P20 addendum. Every committed artefact under `output_examples/`, `logs/examples/`, `eval/results_live/` and `docs/evidence/` comes from a real run. No trace or output was edited by hand. The web console shipped at Gate B (PR #37), so the documents describe it.

## Summary

| Step | Result |
|---|---|
| S1 Did the fix ship? | **No.** Routing modes are still coerced to `auto` (proof run 4, committed). A request naming Lightning by exact id was served by Super VL (run 5, kept as evidence). Routing modes kept; deviation file updated |
| S2 Live examples | **Four of six live:** examples 2, 3, 4 and 5. Examples 1 and 6 failed `--require-live` twice each and keep current sample-mode outputs. All six outcomes match `expected.json` |
| S3 Live memory session | Skipped (approved): routing did not change. The P15 session (6/6 live) stands |
| S4 Live evaluation | Done, n=10 plus 4×2 repeats, about 39 min. Arbiter 10/10, 0 unsafe, 4/4 consistent; 10 of 21 model calls fell back. Baseline unmeasured (all 502). Offline 16/16. Published after human review |
| S5 Stale outputs (C6) | Done. The root holds four live outputs and two byte copies of `sample_mode/`. The 12 pre-P14-A traces are in `logs/examples/history/`. Test P20-T2 guards it |
| S6 Documents | Done: README, SPONSORS, IMPACT, metadata, EVALUATION, DEMO_SCRIPT, SLIDES (23 slides), QA_PREP, SUBMISSION, deviation file, PRIOR_WORK. C4 and C5 fixed |
| S7 Clean clone | `--local` pre-check on `79987ff`: **8/8 pass** after the approved history-scan fix (the first run failed step 6, see below). From a container of the built image with `SAMPLE_MODE=true`: `GET /` → 307 to `/console/`, `GET /console/` → 200 ("Arbiter console"), `GET /recordings` → 200. The run against the GitHub URL with `--evidence` follows the merge, in a follow-up PR |

## S1: the Nightshift routing fix

| Run | Sent | fast | deep | Derived deviations |
|---|---|---|---|---|
| 4 (committed, `docs/evidence/nightshift_proof.json`, 11:22:20Z) | `meterless/fast`, `meterless/deep` | `bound_mode: auto`, coerced; Lightning, `rcpt_req_936ew345` | coerced; Super VL, `rcpt_req_wu3r6jyf` | `mode_coerced` ×2 |
| 5 (`docs/evidence/history/nightshift_proof-run5-exact-ids.json`, 11:22:33Z) | exact Lightning and Super VL ids | not coerced, served in `auto` by **Super VL**, `rcpt_req_504ono0n` | Super VL, `rcpt_req_ieobohlf` | `same_model_both_lanes`, `lane_model_differs_from_design` |

Run 3 (P15) moved to `docs/evidence/history/nightshift_proof-run3.json`. Both runs, and the Console version supplied by the human, are recorded in `docs/evidence/nightshift_deviations.md`.

## S2: live examples

All runs used `METERLESS_NO_THINK=1` and the routing modes, each with a 660 s kill. All six were re-run after the workload fix (below), on one commit.

| Ex | Root output | Run | Outcome (label) | Time | Queries | Model calls (ok / fell back) |
|---|---|---|---|---|---|---|
| 1 | sample mode | `run-cea4afd517a5` | APPROVE (APPROVE) | – | 10 | live attempts `run-4ace5ff50d6b`, `run-b32c49359853`: 0 / 1 each, Lightning 502 |
| 2 | **live** | `run-211916c1544d` | ESCALATE (ESCALATE) | 228 s | 14 via Zetaris, 21.9 s | 4 / 1 (Super VL; one deep plan routed to Lightning, 502) |
| 3 | **live** (retry) | `run-1b185078f01b` | ESCALATE (ESCALATE) | 196 s | 10 | 4 / 1; the injected document segment blocked (score 0.92). First attempt `run-1c14e1fbdbcb`: `provider_deadline` |
| 4 | **live** | `run-28ca582caf3d` | REQUEST_INFO (REQUEST_INFO) | 137 s | 10 | 2 / 1 |
| 5 | **live** | `run-06c793decd39` | DECLINE (DECLINE) | 146 s | 10 | 4 / 1 |
| 6 | sample mode | `run-f8a3d8fe25ba` | APPROVE (APPROVE) | – | 7 | live attempts `run-521b615a9877`, `run-f6327675dca7`: 0 / 1 each, Lightning 502 |

Every failed attempt is in `logs/examples/live_failed/`. Every successful call in the live examples was served by Super VL. Example 2 was reviewed with the human before commit: the brief, `contradiction_found` (EU versus US, `CTR-30007`), the KEV join (15 rows, `zetaris_request_id=04559cdd-…`), two Evaluator send-backs, the Challenger re-plan and escalation, and policy ESCALATE. Its Challenger made no model call; the deterministic T1 rule fired first.

**Superseded first attempt.** The first S2 run, at 11:27, timed out on every registry query (Zetaris answered `SELECT 1`, but USL queries hung) and fell back to the mirror. It was stopped before writing anything. The human restarted the Zetaris driver, and a one-query probe (2.3 s) confirmed it before S2 resumed. A second pass of examples 1–3 was made before the workload fix. It was not committed and was superseded by the full re-run.

## S4: live evaluation

`eval/results_live/20261025T153035975818Z/` (git sha `cabd79e`, first 10 test cases by case id, 4×2 consistency).

| System | n | Accuracy | Unsafe | Invalid | p50 / p95 | Calls/case | Model-call fallback |
|---|---:|---:|---:|---:|---:|---:|---:|
| arbiter (live) | 10 | 10/10 (Wilson 0.72–1.00) | 0/10 | — | 76.3 s / 271.6 s | 2.1 | 10 of 21 (0.476) |
| baseline (live) | 10 | 0/10 | 0/10 | 10/10 | 62.7 s / 125.0 s | 1.0 | 10 of 10 |
| arbiter_offline | 16 | 16/16 | 0/16 | — | 0.42 s / 0.57 s | 0 | — |

- **Arbiter:** 6 of the 10 primary cases had no successful model call. All ten decisions were still correct. Over the primary runs and the 4 repeats: 25 calls, 11 succeeded, 14 fell back.
- **Fallback rate:** rose from 0.20 (P15, 5 of 25, n=5) to 0.48. The lower median is because more cases lost their first call; it is not presented as a speed-up.
- **Lightning:** Lightning served two deep-lane calls successfully (a plan, `rcpt_req_eu1iqmuc`, and a challenge, `rcpt_req_yaqwjyz1`); the rest were 502. Routing is intermittent, not dead.
- **Baseline:** all 10 primary calls and 4 repeats returned 502 (Lightning empty response). Published as unmeasured; the prompt was not changed.
- **First-case check:** the first live case had no successful model call. The human chose to let the run continue.

## What else was built

| Change | Files | Why |
|---|---|---|
| Workload counts read the tracer's real file | `app/orchestrator.py`, `app/tracing.py` (`Tracer.path`), `tests/unit/orchestrator/test_p20_workload.py` | The human found `workload.models: []` in a live output. `_workload()` read `logs/trace-<run_id>.jsonl` relative to the cwd; the examples CLI and the eval harness log to a temporary directory, so `models`, `model_calls` and `queries` were empty or zero in every example output. The eval harness gets the same fix. Its published metrics never used `workload`, so earlier eval numbers are unaffected. The regression test fails on the old code |
| Console fixes (addendum C) | `web/src/run/mode.ts`, `web/src/pages/assess/{RecordingList,AssessPage}.tsx`, `web/src/run/RunCanvas.tsx`, `web/dist/` | The live memory session (`llm: auto`, served by Nightshift) is listed as live; the chip and recording list say "fallback steps" (trace steps marked fallback), distinct from the strip's "Retries and fallbacks"; Assess → New vendor links to `/new` |
| Eval block heading (addendum D) | `eval/report.py` | A level-3 heading, not a second H1 in the README |
| CI web job (addendum E) | `.github/workflows/ci.yml` | `npm ci && npm run check` on every push |
| History secret scan (approved during S7) | `scripts/clean_clone_check.py`, `tests/unit/docker/test_clean_clone.py` | A deleted file's diff ends in `+++ /dev/null`, so its lines were filed under the previous file. A deleted, allowlisted bundle (`bd5ac01`, already on `main`) was reported as `web/dist/.source-hash [sk]`, which failed step 6 |
| Stray spec | `P18C_CASE_AND_QUEUE2.md` removed | Byte-identical to `docs/spec/release3/P18C_CASE_AND_QUEUE.md` |
| P20 tests and gate | `tests/unit/docs/test_outputs_current.py`, `tests/unit/docs/test_p20.py`, `scripts/gates/p20.py` | P20-T1, T2, T4, T5; the gate checks metadata, the usage log, live traces and a current root of `output_examples/` |

## Acceptance tests

| Id | Test | Result |
|---|---|---|
| P20-T1 | `test_p20.py::test_p20_t1_live_traces_are_live_and_collaborative` | pass (4 live traces) |
| P20-T2 | `test_outputs_current.py` (3 tests) | pass; it failed at the tests-first commit on the stale root example 2 (`ALL_REQUIRED_CONTROLS_MET` on ESCALATE) |
| P20-T3 | the P17 claims tests in `tests/unit/docs/` | pass on the new evidence (with the approved updates below) |
| P20-T4 | `test_p20.py::test_p20_t4_metadata_models_were_served` | pass |
| P20-T5 | `test_p20.py::test_p20_t5_readme_eval_block_is_latest_live_summary` | pass |

## Deviations and approved exceptions

- **Branch:** `p20-submit`, not `p20-live` (Q1).
- **S3 skipped** because routing did not change (spec rule; confirmed by the human).
- **Tests and files outside the lane, all approved:**
  - path-only repoints to archived traces: `web/src/run/__tests__/{helpers.ts,describe.test.ts}`, `web/src/api/__tests__/events.test.ts`, `web/src/features/usl/__tests__/fixtures/live_recording.json` (Q2); `tests/unit/api/test_p18a_evidence.py` (now names example 2's live run); `tests/unit/ui/test_p19_provider.py` (the archived P15 trace is still its fixture);
  - `tests/unit/eval/test_live_traces.py`, `tests/unit/docs/test_examples.py` and `scripts/gates/p6.py`: an offline root output resolves its trace in `logs/examples/sample_mode/` (Q3, same assertions);
  - `tests/unit/docs/test_impact_numbers.py`: follows the example 2 trace (14 queries);
  - addendum B updates in `tests/unit/docs/test_claims.py`: eval labels (10/10, 10 of 21, 6 of 10), the demo-script run and receipts (`run-211916c1544d`, proof run 4), and 23 slides with monitoring on slide 22. `test_p17_t10_submission_checklist_state` is unchanged: it still expects empty video and deck links, and is updated when they are uploaded;
  - `tests/unit/api/test_p19_eval_latest.py` and `tests/unit/ui/test_p19_eval_page.py` read their expected date, n and arbiter row from the latest committed live `summary.json`, instead of the 24 October values. They now test "the page shows the latest live run" and won't break on the next eval;
  - `ui/screens.py` (`_render_eval_markdown`): the Streamlit Evaluation page drops the summary's leading `### Evaluation results` heading, which is harness output in the committed `summary.md` (addendum D). The approved route was to widen `ui/components.py:strip_leading_h1`, but `test_p12_strip_leading_h1` requires that function to keep `## ` lines, so the strip went into the page renderer instead and `strip_leading_h1` is unchanged. `test_p12_eval_title_once` passes as written;
  - `app/orchestrator.py`, `app/tracing.py` (workload fix), `web/**` (addendum C), `eval/report.py` (addendum D), `.github/workflows/ci.yml`, `docs/PRIOR_WORK.md` (addendum E), `scripts/clean_clone_check.py` (S7 history-scan fix).
- **A commit that bundled two things:** the move of the P15 example 1 trace to `logs/examples/live/history/` was already staged and went into the tests-first commit `16c4799`. History was not rewritten.
- **Human commit on the branch:** `1deb79e` (`.claude/settings.json`, hook uses `python3`).
- **Publishing:** `python run.py eval --live --publish` on its own publishes the newest *offline* summary (`app/cli/eval.py`, `publish_only` ignores `--live`). It was caught on the diff and reverted. The README block and `docs/EVALUATION.md` were published with `eval.report.publish` on `eval/results_live/`. The CLI is not changed here.
- **The USL evidence line** in `metadata.json` now cites a `Q_VENDOR_PROFILE` request id: example 2 ran no `Q_VENDOR_360`.
- **Oakhaven injection:** the live trace has one blocked segment. The output's `workload.guard_blocks` is 2, because it counts guard flags, and one segment can raise more than one. The docs say "the segment".
- **Stats wording:** fallback rates are written 0.20 and 0.48, because "48%" collides with the cited DBIR statistic in the claims test.
- **Eval `cases.jsonl`** holds absolute trace paths from the recording machine, as the P15 run does. It is the harness's output and was not edited.

## Known gaps

- **Video and deck links:** not uploaded yet. `metadata.json` `demo_video` and `slide_deck` are empty; `test_p17_t10_submission_checklist_state` is updated together with them.
- **External inputs:** both are in. The Nightshift Console version is v1.2.1, read by the operator. The organisers' IDE confirmation is linked in `docs/PRIOR_WORK.md`, dated 22 October 2026, 13:30, as shown on the platform (no time zone given).
- **Slide 6** ("What existing tools do") is general and names no product until the human checks it against the research deck.
- **Clean clone against the GitHub URL** with `--evidence` runs after the merge (follow-up PR).
- **Console screenshots** were not re-captured from the new live runs. The committed `docs/img/console_*.png` (P18) are used, including the live Quillfeather ruling.
- **Measured baseline:** still blocked on Nightshift routing.

## Commands run

```bash
python run.py zetaris status; python run.py llm status
LLM_PROVIDER=meterless METERLESS_MODEL_FAST=meterless/fast METERLESS_MODEL_DEEP=meterless/deep python run.py llm proof --out <scratch>
LLM_PROVIDER=meterless METERLESS_MODEL_FAST=nvidia/nemotron-3.5-lightning-30b-a3b METERLESS_MODEL_DEEP=nvidia/nemotron-3.5-super-vl-120b-a12b python run.py llm proof --out <scratch>
METERLESS_NO_THINK=1 timeout 660 python run.py examples --live --only example_N    # N = 1..6, then retries 1, 3, 6
python run.py examples                                                              # sample mode (twice: before and after the workload fix)
python scripts/check_trace.py --require-live --require-collaboration logs/examples/live
METERLESS_NO_THINK=1 timeout 5400 python run.py eval --live --split test --systems arbiter,baseline,arbiter_offline --cases 10 --consistency 4x2
python -c "from eval.report import latest_summary, publish; ..."                    # README block and docs/EVALUATION.md
cd web && npm ci && npm run check
python scripts/compile_cursor_usage.py
python scripts/clean_clone_check.py --local .
python scripts/tasks.py verify-pass --pass 20; python scripts/tasks.py verify
```
