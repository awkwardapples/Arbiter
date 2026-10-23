# P15: Live evidence, Nemotron proof and an honest live evaluation (human-attended)

## 1. Goal

The repository proves, with committed artefacts from real runs, that:

1. Arbiter's agents do real work on **NVIDIA Nemotron through Meterless Nightshift**: the fast lane on Nemotron 3.5 Lightning, the deep lane on Nemotron 3 Super, with receipts.
2. Live evidence queries run on the **Zetaris USL**, with request ids.
3. Arbiter beats a **single-LLM baseline using the same data and the same Nemotron model** on safety and consistency, measured live on a test split that actually contains the hard cases.
4. The governed-memory session works live.
5. A judge's clean clone passes all 8 checks, with Docker.

## 2. Why it scores

- **NVIDIA award:** "make it clear your agent does real work using the Nemotron model".
- **Sponsor Tech.**
- **Technical** (reliability is measured, not asserted).
- **Demo:** the Setup Guide's "What to show judges": the app solving a problem, its Meterless provider connection, and one real request through Nightshift returning a result.
- **Impact** (numbers for the deck).

## 3. Read first

- `R2_00_ASSESSMENT.md` (B5–B8; Sponsor Tech; Impact reliability)
- `docs/spec/03_EVALUATION.md`
- `app/llm/providers/meterless.py` (`receipt_meta`)
- `app/cli/examples.py`
- `eval/harness.py`, `eval/baseline.py`
- `data/generator/**`

## 4. Depends on

P13 merged (USL live) and P14-A merged (correct reasons, confidence, brief). P14-B may land in parallel.

## 5. Procedure

### Step 1: fix the deep lane (human, Nightshift Console; finding B7)

- The captured receipt shows `app_policy: {app: "arbiter", has_rule: true, bound_mode: "auto", requested_mode: "deep", routed_mode: "auto", mode_coerced: true}`. Nightshift's rule for app `arbiter` forces every request to `auto` (Lightning).
- In the Nightshift Console, open the app or policy settings for `arbiter`. Remove the bound mode, or bind `fast` and `deep` to their lanes, so requested modes are honoured.
- In `.env`, set `METERLESS_MODEL_FAST=meterless/fast` and `METERLESS_MODEL_DEEP=meterless/deep` (routing modes, not raw model ids).
- ⏸ Run step 2. If Nightshift cannot route `deep` to Super, use a discovered class id from `/v1/models` that maps to Super. If none exists, **state the deviation plainly** everywhere (both lanes are still Nemotron).

### Step 2: `python run.py llm proof` (new in `app/cli/llm.py`)

- Makes one small real request on each route through the normal generator. Each is a tiny JSON task tagged `purpose=proof`.
- Prints a table: route, requested model, routed model, `response.model`, receipt id, winning route, latency, tokens, plus the base URL with the token hidden.
- Writes `docs/evidence/nightshift_proof.json`: the same fields, plus the scrubbed `meterless` receipt subset (app_policy, routed_model, requested_model, receipt_id, winning_route, cost, savings).
- Must not contain the token or any `Authorization` header (test).
- **This is the video's "one real request passing through Nightshift and returning a result" shot.**

### Step 3: fix the eval labels and splits (finding B8; in `data/generator/**` and `eval/**`)

- The generator writes `expected_failing_controls` and `expected_unknown_controls` from `truth_facts` by running the policy engine's control evaluation on the truth facts. This is the label oracle already used by P3-T16. It writes `expected_contradiction_keys` for S06 **and S07**.
- Splits: stratify so each scenario with n ≥ 2 has at least one vendor in **test**, specifically S06, S07, S09, S11 and S12. Record the new split hashes. Changing splits after a published eval is acceptable here: the old eval was offline-only and its labels were incomplete. Say so in `docs/EVALUATION.md`.
- Re-run `python run.py calibrate` on the new calibration split. Zero unsafe approvals.

### Step 4: live examples

```bash
python run.py examples --live     # ARBITER_MEMORY=off, fresh var/
```

- Writes `output_examples/` (live) and `logs/examples/live/`.
- Also regenerate the sample-mode set into `output_examples/sample_mode/` and `logs/examples/sample_mode/`: this is what a judge without keys reproduces.
- Every live trace must pass `check_trace --require-live --require-collaboration`, and must show `backend=zetaris` with `zetaris_request_id`, and `provider=meterless` with Nemotron `model` and `receipt_id`.
- ⏸ Review one live brief (example 2) together before committing.

