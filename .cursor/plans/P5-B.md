# P5-B plan: evaluation harness, baseline, calibration, publishing

## Approved decisions (2026-10-22)

- **Calibration file.** Add `split_sha256`, `objective`, and `calibration_results` as optional fields on `Calibration` in `app/policy/loader.py`, each defaulting to `None`. Old files keep loading. This is an approved additive extension of a P2-C file. Gates and weights logic stay as they are. The pass report will say this file was touched.
- **One file.** Those three fields live on the calibration JSON. They are not stored in a second results file.
- **No live calls.** This lane does not call Nightshift or Zetaris. Every gate run uses the DuckDB mirror and `LLM_PROVIDER=offline`.
- **Splits.** Gate search reads the calibration split only. Headline metrics for a run are computed on the splits that run asked for (`test`, `inline`, or both). `summary.json` names that split list and its sha256. The test split is never an input to `calibrate`.
- **Examples.** The offline gate runs all six `input_examples/example_*.json` files through `orchestrator.run` and writes `output_examples/` plus `logs/examples/`. `run.py` `assess` is not edited. Each example header records `p50_ms` (and `n_runs`). If the offline timings are too small to mean much, the header still records them and says so.
- **Report.** `docs/EVALUATION.md` is rendered from `summary.json`.

## Goal

Build the evaluation lane from `03_EVALUATION.md`: run the labelled splits through Arbiter, a single-call baseline, and offline Arbiter; score them with pure metrics; tune only the tier confidence gates on the calibration split; and publish numbers that are rendered from `eval/results/*/summary.json`. The session check reuses the existing `demo-session` command. Live Meterless runs stay human-attended after the offline gate is green.

## Files

All paths below are inside P5-B ownership (`docs/spec/passes/README.md` §3) except the one loader edit in the questions section. That edit is not started unless you approve it with this plan.

| File | Action |
|---|---|
| `eval/metrics.py` | Create. Pure metric functions and Wilson intervals. |
| `eval/baseline.py` | Fill the stub. One deep-route call, same evidence, `INVALID` when the model is offline or the JSON still fails after the generator's single repair. |
| `eval/prompts/baseline.md` | Create. Policy text, evidence JSON, five outcome definitions, required JSON shape. |
| `eval/harness.py` | Fill the stub. `run(...)` over splits, isolated `var/` per case and repeat, result artefacts. |
| `eval/calibrate.py` | Create. Offline grid over stored `PolicyInputs`. |
| `eval/report.py` | Fill the stub. `render_summary_md` and `publish`. |
| `app/cli/eval.py` | Fill the stub. `eval` and `calibrate` handlers. The module only delegates; it does not read `data/evals`. |
| `scripts/gates/p5b.py` | Fill this lane's gate stub (P0 created it for this lane). |
| `app/policy/loader.py` | Approved additive edit. Optional `split_sha256`, `objective`, `calibration_results` on `Calibration`. |
| `app/api/routes_meta.py` | Final commit only. Add `GET /eval/latest`. P4-B's health, vendors, and audit routes stay as they are. |
| `output_examples/*_output.json` | Written by the offline examples run (`orchestrator.run`), six files. |
| `logs/examples/trace-*.jsonl` | Traces copied from those same runs. |
| `policy/calibration/<version>.json` | Written by `calibrate` at run time. `cal-initial.json` is kept. `ACTIVE` is updated to the new version name. |
| `docs/EVALUATION.md` | Written only by `publish`. |
| `tests/unit/eval/test_metrics.py` | P5-T1 |
| `tests/unit/eval/test_harness_offline.py` | P5-T2 |
| `tests/unit/eval/test_calibrate.py` | P5-T3 |
| `tests/evals/test_session.py` | P5-T4 |
| `tests/unit/eval/test_publish.py` | P5-T5 and P5-T8 |
| `tests/unit/eval/test_leakage.py` | P5-T6 |
| `tests/unit/eval/test_env.py` | P5-T7 |
| `docs/passes/P5-B_REPORT.md` | Finish step. |
| `docs/cursor-usage/P5-B.md` | Finish step. |

Not edited: `README.md` (P6 owns it and the `<!-- EVAL:START -->` / `<!-- EVAL:END -->` markers). `publish` rewrites the README only when both markers are already present. `app/orchestrator.py` stays as it is; see risks. Ablation (`ablation_no_loop`) is a cut line and is not built.

`03` §6 names `tests/unit/test_readme_eval_block.py`. That path sits outside `tests/unit/eval/**`. The test will live at `tests/unit/eval/test_publish.py` so it stays in this lane.

## Interfaces

