# P6: Hardening, real examples, README and sponsor docs (Docker and the clean-clone check were built in P4-B)

## 1. Goal

A judge with an ordinary laptop and **no credentials** can do all of the following with nothing but the README:

- `docker build`;
- `docker run -e SAMPLE_MODE=true`;
- `curl /run` on three or more examples;
- read the traces;
- see sponsor use explained with file references.

A judge **with** Zetaris and Nightshift can run live by following the README. Every claim in the docs is backed by code, tests or traces.

## 2. Why it scores

- **Technical:** reproducibility.
- **Disqualification checklist:** "can a judge run it", sample mode, no secrets, no hardcoding.
- **Sponsor Tech:** the explanation.
- **Impact:** clarity.

## 3. Read first

- `04_SUBMISSION_PLAYBOOK.md` §§1, 4, 5, 6
- The Technical Execution Guide and Disqualification Checklist (as summarised in 04)
- Master spec §§9–14

## 4. Deliverables

| File | Responsibility |
|---|---|
| `app/cli/examples.py` | `python run.py examples [--live]` runs every input example through the **real** system with `ARBITER_MEMORY=off` and a fresh temporary `var/` (so no example depends on an earlier run) and writes `output_examples/<name>_output.json` (the response plus a header `{generated_by: "python run.py examples", run_id, mode, git_sha, generated_at}`) and copies the trace to `logs/examples/trace-<run_id>.jsonl`. **Live mode is preferred for committed examples.** If a live run is impossible, generate in sample mode and say so in the header and README |
| `README.md` | Full README (§5) |
| `docs/ARCHITECTURE.md` | Mermaid diagrams: layers, the state machine with loops, the agent authority table, the data path (simulator → Zetaris REST tables → views → USL → registry → agents), the memory governance flow, and contract signing and verification |
| `docs/SPONSORS.md` | 04 §4, finalised. **Every claim links to a file and to a trace line** in `logs/examples/` |
| `docs/DEMO_SCRIPT.md` | 04 §2.2 with the actual run ids; a 5-minute live-demo variant for any finalist session |
| `docs/trace_schema.json` | Exported from `TraceEvent.model_json_schema()` |
| `metadata.json` | 04 §5. Model ids come from the latest eval `env.json` |
| `scripts/check_metadata.py` | Validates the JSON structure; every `files` path exists; `track` equals the README track; model ids appear in at least one `logs/examples` trace |
| `data/README.md`, `vendor/meterless/NOTICE*.md` | Final review |
| `.env.example` | Final review: every variable is documented with a comment |

## 5. README structure (exact order; follow the "Strong README" pattern)

1. **Title, badges** (CI, track: Reasoning Architecture), a one-line description, a demo video link, and a quick-start box (Docker sample mode in three commands).
2. **Problem and users**: DBIR 2026 statistics with a citation, the TPRM analyst, and why onboarding is the control point.
3. **What Arbiter does**: input → five outcomes; cited facts; counterfactuals; signed action. "All enterprise data is synthetic; CISA KEV is real public data."
4. **Agents**: the authority table (master spec §6.1) with a "can block or retry?" column.
5. **What makes this an agent system**: loops (Evaluator → Planner, Challenger → Planner), the policy decides, a verifier with SoR re-queries, governed memory, approval gates, and a real trace excerpt (from `logs/examples`, with its run id).
6. **Architecture**: a mermaid diagram plus a link to `docs/ARCHITECTURE.md`.
7. **Tech stack**: a table.
8. **Setup**:
   - (a) Docker, sample mode with no credentials;
   - (b) native Python;
   - (c) live mode: Zetaris onboarding (`python run.py zetaris onboard`), Nightshift setup, `.env`, `python run.py preflight`.
