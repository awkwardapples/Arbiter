# P19 report: fixes a judge would find

Branch `p19-fixes`. Built in Claude Code (Claude Opus 5.5) from the approved plan `.cursor/plans/P19.md`. No decision logic changed: `app/policy/` is untouched, and the six example outcomes still match `input_examples/expected.json`.

## What was built

| Fix | Finding | Result |
|---|---|---|
| F1 | C1 | `docs/IMPACT.md` §3 now says "16.6 s of Zetaris time". That is the sum of `latency_ms` over the 12 `query_zetaris` events in `logs/examples/live/trace-run-83de5da137c0.jsonl` (16 584 ms) |
| F2 | B10, C2 | `app/store.py` adds a `machine_decisions` table with `put_machine_decision` and `machine_decision_for`. `POST /cases/{id}/review` keeps the machine record before the human record replaces it. `app/audit/replay.py` handles a human-reviewed case on its own path (below). `run.py replay` prints the override sentence to stderr |
| F3 | C3 | `docs/PRIOR_WORK.md` §1 "How" and §2 "Code reused" now use the text you approved. Typos and double spaces are fixed |
| F4 | C8, B11 | New `GET /eval/latest` returns `{live, offline, live_markdown, offline_markdown}` from the newest run under `eval/results_live/` and `eval/results/`. It reads summaries only and gives a structured 404 when neither exists. The Streamlit Evaluation page shows "Live evaluation" first, then "Offline benchmark". `EVAL_SUMMARY_PATH` is removed |
| F5 | C7, C9, B12 | New spinner text, exactly as the spec gives it. `_served()` reads `model`, then `routed_model`, then `winning_route.model`, and never `provider_model`. New `.streamlit/config.toml` sets `toolbarMode = "minimal"`. `scripts/capture_ui.py` clicks "Don't show again" on the skills popover |
| F6 | C11 | `NVIDIA_MODEL_DEEP` now defaults to `nvidia/nemotron-3.5-super-vl-120b-a12b` in `app/config.py` and `.env.example` |
| F7 | B13 | The shared AppTest helper `_run_page` (`tests/unit/ui/test_pages_smoke.py`) passes `default_timeout=15`. Every UI module except P14-B's goes through it, so `test_p10_new_assessment_how_to_use` gets the timeout too. `p14b_support.py` already used 30 |
| F8 | — | `app/labels.py` replaces `_AUDIENCE` with `_HEADLINE_LEAD`, one phrase per outcome. The no-points "Approve: … meets the checks" form is unchanged |

### Replay of a reviewed case (F2)

A stored record with `outcome_reasons == ["HUMAN_REVIEW"]` is replayed in three parts.

1. **Machine.**
   - **Stored machine record** (`machine_source: "stored"`): replay runs today's checks on it. Those are the policy hash, recompute through `decide`/`force_escalate`, the record and content hashes, the facts diff and the outcome. It also checks that the human record equals the machine record except for `outcome`, `outcome_reasons`, `run_id`, `created_at` and `record_sha256` (`review.record`).
   - **No stored machine record** (a case reviewed before P19, `machine_source: "reconstructed"`): replay re-decides from the human record's `policy_inputs`. It checks the policy hash, the human record's content hash and the facts diff.
2. **Review.** The latest review must exist (`review.missing`). Its `decision` must equal the stored outcome (`review.decision`) and its `human_run_id` the stored `run_id` (`review.run_id`). The human record's content hash must hold (`review.record_hash`). The reviewer's role must be a policy role whose rank is at least the highest rank in `required_approvals` (`review.role`).
3. **Signatures.** Checked as before.

`match` requires all three. `ReplayResult` gains `human_override`, `machine_outcome` and `machine_source` (additive). All three are `None` for unreviewed cases, which follow the unchanged path.

## Deviations from the spec (with reasons)