```python
# eval/metrics.py
OUTCOMES = ("APPROVE", "APPROVE_WITH_CONDITIONS", "REQUEST_INFO", "ESCALATE", "DECLINE")
METRIC_KEYS = (
    "accuracy", "macro_f1", "unsafe_approvals", "over_escalations",
    "failing_control_recall", "contradiction_recall", "contradiction_precision",
    "injection_detection", "injection_false_positive_rate", "fact_accuracy",
    "grounding_rate", "consistency", "abstention_rate", "selective_accuracy",
    "invalid_rate", "cost", "fallback_rate",
)

def wilson_interval(k: int, n: int, *, z: float = 1.96) -> tuple[float, float] | None: ...
def score(cases: list[CaseScore], *, truth_facts: dict[str, dict]) -> dict: ...
```

`n == 0` returns a null rate and a null Wilson interval. Counts stay zero.

```python
# eval/baseline.py
class BaselineVerdict(BaseModel):
    outcome: Literal["APPROVE", "APPROVE_WITH_CONDITIONS", "REQUEST_INFO", "ESCALATE", "DECLINE"]
    reasons: list[str]
    failing_controls: list[str]
    cited_fields: list[str]

def run_baseline(case_input: CaseInput, *, settings: Settings, tracer: Tracer) -> BaselineResult: ...
```

`BaselineResult` carries `outcome` (`INVALID` included), `reasons`, `failing_controls`, `cited_fields`, token counts, latency, and the trace path. The call is `generate(..., route="deep", response="json", schema=BaselineVerdict, purpose="baseline")`. `purpose="baseline"` is absent from `PURPOSES`, so the generator's default applies: temperature `0.0`, `max_tokens` 2048. Offline, timeout, and `ParseFailure` become `INVALID`. There is no deterministic verdict.

Evidence uses `get_backend` (DuckDB or Zetaris, plus `InlineBackend` for a submission). Queries are the intake profile plus `app.agents.planner.allowed_queries`, with parameters from `build_params` and `INCIDENT_WINDOW_DAYS`, so the baseline sees the same registry rows Arbiter is allowed to see. Answer and document text is passed through `app.guard.pii.redact` only. ScoutGuard is not applied.

```python
# eval/harness.py
def run(
    systems: list[str],
    splits: list[str],
    *,
    consistency: tuple[int, int] | None = None,
    concurrency: int = 1,
    llm: Literal["auto", "meterless", "nvidia", "offline"] = "auto",
    sample_mode: bool | None = None,
    results_root: Path = Path("eval/results"),
) -> Path: ...

def run_session(*, live: bool, results_root: Path = Path("eval/results")) -> Path: ...
```

`concurrency` is clamped to 1 or 2. Each case and each repeat gets a new temporary directory passed as `Deps.var_dir`, `ARBITER_MEMORY=off` (the session command is the exception), and its own trace directory. Arbiter runs go through `app.orchestrator.run`. A thin evaluator wrapper in `eval/harness.py` records `len(claims)` and how many have `grounded is True` after the real `EvaluatorAgent` returns. Those counts are the Arbiter grounding numerator and denominator. They come from the run, and they are stored on the case row because `CaseBundle` does not keep claims.

`arbiter_offline` forces `RunOptions.llm="offline"`. `arbiter` uses the requested `--llm`. A policy `ESCALATE` stays `ESCALATE`. A run that reached safe escalation (`escalation_reasons` non-empty) is stored as `ESCALATE` with `safe_escalate: true`. `APPROVE` stays `APPROVE` when the contract is `pending_approval`.

Artefacts under `eval/results/<UTC timestamp>/`:

- `cases.jsonl` — one row per case × system × repeat: outcome, reasons, failing controls, contradiction keys, guard block, trace path, tokens, latency, mode, safe-escalate flag, facts hash
- `summary.json` — per system, every key in `METRIC_KEYS`, plus split name, n, and the honesty header
- `summary.md` — `render_summary_md` of that JSON
- `confusion_<system>.csv` — expected outcome × predicted outcome, columns for the five outcomes and `INVALID`
- `env.json` — git sha, data mode, provider, model ids taken only from trace `model` fields, split sha256 map, calibration version from `policy/calibration/ACTIVE`, KEV `catalogVersion` from `data/kev/kev_snapshot.json`

```python
# eval/calibrate.py
def calibrate(
    records: list[DecisionRecord],
    labels: dict[str, str],
    *,
    out_dir: Path,
    active_path: Path | None,
    weights: dict[str, float],
    split_sha256: str,
    as_of: date,
) -> Path: ...
```

