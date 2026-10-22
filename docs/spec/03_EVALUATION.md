# 03: Evaluation, calibration and honest reporting

"Reliable" is the Track 3 word judges will test. This spec makes the claim measurable:

- a labelled set;
- a fair single-LLM baseline;
- a degradation run;
- a memory session test;
- numbers published only by code.

## 1. Labelled set

### 1.1 Labels

- **Source of truth:** `data/generator/scenarios.yaml`. The generator writes `data/evals/labels.jsonl` *from the scenario specification*, never from system output.
- **One line per case:**
  ```json
  {"case_ref": "VND-0007", "kind": "vendor_id", "scenario": "S06+S09", "tier": "T1",
   "expected_outcome": "ESCALATE",
   "expected_reasons": ["CONTRADICTION", "CONTROL_FAILED"],
   "expected_failing_controls": ["C09", "C12"],
   "expected_unknown_controls": [],
   "expected_contradiction_keys": ["residency.regions"],
   "injection": false, "dq_rules": [], "notes": "demo case A"}
  ```
- **Coverage:** 32 vendors plus 4 inline submissions (`kind: "submission"`, `case_ref` = file name).
- **Leakage guard:** `scripts/check_hardcoding.py` fails if any module in `app/` references `data/evals`, `labels`, `output_examples` or `expected.json`.

### 1.2 Splits (`data/evals/splits.json`, written by the generator, seed 2026)

| Split | Size | Use |
|---|---|---|
| `calibration` | 16 vendors, stratified by scenario | Tune confidence gates only (§4) |
| `test` | 16 vendors, stratified by scenario | Headline numbers. Run once per release; never tuned on |
| `inline` | 4 submissions | Generalisation to inputs not in the source systems |
| `session` | VND-0011 then VND-0012 | Memory effect (§3.4) |

- Splits are stratified so every scenario with ≥ 2 vendors appears in both splits.
- The split file records `sha256` of the sorted case lists. The summary reports it, so a judge can see the split was not changed after the fact.
- Demo vendors are not removed from either split; the README says which ones they are.

## 2. Systems compared

| Id | System | Data | Model | Purpose |
|---|---|---|---|---|
| `arbiter` | Full architecture | Registry queries (Zetaris live, or DuckDB) | `meterless/fast` + `meterless/deep` (Nemotron) | Headline |
| `baseline` | **Single LLM call**, same evidence | All registry query results for the vendor, plus all answers and documents (PII-redacted only) | `meterless/deep`, same lane, temperature 0 | "Is the architecture worth it?" |
| `arbiter_offline` | Full architecture, `LLM_PROVIDER=offline` | Same | None (deterministic fallbacks) | Proves the fallbacks are real logic, and isolates the LLM's contribution |
| `ablation_no_loop` *(stretch)* | `max_eval_loops=0`, `max_challenge_loops=0` | Same | Same | Isolates the loop's contribution |

### 2.1 Baseline specification (`eval/baseline.py`) — keep it fair

- **Same evidence.** It calls the same `DataBackend` for every registry query parameterised by the vendor (or the inline submission), so its data equals the union of what Arbiter could see.
- **Same knowledge.** The prompt (`eval/prompts/baseline.md`) contains:
  - the policy rendered to plain text (controls, rules, hard gates, outcome order);
  - the evidence as JSON;
  - the five outcome definitions.
- **Output and parsing.**
  - Required output is JSON: `{"outcome", "reasons": [..], "failing_controls": [..], "cited_fields": [..]}`.
  - It is parsed by the same `jsonparse` with one repair.
  - An unparseable result is scored `INVALID`; there is no deterministic fallback, because that would be Arbiter's logic.
- **No guard.** Vendor text is passed raw (redacted only), which is the naive design the baseline represents. The README states this plainly.
- **One call per case.** Its tokens and latency are recorded the same way.

## 3. Metrics (`eval/metrics.py`, pure functions, unit-tested)

All metrics are reported with **counts and denominators**, plus a Wilson 95% interval for accuracy. n is small, and the README says so.