- **"Written once" became a save per review (approved after the fact).** The spec asks for the machine record to be written once, the first time a review replaces the record. The demo session resets `var/` but keeps `arbiter.db`, so it re-runs VND-0011 and reviews it a second time. With `INSERT OR IGNORE`, the kept record was the stale step-1 run, and the new `review.record` check failed. The store now uses `INSERT OR REPLACE`. The review route writes only when the record being replaced is a machine record, so a second review of the same decision still keeps the first machine record.
- **Evaluation page caption.** `EVAL_CAPTION` described "two views", which is wrong now that there is a live section. It now reads "Three views: the published live evaluation, the offline benchmark on a fixed labelled set, and this instance's own activity." There is also a new `EVAL_LIVE_CAPTION` in `ui/components.py`.
- **The `FakeArbiterClient` default changed.** `eval_latest_404` now defaults to `False`, and the fake returns the real committed payload (`published_eval()` in `tests/unit/ui/conftest.py`). Tests that need the 404 path set it to `True`.
- **The spinner constant keeps its name.** The plan called it `RUN_SPINNER`; the existing name `ASSESSMENT_SPINNER` is kept.

## Files outside lane 19 (approved exceptions)

- `app/cli/audit.py`: the override sentence (plan exception).
- `.env.example`: one line, edited with `sed` (plan exception).
- `tests/unit/docs/test_impact_numbers.py`: a new file (plan exception).
- `scripts/capture_ui.py`: the popover click (Q3).
- `tests/unit/llm/test_resolve.py::test_p2_t15_auto_falls_back_to_nvidia`: the expected deep model is now the new default (approved mid-lane). The test still checks the fallback to NVIDIA.
- `tests/unit/ui/test_p12.py`: import order only. The logo fix merged from `main` (3c8cefa) left the imports unsorted, which failed lint.
- `docs/CURSOR_USAGE.md`: regenerated by `scripts/compile_cursor_usage.py` to include this lane's note. P17-T11 requires it to match the compiler output.

## Tests updated for the new behaviour

None was removed or skipped. Each test now reads the page through `/eval/latest`, not a patched path:

- `tests/unit/ui/test_pages_smoke.py::test_p5_t14_eval_not_published_on_404`: the 404 path, then the published payload.
- `tests/unit/ui/test_p10.py::test_p10_eval_offline_caption`.
- `tests/unit/ui/test_p12.py`: `_evaluation`, `_PAGE_CAPTION` (the new caption), and `test_p12_eval_sections`, whose subheader list now starts with "Live evaluation".
- `tests/unit/ui/test_p9.py::test_p9_eval_renders_summary_when_present` and `test_p9_eval_fallback_when_summary_missing`.
- `tests/unit/ui/test_polish.py`: `SPINNER_TEXT` is now the F5 sentence.
- `tests/unit/llm/test_resolve.py`: see above.

No existing test asserted the old F8 headline strings.

## Acceptance tests (marker `p19`)

| Id | File |
|---|---|
| P19-T1 | `tests/unit/docs/test_impact_numbers.py` |
| P19-T2 | `tests/unit/audit/test_p19_replay.py`: CASE-0011 after the demo session (`match`, `ESCALATE`, override `APPROVE_WITH_CONDITIONS`, `stored`, CLI stderr), a tampered human outcome, unreviewed CASE-0003, and a reconstructed pre-P19 case |
| P19-T3 | `tests/unit/api/test_p19_eval_latest.py`, `tests/unit/ui/test_p19_eval_page.py` |
| P19-T4 | `tests/unit/ui/test_p19_provider.py` |
| P19-T5 | `tests/unit/api/test_p19_health.py` |
| P19-T6 | `tests/unit/labels/test_p19_headlines.py`: the six examples, plus one record with why-points under all five outcomes |

## Known gaps

- **P14-A UI fixtures.** `tests/fixtures/ui/p14a_case_request_info.json` still holds the old headline "Request information to the vendor: …". The repo has no recording script, and F8 forbids hand edits (Q2). No test compares the fixture with `labels.py`.
- **`output_examples/` and the screenshots** still show the old headlines and the old Streamlit chrome. P20 regenerates and re-captures them.
- **The second-review rule has no test of its own.** It is covered only by reading the code: the route skips the machine write when the record it replaces is a human one.

## Commands run

```
.venv/bin/python -m pytest -m p19                      # 15 failing at test(p19), then all green
git merge origin/main                                  # brings in the RGBA logo and the P12-T5 fix (3c8cefa)
.venv/bin/python scripts/compile_cursor_usage.py [--check]
python scripts/tasks.py verify-pass --pass 19          # green
```
