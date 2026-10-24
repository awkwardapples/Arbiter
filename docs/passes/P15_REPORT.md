# P15 report: live evidence, Nemotron proof and live evaluation

Branch `p15-live`. Human-attended on 24 October 2026, with Zetaris USL and Meterless Nightshift running on the development machine. Every committed artefact below comes from a real run. No trace or output was edited by hand.

## Summary

| Spec step | Result |
|---|---|
| 1. Deep lane routing (B7) | **Deviation, stated plainly.** Nightshift's Default app rule coerces both lanes to `auto`, and the Console offers no way to remove it. Meterless has acknowledged the bug, with a fix pending. See `docs/evidence/nightshift_deviations.md` |
| 2. `run.py llm proof` | Done. `docs/evidence/nightshift_proof.json` holds real receipts for both lanes; its deviations are derived from the receipts |
| 3. Labels and splits (B8) | Done. Labels come from the oracle; the test split has S06, S07, S09, S11 and S12. P3-T16 is green. Calibration was re-run, nothing committed, gates unchanged |
| 4. Live examples | **Subset: example 1 only.** Example 3's two live attempts failed on their first call and are kept in `logs/examples/live_failed/`. Sample-mode set regenerated |
| 5. Live memory session | Done. 6/6 steps; `docs/evidence/memory_session.md` |
| 6. Live evaluation | Done with n=5 live and n=16 offline. **The baseline was not measured**: every baseline call returned HTTP 502 |
| 7. Clean clone with Docker | Done. All 8 steps pass (`docs/passes/clean-clone-2026-10-24.md`, commit `10753bb`) |
| Parity refresh | Done. `all_green: true`, `query_layer: usl`, DQ 5/5, 416/416. Byte-identical to the committed file, so no commit |

## What was built

- **`receipt_meta`** (`app/llm/providers/meterless.py`):
  - **Kept:** `response_id`, the existing receipt scalars, `winning_route.*` (now including `model`), `app_policy.*`, `cost.*`, `cost.baseline.*` and `savings.*`. `app_policy` is read from `meterless.app_policy` or `meterless.receipt.app_policy`.
  - **Dropped:** phases, egress, lineage, cache and envelopes.
- **`python run.py llm proof [--out PATH]`** (`app/cli/llm.py`):
  - **Resolution:** clears the resolution cache, then resolves the provider. If it is not `meterless`, the command prints `Nightshift not reachable: <reason>` and exits 1.
  - **Calls:** makes one `generate()` call per lane (`purpose=proof`) and reads each result back from its own trace line. A failed call prints `proof <lane>: FAILED <type>: <message>` and exits 1, for example `meterless HTTP 404: function_not_found`. Only the status and machine-readable error codes are printed, never free text (approved).
  - **Output:** writes `ProofDocument` JSON and its schema. `deviations` is computed from the two receipts: `mode_coerced`, `same_model_both_lanes` and `lane_model_differs_from_design`.
- **Labels** (`data/generator/oracle.py`, `generate.py`):
  - `expected_failing_controls`, `expected_unknown_controls` and `expected_contradiction_keys` come from `decide()` on the truth facts.
  - `_cover_codes` moves singleton-key vendors so that every scenario code on 2 or more vendors appears in both splits. VND-0007 (S06+S09) moved into the test split.
  - Only `labels.jsonl` and `splits.json` changed.
- **Live eval:**
  - `eval/live.py` adds per-system options and a scoped environment. Live runs pin `LLM_PROVIDER=meterless`.
  - It also adds a case subset and a per-system `run` block: mode, model ids, routed models per lane, p50/p95, calls per case and model-call fallback rate.
  - `eval/report.py` renders the three-way table, the reduced-n note, the routed model per lane and a deviation line derived from the summary. `publish` replaces only the marked block in the docs file.
  - Old summaries render byte-identically, so P5-T5 stays green.
- **Examples** (`app/cli/examples.py`):
  - Live output goes to `output_examples/` with traces in `logs/examples/live/`.
  - Sample mode goes to `output_examples/sample_mode/` and `logs/examples/sample_mode/`.
  - `--only STEM…`; `_is_live` requires `zetaris` + `meterless`; `--live` pins `LLM_PROVIDER=meterless`.

### Approved changes outside the P15 file list

| File | Change | Approved |
|---|---|---|
| `app/cli/eval.py` | Additive `--live` and `--cases N`; offline stays the default; live results go to `eval/results_live/`, and `--live --publish` writes only `docs/EVALUATION.md` | Q2 (a) |
| `app/config.py`, `.env.example`, `app/llm/providers/meterless.py` | `METERLESS_NO_THINK` (default false) prepends `{"role": "system", "content": "/no_think"}` on Nightshift calls and records `no_think: true` in `provider_meta` | Additive config change, approved |
| `tests/unit/docs/test_examples.py`, `scripts/gates/p6.py` | P6 test retarget: a live header resolves its trace in `logs/examples/live/`, an offline one in `logs/examples/` | Approved |