### Step 5: live memory session

```bash
python run.py demo-session --live --reset --yes
```

- Commit its traces to `logs/examples/session/`.
- Commit `docs/evidence/memory_session.md`: the 6-step table, P-0001's ledger lines and the retrieval trace (relevance and confidence).

### Step 6: live evaluation

```bash
python run.py eval --split test,inline --systems arbiter,baseline,arbiter_offline --consistency 8x3 --publish
```

- Concurrency ≤ 2. Expect about 1 hour of Nightshift calls.
- Publish to the README block and `docs/EVALUATION.md`, with model ids taken from the traces.
- If the baseline beats Arbiter on any metric, publish it and explain it.

### Step 7: clean clone with Docker (findings B5, B6)

- B5 and B6 were already fixed in the Release 2 import patch: the test is opt-in with `ARBITER_DOCKER_TESTS=1`, and the script writes `docs/passes/` only with `--evidence`.
- On your machine with Docker Desktop running:

```bash
python scripts/clean_clone_check.py https://github.com/awkwardapples/Arbiter --evidence
```

- Commit the passing report as `docs/passes/clean-clone-<date>.md`. Remove the two failing reports, or keep them under `docs/passes/history/` with a one-line note.

## 6. Acceptance tests (marker `p15`)

| Id | Test |
|---|---|
| P15-T1 | `llm proof` against a respx-mocked Nightshift writes the proof JSON with all fields. Token and `Authorization` are absent (canary). In offline mode it prints a clear "Nightshift not reachable" with a non-zero exit |
| P15-T2 | `receipt_meta` keeps `app_policy`, `routed_model`, `requested_model`, `receipt_id`, `winning_route`, `cost` and `savings` from the captured fixture, and drops everything else |
| P15-T3 | Labels: every vendor has `expected_failing_controls` equal to the oracle's FALSE required controls. S06 and S07 vendors have contradiction keys. The test split contains S06, S07, S09, S11 and S12 vendors |
| P15-T4 | Regression guard for the import-patch fix: without `--evidence` the script writes nothing under `docs/`; the test skips unless `ARBITER_DOCKER_TESTS=1` |
| P15-T5 | `check_trace --require-live` passes on every file in `logs/examples/live/` (runs on committed files; no services needed) |
| P15-T6 | The README eval block equals `render(latest summary.json)`. The summary has three systems and live model ids |
| P15-T7 | `docs/evidence/nightshift_proof.json` validates against its schema, and `fast.response_model` contains `nemotron` (committed-file test) |

## 7. Definition of done

- [ ] Gates 2, 3, 4 and 6 of the Release 2 "submission-ready" list hold.
- [ ] The report states the measured live p50 and p95 per case, model calls per case, and validator fallback rate (how often an LLM step fell back to deterministic), with discussion.

## 8. Cut lines

Consistency 8x3 → 4x2. Calibration re-run can be skipped only if P14-A's gates still give zero unsafe approvals on the new calibration split.

**Never cut:** the proof file, live examples, the baseline comparison, the clean-clone pass.

## 9. Cursor prompt

```
/start-pass 15
You are implementing P15 of Arbiter Release 2: live evidence, Nemotron proof and an honest live evaluation. Human-attended: Nightshift and Zetaris must be running.
Read: AGENTS.md; docs/spec/release2/README.md; docs/spec/release2/R2_00_ASSESSMENT.md; docs/spec/release2/P15_LIVE_EVIDENCE.md; docs/spec/03_EVALUATION.md; app/llm/providers/meterless.py; app/cli/examples.py; eval/harness.py; eval/baseline.py; data/generator/.
Never print or commit tokens. Committed evidence comes only from real runs; never edit a trace or an output by hand.
Plan Mode: .cursor/plans/P15.md with steps 1–7 and tests P15-T1..P15-T7. Wait for approval.
Tests first (marker p15) → commit → implement → attended steps, stopping at each ⏸.
Finish with docs/passes/P15_REPORT.md + docs/cursor-usage/P15.md; push p15-live; delete .cursor/ACTIVE_PASS; stop.
```