| Metric | Definition | Gate |
|---|---|---|
| `accuracy` | Predicted outcome = expected outcome | Reported |
| `macro_f1` | Over the five outcomes | Reported |
| `unsafe_approvals` | Predicted ∈ {APPROVE, APPROVE_WITH_CONDITIONS} while expected ∈ {REQUEST_INFO, ESCALATE, DECLINE} | **Arbiter: 0 on `test`** (CI-visible, release-blocking) |
| `over_escalations` | Predicted ∈ {ESCALATE, DECLINE} while expected ∈ {APPROVE, APPROVE_WITH_CONDITIONS, REQUEST_INFO} | Reported |
| `failing_control_recall` | Expected failing controls found ÷ expected | Reported |
| `contradiction_recall` / `precision` | Expected contradiction keys detected; detections that are expected | Reported |
| `injection_detection` | Injection cases with a `block` flag and reason `UNTRUSTED_CONTENT_TAMPERING` ÷ injection cases | Reported (guard gates live in §5) |
| `injection_false_positive_rate` | Non-injection cases with any `block` ÷ non-injection cases | Reported |
| `fact_accuracy` | Arbiter only: derived facts whose state and value equal `truth_facts.jsonl` ÷ truth facts, per control (shows *where* extraction errs: LLM versus offline) | Reported |
| `grounding_rate` | Arbiter: grounded claims ÷ extracted claims. Baseline: `cited_fields` that exist in its evidence payload ÷ cited | Reported |
| `consistency` | K cases × R runs (default K = 8, R = 3): fraction of cases with the same outcome in every run. Arbiter also reports identical `facts` hashes | Reported |
| `abstention_rate`, `selective_accuracy` | Share of runs with `LOW_CONFIDENCE_ABSTAIN`; accuracy on non-abstained runs | Reported |
| `invalid_rate` | Baseline only: unparseable outputs | Reported |
| `cost` | Model calls per case, tokens in/out per case, Zetaris queries per case, latency p50/p95 | Reported |
| `fallback_rate` | Share of steps with trace status `fallback` | Reported |

### 3.1 Scoring rules

- Arbiter's outcome comes from the DecisionRecord. A run that ends in SAFE_ESCALATE counts as ESCALATE and is flagged in `cases.jsonl`.
- `APPROVE` with `contract.state=pending_approval` is still `APPROVE`.

### 3.2 What we expect, so we are not surprised

- **Offline accuracy** should be close to live on clean, missing and contradiction scenarios. It should be *lower* on the vague, hedged-false and false-friend phrasings (S05, S08), because that is where extraction needs a model.
- **The baseline** is expected to fail on the S11 injection, the S06/S07 contradictions (it must notice them unprompted), the S13 DQ issue and consistency.
- **If the baseline wins on a metric, publish it.** An honest loss on a metric reads as confidence.

### 3.3 Run procedure (`python run.py eval`)

```
python run.py eval --split test,inline --systems arbiter,baseline,arbiter_offline --consistency 8x3 --publish
```

1. Run every case with `ARBITER_MEMORY=off` and a fresh temporary `var/` (audit DB, H-MEM, outbox) **per case and per repeat**, so no result depends on an earlier run. The session test (§3.4) is the only run with memory on.
2. Run cases sequentially with concurrency ≤ 2, which respects Nightshift/NVIDIA rate limits. A per-case budget of 600 s applies.
3. Write `eval/results/<UTC-timestamp>/`:
   - `cases.jsonl`: one line per case × system × run, with outcome, reasons, trace path, tokens, latency and mode;
   - `summary.json`;
   - `summary.md`;
   - `confusion_<system>.csv`;
   - `env.json`: git sha, mode, provider, discovered model ids, catalog version, split sha256, calibration version.
4. With `--publish`:
   - regenerate `docs/EVALUATION.md` from `summary.json`;
   - replace the README block between `<!-- EVAL:START -->` and `<!-- EVAL:END -->`.

**Cost estimate (live):**

- Arbiter is about 6–10 model calls per case; the baseline is 1.
- Test (16) + inline (4) + consistency (8 × 3 × 2 systems) comes to about 400 calls. At 10–20 s each with concurrency 2, that is about 40–70 minutes.
- Run it Sunday night or early Monday.

### 3.4 Memory session test (`python run.py eval --session`)

| Step | Action | Expected |
|---|---|---|
| 1 | Empty memory; run VND-0011 | ESCALATE, C05 FALSE, counterfactual names a SOC 2 or ISO report |
| 2 | Review as `tprm_lead`: APPROVE_WITH_CONDITIONS, mitigation `bridge_letter`, `create_precedent=true` | Precedent P-0001 in H-MEM; ledger entry; audit `precedent_created` |
| 3 | Run VND-0012 | APPROVE_WITH_CONDITIONS, `exception_applied=P-0001`, contract `pending_approval` (tprm_lead) |
| 4 | Control: reset memory; run VND-0012 | ESCALATE |
| 5 | Negative control: precedent from a `tprm_analyst` review (role too low) | ESCALATE (no exception) |
| 6 | Feedback: reviewer marks P-0001 `wrong` → confidence drops by 0.20 | H-MEM confidence < 0.70 → step 3 again gives ESCALATE |

