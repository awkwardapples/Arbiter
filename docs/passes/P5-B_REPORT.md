# P5-B report: evaluation harness, baseline, calibration

## Built

- `eval/metrics.py` — accuracy, selective accuracy, macro-F1, unsafe approvals, over-escalation, contradiction handling, injection, consistency, cost, latency. Wilson 95%.
- `eval/harness.py` — labelled splits through `orchestrator.run`. This lane forces `SAMPLE_MODE=true`, `LLM_PROVIDER=offline`, `ARBITER_MEMORY=off`.
- `eval/baseline.py` — one deep call on the same registry evidence, PII redaction only. Offline or unparseable output is `INVALID`.
- `eval/calibrate.py` — per-tier gate search on the calibration split only. Weights copied from `cal-initial.json`. Does not retarget `ACTIVE` unless asked.
- `eval/report.py` — `docs/EVALUATION.md` rewritten from `summary.json`. README block updates only when both markers exist.
- `eval/examples.py` — six `output_examples/` files and `logs/examples/` traces from real `orchestrator.run` calls.
- `app/cli/eval.py` — `eval`, `eval --session`, `eval calibrate`. `--llm` is accepted and ignored.
- `scripts/gates/p5b.py` — inline-split smoke.
- `app/policy/loader.py` — three optional fields on `Calibration` (approved additive extension; see below).

## Cross-lane touch (approved)

`app/policy/loader.py` is owned by P2-C. P5-B adds optional `split_sha256`, `objective`, and `calibration_results` (`None` when absent). `cal-initial.json` still loads. Gates and weights are unchanged. This is not a schema change to the decision logic.

## Which split each number is on

| Number | Split | Source |
|---|---|---|
| 15/15 correct, 0 unsafe approvals | test | `eval/results/20261022T080517661769Z/summary.json`, copied into `docs/EVALUATION.md` |
| unsafe approvals = 1, so no new calibration file | calibration | `calibrate_split` (P5-T3) |
| session table, six `yes` | session vendors VND-0011, VND-0012 | P5-T4 |

`docs/EVALUATION.md` is the test-split offline run. It is not a calibration result and it is not a live Nightshift run. `git_sha` inside that summary is `a7228be` (the acceptance-test commit). The run executed the uncommitted harness on top of that commit.

`data/evals/splits.json` has 15 test cases and 17 calibration cases. Tests compare counts to that file.

No new file under `policy/calibration/`. `ACTIVE` stays `cal-initial`. The search keeps the initial gates when it cannot find a gate with zero unsafe approvals, and it records the real unsafe count. That count is 1, so the zero-unsafe acceptance stays red.

## Known gaps / blocked

- Gate calibration cannot clear T3 because S06's offline contradiction is not raised.
- Root cause: extractor does not surface the contradiction fact, so decide() sees no contradiction and returns ALL_REQUIRED_CONTROLS_MET.
- Cross-lane follow-up: P3.5 (offline extractor fix for S06).
- The test split is clean (15/15, 0 unsafe approvals). The failure is only on the calibration split.

P5-T3 still requires `unsafe_approvals == 0`. The assertion message is:

`VND-0023 (S06) offline path approves with ALL_REQUIRED_CONTROLS_MET; contradiction on residency.regions not raised by extractor.`

Do not merge until P3.5 lands. This lane did not edit `app/extract/`, `app/facts.py`, `app/grounding.py`, or `data/evals/`.

P5-T5 stays skipped until `README.md` has `<!-- EVAL:START -->` and `<!-- EVAL:END -->` (P6).

`GET /eval/latest` is not in this change. `routes_meta.py` was left for a follow-up that does not depend on P3.5.

`python scripts/tasks.py verify-pass --pass 5b` is red on P5-T3 by design. It was not treated as a green gate.

## Deviations

- Offline only. No Nightshift call and no Zetaris call. `arbiter_offline` is the system under test. The baseline's offline path is `INVALID` on purpose (no deterministic fallback).
- `run.py assess` was not edited.
- Example headers say `orchestrator.run offline gate (sample mode, DuckDB)`. They do not claim `python run.py examples`.
- Offline p50 values are a few hundred milliseconds. They are recorded and labelled as not live latency.
- The harness does not parallelise. The shared DuckDB connection is not thread-safe.
- Baseline `purpose="baseline"` is outside `PURPOSES`, so the generator uses temperature 0.0 and max_tokens 2048. No P2-B edit.

## Commands

```
.venv/bin/ruff check eval app/cli/eval.py app/policy/loader.py scripts/gates/p5b.py tests/unit/eval tests/evals
.venv/bin/python -m pytest tests/unit/eval tests/evals -q
```

P5-T1, T2, T4, T6, T7, T8 and the offline-examples check pass. P5-T5 skips. P5-T3 fails with the VND-0023 message above.

## Explain it

1. The baseline sees the same registry evidence and the same policy text, with PII redacted, and makes one deep call. Its weakness is that a parse failure or the offline provider is `INVALID`, and it has no ScoutGuard and no deterministic fallback.
2. An unsafe approval is a predicted `APPROVE` or `APPROVE_WITH_CONDITIONS` when the label is `REQUEST_INFO`, `ESCALATE`, or `DECLINE`.
3. Only the tier gates are free parameters. Weights were fixed before any case was scored. The calibration split is the only split the search reads.
4. A judge regenerates `docs/EVALUATION.md` with `python run.py eval --split test --systems arbiter_offline,baseline --llm offline --publish` and diffs it against `summary.json`. README markers are not present yet, so the README is not updated.
5. On the offline test split the baseline is entirely `INVALID` (it has no offline fallback) and arbiter_offline is 15/15. There is no offline case where the baseline beats Arbiter. The calibration split is where Arbiter is wrong: VND-0023.