For each tier, try gates `0.60, 0.65, …, 0.95`. Each candidate builds a `Calibration` and calls `decide` on the stored `policy_inputs`. No model calls. Objective, per tier: maximum accuracy among gates with zero unsafe approvals on that tier's cases. Equal accuracy keeps the higher gate. Weights are copied from the active calibration and are not searched. The new file is never an overwrite of an older version. Version id: `cal-<as_of>-<first 8 hex of split_sha256>`.

```python
# eval/report.py
def render_summary_md(summary: dict) -> str: ...
def publish(summary: dict, *, docs_path: Path, readme_path: Path | None = None) -> None: ...
def latest_summary(results_root: Path) -> dict: ...
```

`publish` rewrites `docs/EVALUATION.md` from the summary. On the README it replaces only the bytes between the two markers, and it does nothing to the README when either marker is missing. A second call with the same summary writes the same bytes.

```python
# app/cli/eval.py
def cmd_eval(args: argparse.Namespace) -> int: ...
def cmd_calibrate(args: argparse.Namespace) -> int: ...
```

Flags already registered: `--split`, `--systems`, `--consistency` (`KxR`), `--llm`, `--publish`, `--session`. `--publish` with no new run publishes `latest_summary`. `--session` runs `run_session` and does not also run a split.

```python
# app/api/routes_meta.py
class EvalLatestResponse(BaseModel):
    results_dir: str
    summary_md: str
    summary: dict

@router.get("/eval/latest", response_model=EvalLatestResponse)
def eval_latest() -> EvalLatestResponse: ...
```

Missing results return the API's structured 404.

## Metric definitions

Scored from case rows and `data/evals/labels.jsonl` / `truth_facts.jsonl` inside `eval/` only.

| Metric | Definition |
|---|---|
| `accuracy` | Predicted outcome equals expected. `INVALID` counts as wrong. Report `correct`, `n`, `rate`, and Wilson 95% (`z = 1.96`): centre `(k + z²/2) / (n + z²)`, half-width `z · sqrt(k(n−k)/n + z²/4) / (n + z²)`. |
| `macro_f1` | Unweighted mean of per-outcome F1 over the five outcomes. A class with no expected and no predicted rows is left out of the mean. Mean is null when every class is left out. |
| `unsafe_approvals` | Predicted in `{APPROVE, APPROVE_WITH_CONDITIONS}` and expected in `{REQUEST_INFO, ESCALATE, DECLINE}`. Report count and `n`. |
| `over_escalations` | Predicted in `{ESCALATE, DECLINE}` and expected in `{APPROVE, APPROVE_WITH_CONDITIONS, REQUEST_INFO}`. |
| `failing_control_recall` | Micro: expected failing-control ids found on the prediction, divided by expected ids. Zero expected ids → null rate. |
| `contradiction_recall` / `precision` | Detected keys are the decision's contradiction keys. Recall is expected keys found ÷ expected. Precision is detected keys that were expected ÷ detected. A zero denominator is a null rate. |
| `injection_detection` | Labelled injection cases whose decision has a `block` guard flag and reason `UNTRUSTED_CONTENT_TAMPERING`, divided by injection cases. |
| `injection_false_positive_rate` | Non-injection cases with any `block` flag, divided by non-injection cases. |
| `fact_accuracy` | Arbiter only (null for the baseline). A truth-fact key matches when the decision fact has the same `state` and `value` (lists compared sorted). Also broken out per `control_id`. |
| `grounding_rate` | Arbiter: grounded claims ÷ extracted claims from the run wrapper. Baseline: `cited_fields` whose names occur in the evidence payload ÷ cited fields. Zero extracted or cited → null rate. |
| `consistency` | Among the K cases × R repeats: cases whose outcome is the same on every repeat, ÷ K. Arbiter also reports how many of those cases kept the same facts hash (`sha256` of canonical `(key, state, value)` sorted by key). Null when `--consistency` was omitted; the key is still present. |
| `abstention_rate` | Rows whose reasons include `LOW_CONFIDENCE_ABSTAIN`, ÷ rows. |
| `selective_accuracy` | Accuracy on rows that did not abstain. Null when every row abstained. |
| `invalid_rate` | Baseline rows with outcome `INVALID`, ÷ baseline rows. Null for Arbiter systems. |
| `cost` | Model-call events per case, tokens in and out per case, registry query events per case, latency p50 and p95 from the run's elapsed time. |
| `fallback_rate` | Trace events with `status == "fallback"`, ÷ trace events. |

`summary.md` states mode, provider, model ids from traces, date, git sha, split, n, and that the data is synthetic. A results directory whose traces contain `provider=offline` is labelled offline in that summary.

## Acceptance tests