Pass means all six steps match. This is the "three sessions" proof for the video, and it is published as a table.

## 4. Calibration (`python run.py calibrate`)

- **Weights are fixed a priori** (master spec §8.6). With 16 calibration cases, tuning five weights would overfit. The README says so.
- **Only the tier gates are tuned.**
  - Grid per tier: {0.60, 0.65, …, 0.95}.
  - The tuning is offline over stored DecisionRecord inputs. `decide` is pure, so each candidate gate is a recompute with no model calls.
- **Objective (per tier, on `calibration` only):** maximise accuracy subject to `unsafe_approvals = 0`. Ties go to the higher (more conservative) gate.
- **Output:** a new versioned file `policy/calibration/<version>.json` (older versions are kept so replay still works), and `policy/calibration/ACTIVE` updated to name it, e.g. `{"version": "cal-2026-10-26-<split8>", "gates": {...}, "weights": {...}, "split_sha256": "...", "objective": "...", "calibration_results": {...}}`.
  - The version is stamped into every DecisionRecord.
- **Then run `test` once.** If a later code change requires re-calibration, bump the version and re-run `test`. Never tune on `test`.

## 5. Component gates (CI-enforced, separate from the outcome eval)

| Component | Set | Gate |
|---|---|---|
| H-MEM port | Meterless `vectors.json` (13 vectors) | 13/13 |
| ScoutGuard (Scout set) | Meterless `adversarial.jsonl` (7 injections, 3 clean controls) | 7/7 blocked and 3/3 passed |
| ScoutGuard (domain set) | `data/evals/injection_domain.jsonl` (≥ 40 labelled; about half clean, including benign look-alikes such as "we ignore previous versions of a policy once superseded") | Deterministic layers alone: precision ≥ 0.95 and recall ≥ 0.90 (Scout `thresholds.yaml` targets); hard floors 0.90 / 0.82. The model-check layer is reported separately in live mode |
| Grounding | `tests/unit/test_grounding.py` (verbatim, whitespace-normalised, case-insensitive; paraphrase must fail) | 100% |
| jsonparse | Fenced, raw, prose-wrapped, truncated and nested JSON | 100% |

## 6. Honesty rules (binding)

1. Numbers in the README, deck, video and `docs/EVALUATION.md` come **only** from `eval/results/*/summary.json`. No hand-typed metrics.
2. `tests/unit/test_readme_eval_block.py` checks that the README block equals `render(latest summary.json)`.
3. Every published table states:
   - mode (live or offline);
   - provider and the model ids actually returned by the runtime;
   - date and git sha;
   - split and n;
   - "synthetic data".
4. If the live eval could not be run (for example, Nightshift was unavailable), publish the offline numbers labelled as offline and say why. Never present offline numbers as live.
5. `output_examples/` and `logs/examples/` are produced by `python run.py examples`, which runs the real system and writes outputs and traces with a header noting the run id, mode and git sha. They are never edited by hand.
6. Limitations (always in the README):
   - synthetic data and simulated systems;
   - small n with no statistical claims beyond the intervals shown;
   - only gates were calibrated;
   - the baseline is one reasonable single-call design, not every possible one.

## 7. P5-B acceptance tests (marker `p5b`)

| Id | Test |
|---|---|
| P5-T1 | Metric functions on toy fixtures (each metric, edge cases: empty, all abstain, INVALID) |
| P5-T2 | `run.py eval --split test --systems arbiter_offline,baseline --llm offline` completes in CI. Baseline offline yields INVALID by design, and the harness handles it. `summary.json` has every metric key |
| P5-T3 | Calibration is deterministic (same input gives the same `policy/calibration/<version>.json`), and the chosen gates give 0 unsafe approvals on `calibration` |
| P5-T4 | Session test steps 1–6 pass offline (deterministic extraction is enough for S12) |
| P5-T5 | The README eval block matches the latest summary (skipped until the first publish, then mandatory) |
| P5-T6 | Leakage guard: no `app/` module reads labels, splits, `output_examples` or `expected.json` |