## Nightshift proof and routing

The committed proof is run 3 (04:05Z). Runs 1 and 2 are kept in `docs/evidence/history/`.

| Run | fast | deep |
|---|---|---|
| 1 | `bound_mode: deep`, coerced; Super VL (`rcpt_req_y99j3amt`) | not coerced; Super VL (`rcpt_req_hzqsybsl`) |
| 2 | `bound_mode: auto`, coerced; Super VL (`rcpt_req_54c10ozg`) | coerced; Super VL (`rcpt_req_04ajibho`) |
| 3 (committed) | `bound_mode: auto`, coerced; **Lightning** (`rcpt_req_924f14pn`, 5728 ms, 57/262 tokens) | coerced; Super VL (`rcpt_req_p412l7ql`, 615 ms, 57/34 tokens) |

Run 3's derived deviations are two `mode_coerced` entries. In `auto` mode Nightshift chooses the model per request, so lane separation is not guaranteed. Large deep-lane prompts were repeatedly routed to Lightning, which returned HTTP 502 `nvidia/nemotron-3.5-lightning-30b-a3b_empty_response`.

The human-observed facts are in `docs/evidence/nightshift_deviations.md`:
- Super 3 120B returns 404 (not entitled);
- the fleet bindings are correct;
- the operator's restart attempts;
- the vendor's acknowledgement.

## Live examples

All live runs since `/no_think` used `METERLESS_NO_THINK=1`.

| Example | Run | Outcome | Time | LLM steps (agent, purpose, lane → routed model, receipt) |
|---|---|---|---|---|
| 1 (VND-0003) | `run-83de5da137c0` (committed) | APPROVE (label APPROVE) | 159.0 s | Planner plan deep → Super VL `rcpt_req_ltd0d684`; Evidence extract fast → Super VL `rcpt_req_y39h16ui`; Evaluator critique fast → Super VL `rcpt_req_rfbsdjpm`; Planner plan deep → Super VL `rcpt_req_cdh75z4f`; Challenger challenge deep → Super VL `rcpt_req_7r1o2wvc`; Planner plan deep → **502** (fallback) |
| 3 (VND-0015) | `run-3895568b0e9a`, `run-ad51059259f0` (`logs/examples/live_failed/`) | ESCALATE (label ESCALATE) | 40.4 s, 49.9 s | First call (Planner plan, deep) → 502 empty response in both attempts; the rest of each run was deterministic. One retry with identical parameters; not committed as live evidence |

Every call in run 3 of the proof, and in the live examples, carried `app_policy.mode_coerced: True`. The Reporter stayed `template:v1`, and the brief is deterministic by design (P14-A).

**Example 1 live:**
- Fallback rate 1/6 model calls.
- Zetaris request ids are present on all 24 data events, e.g. `Q_VENDOR_PROFILE` `zetaris_request_id=55bf9cc1-e25e-4a48-9b41-f2bda35d935d`. This id is the `X-Request-ID` header that Arbiter generates and sends to Zetaris (`app/data/zetaris.py`); Zetaris does not return one.

**Superseded attempts, before `/no_think`.** These are kept in git history at `87977cc` and replaced in `dc45956` so that configurations are not mixed:
- **Example 1** (`run-7fff81db62da`): REQUEST_INFO. The model's extraction missed the MFA and encryption answers, so C01 and C04 stayed UNKNOWN. That is the safe direction.
- **Example 3** (`run-b4fb57a35302`): ESCALATE.
- **Example 2** (`run-ecbcba2a7228`): its only model call returned 502. It was discarded and never committed.

Examples 2, 4, 5 and 6, and example 3, keep their committed offline outputs and traces in `logs/examples/`. The sample-mode set (all 6, matching `expected.json`) is in `output_examples/sample_mode/`.

## Live memory session

See `docs/evidence/memory_session.md`.
- All 6 steps passed live; P-0001 moves VND-0012 to APPROVE_WITH_CONDITIONS, and reset, analyst role and `wrong` feedback each block it.
- 7 runs, 17 model calls: 10 succeeded (all Super VL, `no_think: true`) and 7 fell back.
- The step-3 retrieval log was removed by the session's own `--reset` before it could be copied.

## Live evaluation

See `docs/EVALUATION.md` and `eval/results_live/20261024T045916036274Z/`.