Marker `@pytest.mark.p5b`. Ids go in the docstring. Offline tests set `SAMPLE_MODE=true` so CI uses the DuckDB mirror. They do not need Zetaris or Nightshift.

| Id | How it is tested |
|---|---|
| P5-T1 | Toy rows in `tests/unit/eval/test_metrics.py`: one hit and one miss per metric; empty input (null rates); every row abstaining (`selective_accuracy` null, `abstention_rate` 1); a baseline `INVALID` row counted wrong for accuracy and inside `invalid_rate`. |
| P5-T2 | Subprocess `python run.py eval --split test --systems arbiter_offline,baseline --llm offline` with `SAMPLE_MODE=true`. It exits 0. Baseline `invalid_rate` is 1. `summary.json` contains every `METRIC_KEYS` entry. |
| P5-T3 | Run offline Arbiter on the calibration split, call `calibrate` twice into a temp directory, and assert the two JSON files are byte-identical. Re-score those stored inputs at the chosen gates and assert `unsafe_approvals` is 0. `cal-initial.json` is still present. The test does not point the repo `ACTIVE` file at the temp result. |
| P5-T4 | Subprocess `python run.py eval --session` with cwd on a temp directory and `LLM_PROVIDER=offline`. It delegates to `demo-session --reset --yes` and exits 0, with six passing steps in the captured table. |
| P5-T5 | If `README.md` has no eval markers, the test skips (P6 has not published yet). Once markers exist, the block must equal `render_summary_md(latest summary.json)`. |
| P5-T6 | `scripts/check_hardcoding.py` exits 0 on this repo. A temp `app/*.py` that mentions `labels.jsonl` is reported by `scan_path`. |
| P5-T7 | A fixture trace whose `model` is `from-trace-model` and whose `provider` is `offline` produces `env.json` model ids equal to that trace value, and `summary.md` says offline. The assertion reads the trace file, not `Settings` model names. |
| P5-T8 | `publish` twice on a temp docs file and a temp README that contains the markers. The second write is byte-identical. A sentinel line outside the markers is unchanged. With the markers removed, the README bytes are unchanged. |

`scripts/gates/p5b.py` runs the same command as P5-T2 on the **inline** split (4 cases × 2 systems) and checks that `summary.json` has every metric key. P5-T2 already covers the test split during `verify-pass`, so the gate does not run those 16 cases a second time.

## Workflow after approval

1. Set `.cursor/ACTIVE_PASS` to `5b build`.
2. Add the tests, commit `test(p5b): acceptance tests`, and confirm they fail because the stubs are empty.
3. Implement until `python scripts/tasks.py verify-pass --pass 5b` is green. Small Conventional Commits.
4. Run §B6 step 1 (offline, all splits, `arbiter_offline` and `baseline`). Then stop for you before the live calibration, test, and session commands.
5. Write `docs/passes/P5-B_REPORT.md` and `docs/cursor-usage/P5-B.md`. If the live run has not happened, the report says the published numbers are offline and why.
6. Push `p5b-eval`, delete `.cursor/ACTIVE_PASS`, stop.

## Risks

- P5-T2 runs the full test split (16 vendors) through offline Arbiter and the baseline. P5-T3 runs the calibration split (16) through offline Arbiter. That is several minutes inside `verify-pass`. The runs are the acceptance tests, so they stay.
- `app/orchestrator.py` writes the outbox to `Path("var") / "outbox"`. Case store, memory, and traces are isolated per case. The outbox directory is not. With `ARBITER_MEMORY=off`, a previous outbox file does not change the next decision. I will leave the orchestrator alone.
- `Calibration` in `app/policy/loader.py` is `extra="forbid"` and only has `version`, `gates`, and `weights`. A calibration file that also contains `split_sha256`, `objective`, and `calibration_results` will not load, and `load_default()` will break the app.
- `cases.jsonl` is gitignored. `summary.json`, `summary.md`, `env.json`, and the confusion CSVs can be committed. Published numbers are rendered from `summary.json`.
- Baseline completion budget is 2048 tokens via the generator default. A live reasoning model can spend that budget before it emits JSON and then score `INVALID`. See question 2.
- Zero unsafe approvals on the **test** split is a design issue. If the offline or live test split breaks that, I will stop and tell you instead of moving gates to fit the test split.

## Questions

1. **Calibration file shape.** Resolved: option A. Optional fields on `Calibration`.
2. **Baseline token budget.** Unchanged: stay in-lane. `purpose="baseline"` uses temperature 0.0 and 2048 tokens.
3. **Live §B6.** Not in this lane. Offline DuckDB only. The report will say the numbers are offline.
