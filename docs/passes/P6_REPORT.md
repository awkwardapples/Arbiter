# P6 report

Built on `p6-harden`. `python scripts/tasks.py verify-pass --pass 6` is green (12 P6 tests passed, 1 skipped; regression 615 passed, 4 skipped). The skipped P6 test is the public-URL clean clone. The local clean clone ran as P4-T18 and passed all eight steps.

## What was built

- `python run.py examples` runs each `input_examples/example_*.json` through `orchestrator.run` with `ARBITER_MEMORY=off`, a fresh temporary `var/`, `SAMPLE_MODE=true`, and `LLM_PROVIDER=offline`. It writes `output_examples/<name>_output.json` and adds `logs/examples/trace-<run_id>.jsonl`. It does not delete older traces. `--live` is implemented and was not used for the committed files.
- `python run.py assess` calls `orchestrator.run` and prints the `RunResponse` JSON that `POST /run` returns. `--llm` is optional, so `LLM_PROVIDER` in the environment is kept. Clean-clone step 7 now passes as `run.py assess`.
- `scripts/check_metadata.py` checks the playbook shape, that every cited sponsor path exists, that `track` is `Reasoning Architecture` and appears in the README, and that each top-level `models` id appears in `logs/examples`. NVIDIA catalog ids are not required to appear in traces.
- README in the pass §5 order, `docs/ARCHITECTURE.md` (six mermaid diagrams), `docs/SPONSORS.md` (file paths and verbatim trace lines), `docs/DEMO_SCRIPT.md`, `docs/trace_schema.json` from `TraceEvent.model_json_schema()`, `metadata.json`, and `docs/CURSOR_USAGE.md`.
- Clean-clone step 1 requires at least three files in `output_examples/` and fails if the directory is missing. Step 3 publishes the container on a free host port and checks that each response `run_id` has a trace under `/app/logs` in the container.
- `scripts/scan_secrets.py --history` now applies `.secrets-allowlist`, which the tree scan already did. Fixture files that the assignment pattern flags were added to that list.

## Examples and mode

All six committed outputs are offline sample runs (`mode.data=duckdb`, `mode.llm=offline`, `provider=offline`, `n_runs=1`). Header `git_sha` is `f3415c3c844e9f4a95a3f6a007b5d30f0529ae9c`. None were produced with `--live`.

| File | Vendor | Outcome | Run id |
|---|---|---|---|
| example_1 | Pellucid Forms Ltd | APPROVE | `run-a1ad72bed1f3` |
| example_2 | Quillfeather Payroll Cloud Ltd | ESCALATE | `run-3d6b7460d393` |
| example_3 | Oakhaven Mail Relay Ltd | ESCALATE | `run-ac35d0a215a4` |
| example_4 | Fennimore Survey Tools Ltd | REQUEST_INFO | `run-be10a4e1768e` |
| example_5 | Corvid Ledger Services Ltd | DECLINE | `run-3a3fda966d5f` |
| example_6 | Inline Clean T3 Ltd | APPROVE | `run-c97e248333c6` |

The earlier P5-B traces under `logs/examples/` are still there. `eval/results/` and `docs/EVALUATION.md` were not rewritten. The README eval block is `render_summary_md` of the existing summary, between the markers.

## Clean clone

Local run (`python scripts/clean_clone_check.py --local .`), also P4-T18. Report: `docs/passes/clean-clone-2026-10-23.md`.

```
step 1: pass — ok
step 2: pass — built from Dockerfile
step 3: pass — 6 examples matched on host port 42922
step 4: pass — traces ok
step 5: pass — novel decision REQUEST_INFO
step 6: pass — secret scan ok
step 7: pass — run.py assess
step 8: pass — report written
```

Step 3 did not use host port 8000. The public URL `https://github.com/awkwardapples/Arbiter` was not cloned. That URL still serves the default branch, which does not contain this commit. Re-run with `ARBITER_CLEAN_CLONE=1` after this branch is what that URL checks out.

## Deviations

- Committed examples are sample/offline, not live. `--live` remains on the command.
- Each example is one run (`n_runs=1`). The P5-B header fields (`p50_ms`, `n_runs`, `mode`, `provider`, `timing_note`) are still present. `generated_by` is `python run.py examples`.
- P4-T18's missing-directory case is now a failure (`output_examples/ needs at least 3 files`). The test is stricter. It was not deleted or xfailed.
- `scan_history` honors the allowlist. Added allowlist entries: `tests/unit/llm/test_resolve.py`, `tests/unit/llm/test_meterless.py`, `tests/live/test_meterless_live.py`, `docs/cursor-usage/P2-A.md`, `docs/cursor-usage/P4-B.md`. These are fixture kwargs and prose that quote the assignment pattern, not live keys. Shaped-key patterns (`nvapi`, `sk-`, and the rest) still apply outside the allowlist.
- `app/cli/run_case.py` and `scripts/clean_clone_check.py` were edited. Both were approved exceptions. `app/policy/`, `app/orchestrator.py`, `app/agents/`, `app/memory/`, `app/audit/`, and `app/guard/` were not edited.
- `scripts/tasks.py` `e2e-sample` is still the P0 stub. Out of scope for P6.
- `.env.example` was reviewed against master spec §10. Every variable already has a comment. No edit.
- `data/README.md`, `vendor/meterless/NOTICE.md`, and `NOTICE-scout.md` were reviewed. They already label synthetic data, CC0 KEV, and Apache-2.0. No edit.
- `metadata.models` is `[]`, copied from `eval/results/20261022T080517661769Z/env.json`. The DBIR 48% figure is in the README with the Verizon PDF and news URL. It matches those pages (48%, up from 30%).

## Commands

```
python run.py examples
python scripts/tasks.py verify-pass --pass 6
```

The first verify-pass failed at P4-T18 because that process could not see the Docker socket. The rerun, with the daemon reachable, was green. `python scripts/scan_secrets.py --history` is clean.

## Explain it

1. A judge who runs the image with `SAMPLE_MODE=true` and no `.env` gets the API on port 8000, the DuckDB mirror, and the same agents and policy. If Nightshift is not reachable, model steps use the offline fallback and the trace says `provider: offline`. No credential is read.
2. A sceptical judge should check three things first. The six output headers say `generated_by` is `python run.py examples` and each `run_id` has a trace that passes `check_trace --require-collaboration`. The README block between the eval markers equals `render_summary_md` of `eval/results/20261022T080517661769Z/summary.json`, and that block says offline. Every `jsonl` line in `docs/SPONSORS.md` is a full line from `logs/examples/`.
3. Output examples have to be generated because a hand-written trace would claim a run that did not happen. The header records the run id, the mode, and the git sha of the code that actually ran.
4. In live mode Nightshift is the host process on `127.0.0.1` (console default port 8088). The API must run on the host so it can reach that loopback. A container cannot. Docker is the no-credential sample path.
5. Pre-existing work is the design docs from 20–21 Oct 2026, the problem narrative from Vendor-Risk-Assessment-Agent with no code reused, market-research slide material, and the Apache-2.0 Meterless vectors plus CC0 KEV. Synthetic enterprise data was generated in the build window. Detail is `docs/PRIOR_WORK.md`.