| System | n | Accuracy | Unsafe | Invalid | p50 / p95 per case | Model calls/case | Model-call fallback |
|---|---:|---:|---:|---:|---:|---:|---:|
| arbiter (live) | 5 | 5/5 | 0/5 | — | 141.8 s / 233.3 s | 5.0 | 5/25 (0.20) |
| baseline (live) | 5 | 0/5 | 0/5 | 5/5 | 58.8 s / 80.8 s | 1.0 | 5/5 (1.00) |
| arbiter_offline | 16 | 16/16 | 0/16 | — | 0.44 s / 0.61 s | 0 | — |

- **Live subset:** the first 5 test cases by case id (VND-0001, VND-0003, VND-0004, VND-0006, VND-0007), plus 4×2 consistency repeats. Arbiter live was 4/4 consistent.
- **Baseline:** all 9 of its calls (primary and repeats) returned 502: 7 Lightning empty responses and 2 `provider_deadline`. This measures Nightshift routing, not single-LLM quality. The comparison is published as unmeasured, not as an Arbiter win.
- **Routed models (arbiter live, from receipts):** fast → Super VL (9 calls); deep → Super VL (10) and Lightning (1).
- **Validator fallback discussion:** every fallback was a provider 502, not a validator rejection. Both extract calls in the superseded runs needed one JSON repair; no call in the evaluation did.

## Calibration (not committed)

`calibrate_split` on the new calibration split, written to the scratchpad only:
- gates T1, T2 and T3 = 0.95, unchanged from `cal-2026-10-26-eb975166`;
- 16/16 correct, 0 unsafe approvals.

The gates did not change materially, so nothing was stopped. `policy/calibration/**` is untouched.

## Test changes due to reality

- **T5** (`tests/unit/eval/test_live_traces.py`) was written for all six examples live. It now checks that the live headers and the `logs/examples/live/` traces map one-to-one, with at least one trace, because the approved subset ended up as example 1. Its other checks are unchanged: `check_trace --require-live --require-collaboration`, a Zetaris request id, and a Nemotron model with an `rcpt_` receipt.
- **`tests/unit/eval/test_examples.py`** (P5-B, offline examples) now reads `output_examples/sample_mode/`, because `output_examples/` holds live runs.

## For P17 (not changed here, per Q4 (b))

- `metadata.json` `models` and `sponsor_technologies.nvidia.models`, `docs/SPONSORS.md` and `README.md` still claim the deep lane is `nvidia/nemotron-3-super-120b-a12b`. Per the proof, both lanes run in Nightshift `auto` mode and serve `nvidia/nemotron-3.5-super-vl-120b-a12b` and `nvidia/nemotron-3.5-lightning-30b-a3b`, and the account is not entitled to Super 3 120B. Update those claims and `tests/unit/docs/test_metadata.py` together.
- `scripts/check_metadata.py` reads only top-level `logs/examples/`, so it does not yet check the live traces in `logs/examples/live/`.
- The README eval block still shows the offline 15-case result. Point it at `eval/results_live/` once the claims are aligned.
- `scripts/check_trace.py --require-live` accepts a trace whose only Meterless call failed (the `provider=meterless` fallback event counts). T5 adds the stricter check; the checker itself may want it.
- `python scripts/tasks.py verify` crashes at secret-scan with `AttributeError: 'Namespace' object has no attribute 'history'` (`cmd_verify` passes an empty `Namespace`). This is pre-existing on `main`. `verify-pass` is unaffected.
- `docs/passes/P4-B_REPORT.md`, `P6_REPORT.md`, `P3.5_REPORT.md` and `docs/cursor-usage/P3.5.md` cite the old clean-clone report paths, which are now under `docs/passes/history/`.

## Commands run

```bash
python run.py llm status
python -c "from data.generator.generate import generate; ..."   # seed 2026, as_of 2026-10-26
calibrate_split(out_dir=<scratchpad>)                            # not committed
python run.py examples                                           # sample mode
ZETARIS_QUERY_LAYER=usl python run.py zetaris parity
LLM_PROVIDER=meterless python run.py llm proof                   # three runs
python run.py examples --live --only example_2                   # discarded
python run.py examples --live --only example_1 example_3         # superseded
METERLESS_NO_THINK=1 python run.py examples --live --only example_1 example_3
METERLESS_NO_THINK=1 python run.py examples --live --only example_3   # one retry
ARBITER_MEMORY=on METERLESS_NO_THINK=1 SAMPLE_MODE=false python run.py demo-session --live --reset --yes
python scripts/clean_clone_check.py --local . --evidence
METERLESS_NO_THINK=1 python run.py eval --live --split test --systems arbiter,baseline,arbiter_offline --cases 5 --consistency 4x2 --publish
python scripts/tasks.py verify-pass --pass 15                    # ok: 805 passed, 6 skipped
python scripts/tasks.py secret-scan; python scripts/tasks.py hardcode-check; python scripts/check_metadata.py
python scripts/check_trace.py --require-live --require-collaboration logs/examples/live
```