9. **Usage**: curl `POST /run` for examples 1–3 (shown with abridged responses), a judge's own inline submission, the CLI commands, the console (`python run.py ui`) and the review/approval endpoints.
10. **Sample mode**: exactly what runs and what is cached; deterministic fallbacks are labelled `provider: offline` in traces.
11. **Failure handling**: the table from master spec §12.
12. **Evaluation**: the `<!-- EVAL:START -->…<!-- EVAL:END -->` block (generated) plus a link to `docs/EVALUATION.md`.
13. **Sponsor technology**: Zetaris, Meterless, NVIDIA, Cursor and "what was unique" (from `docs/SPONSORS.md`).
14. **AI and model usage** (AI Usage Policy §6): models, providers, frameworks (none: an explicit state machine), and development tools ("Developed in Cursor; architecture specification and reviews drafted with Claude (Anthropic) outside the repo; all code written and committed through Cursor and reviewed by me").
15. **Data and licensing**: synthetic data, CISA KEV CC0 attribution, regeneration commands.
16. **Third-party code and licences**: FastAPI, pydantic, DuckDB, Streamlit, httpx, tenacity, PyYAML; Meterless H-MEM vectors and Scout eval cases (Apache-2.0, ported and copied with notices).
17. **Limitations**: honest; from master spec §§4 and 13 and 03 §6.
18. **Responsible AI**: human approval for exceptions and declines, the injection guard, no autonomous external actions.
19. **Pre-existing components**: 04 §7 text.
20. **Repository map**.

## 6. Acceptance tests (marker `p6`)

| Id | Test |
|---|---|
| P6-T1 | README section headers exist in the order of §5. Every `python run.py <cmd>` and `python scripts/tasks.py <cmd>` in README code blocks is a registered command (parsed with argparse) |
| P6-T2 | `check_metadata.py` passes |
| P6-T3 | Every `output_examples/*_output.json` header `run_id` has a matching `logs/examples/trace-<run_id>.jsonl`, which passes `check_trace --require-collaboration` (as in P3-T9, every example has a verify loop) and `--require-live` when the header says live |
| P6-T4 | Re-run P4-T17 (Docker sample smoke) and `clean_clone_check.py` against the **public GitHub URL**; attach the report |
| P6-T5 | `scan_secrets.py --history` is clean on the full git history |
| P6-T6 | The README eval block matches the latest summary (P5-T5 becomes mandatory here) |
| P6-T7 | Every file path mentioned in `docs/SPONSORS.md` exists, and every quoted trace line exists verbatim in `logs/examples` |

## 7. Verification

```
python run.py examples --live
docker build -t arbiter . && docker run --rm -p 8000:8000 -e SAMPLE_MODE=true arbiter
curl -s -X POST localhost:8000/run -H "Content-Type: application/json" -d @input_examples/example_1.json
python scripts/clean_clone_check.py https://github.com/<you>/arbiter
python scripts/tasks.py verify-pass --pass 6
```

## 8. Definition of done

- [ ] `clean_clone_check` is all PASS (attach the report).
- [ ] CI is green, including Docker.
- [ ] I have reviewed the README line by line for overclaiming.

## 9. Cut lines

The compose `ui` service (document `python run.py ui` instead); mermaid diagrams beyond two.

## 10. Cursor prompt

```
/start-pass 6
You are implementing pass P6 of Arbiter: real examples, README, metadata.json and sponsor documentation (Docker/CI already exist from P4-B).
Read: AGENTS.md; docs/spec/03_EVALUATION.md §6; docs/spec/04_SUBMISSION_PLAYBOOK.md §§1, 4, 5, 6; docs/spec/00_MASTER_SPEC.md §§9–14; docs/spec/passes/P6_HARDENING_DOCS.md.
Every sentence in README/SPONSORS must be true of the code; link a file or trace line for every capability. Never hand-write or edit an output example or trace: generate with `python run.py examples`.
Plan Mode: .cursor/plans/P6.md with files, README outline and tests P6-T1..P6-T7. Wait for approval.
Tests first (marker p6) → commit → implement until `python scripts/tasks.py verify-pass --pass 6` is green; run clean_clone_check with me.
Finish with docs/passes/P6_REPORT.md + docs/cursor-usage/<LABEL>.md; push p6-hardening; delete .cursor/ACTIVE_PASS; stop.
```

## 11. Explain it

1. What exactly happens when a judge runs the Docker image with no credentials?
2. Which README claims would a sceptical judge check first, and where is the evidence?
3. Why must output examples be generated, never written?
4. How is Nightshift reachable in live mode, and why not from Docker?
5. What is declared as pre-existing, and why?
