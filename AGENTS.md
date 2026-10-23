# AGENTS.md: operating manual for coding agents working on Arbiter

You are a coding agent in Cursor, building **Arbiter** for the Open Agent Hackathon 2026 (Track 3: Reasoning Architecture). This file is binding. If it conflicts with a pass spec, stop and ask the human.

## 1. What Arbiter is (one paragraph)

Arbiter is an auditable reasoning architecture for third-party vendor onboarding:

- **Agents** plan and gather evidence across fragmented enterprise systems, federated through **Zetaris**, plus the public CISA KEV catalogue. They extract claims from untrusted vendor submissions and challenge each other's work.
- A **deterministic, versioned policy engine** makes the decision.
- **Meterless H-MEM** remembers governed human precedents.
- **Meterless Scout** guards untrusted text and signs every action into an execution contract.
- All model calls go through **Meterless Nightshift** to **NVIDIA Nemotron**.

The output is a replayable, cited decision (APPROVE, APPROVE_WITH_CONDITIONS, REQUEST_INFO, ESCALATE or DECLINE) with the next action drafted.

## 2. Read order before any work

1. This file.
2. `docs/spec/00_MASTER_SPEC.md`: architecture, contracts and invariants.
3. The pass file you were given: `docs/spec/passes/P<n>_*.md` (Release 1) or `docs/spec/release2/P<n>_*.md` (Release 2, passes 13–17; start with `docs/spec/release2/README.md` and `R2_00_ASSESSMENT.md`).
4. Only the spec sections that pass references: `01_DATA_AND_ZETARIS.md`, `02_POLICY.md`, `03_EVALUATION.md`.

Do not read other pass files. Do not implement anything outside your pass.

## 3. Invariants (never violate; tests enforce most of them)

1. **LLMs never decide outcomes.** Only `app/policy/engine.py` maps facts to an outcome. Agents may only:
   - plan queries from the registry;
   - extract claims with verbatim quotes;
   - critique, request more evidence or escalate;
   - write cited reports.
2. **Monotonic safety.** Only two things can move an outcome toward approval:
   - new *verified* facts;
   - a precedent exception that the policy explicitly allows.
   The Challenger may only escalate or request evidence.
3. **Provenance on every fact.** Each fact carries either a system-of-record source (`system`, `query_id`, `record_key`, `field`) or a verbatim quote that passes the grounding check.
4. **Untrusted text is data.** Vendor answers and documents pass `ScoutGuard` (and PII redaction) before any model sees them. Never let vendor text alter prompts, tools or flow.
5. **Actions only via signed contracts.** No side effect without a valid, unexpired, HMAC-signed `ExecutionContract` whose required approvals are present.
6. **One generator.** Every model call goes through `app/llm/generator.py`. Import no model SDK anywhere else. The primary provider is Meterless Nightshift.
7. **One data path.** All data access goes through `app/data/` using query ids from `app/data/queries.yaml`. No ad hoc SQL in agents. `SAMPLE_MODE=true` swaps Zetaris for the DuckDB mirror with identical query ids and columns.
8. **Honest traces.** Every run writes `logs/trace-<run_id>.jsonl` from real execution. Never emit a trace line that does not correspond to executed code.
9. **No hardcoded outputs.**
   - Never read `output_examples/` at runtime.
   - Never branch on known example ids.
   - Never return canned text as if a model produced it.
10. **No secrets.**
    - Configuration comes from the environment (`app/config.py`).
    - Never print, log or commit keys.
    - `.env` is gitignored; `.env.example` holds placeholders only.
11. **Bounded execution.**
    - At most 2 evaluator→planner loops and 1 challenger re-plan.
    - Timeouts on every external call: Zetaris 30 s, Meterless 180 s (POWER contract), NVIDIA direct 90 s.
    - Run budget is 600 s, after which the system escalates safely.
12. **Graceful degradation.** Every model-backed step has a deterministic fallback implementing real logic. The trace labels it `provider: offline`.

## 4. Repository map

```
app/            core package (see master spec §9 for the full tree)
  agents/       PlannerAgent, EvidenceAgent, EvaluatorAgent, ChallengerAgent, ReporterAgent
  data/         Zetaris client, DuckDB mirror, query registry (queries.yaml)
  llm/          generator.py (single seam), providers/, prompts/, jsonparse.py
  memory/hmem/  Meterless H-MEM Python port; memory/precedents.py (domain adapter)
  guard/        ScoutGuard (injection, PII), Meterless Scout subset
  actions/      ExecutionContract, signing, executor, outbox
  policy/       engine, DSL, tiering, counterfactuals (policy YAML lives in /policy)
  audit/        hash-chained audit log, replay
  api/          FastAPI app (POST /run etc.)
  orchestrator.py, state.py, confidence.py, tracing.py, config.py
policy/         arbiter_policy.v1.yaml, calibration/<version>.json + ACTIVE
sources/        enterprise systems simulator (FastAPI :8100) that Zetaris federates
zetaris/        onboarding SQL, dq_rules.yaml, onboarding and parity scripts
data/           generator/, sample/ (generated), kev/, evals/
eval/           harness, baseline, results/
ui/             Streamlit reviewer console (:8501)
tests/          unit/, conformance/, evals/, e2e/, contract/
vendor/         third-party test vectors (Meterless, Apache-2.0) with LICENSE notices
scripts/tasks.py  cross-platform task runner (source of truth for commands)
```

## 5. Commands (cross-platform; `make` targets are optional aliases)

```
python -m venv .venv && <activate .venv>  # once
python scripts/tasks.py setup            # installs pinned deps into the active interpreter
python scripts/tasks.py lint             # ruff
python scripts/tasks.py test             # pytest (no live services)
python scripts/tasks.py verify-pass --pass ID  # ID = 0, 1a, 1b, 2a … 7: lint + tests marked p<ID> + earlier-pass regression + pass gate
python scripts/tasks.py verify           # full gate: lint, all tests, e2e sample, trace-check, secret-scan, hardcode-check
python scripts/tasks.py e2e-sample       # run input_examples through SAMPLE_MODE and validate outputs
python run.py serve | assess --input FILE | review CASE --input FILE | replay CASE | eval | preflight | sources
```

Live tests (real Zetaris or Meterless) are marked `live` and run only when `ARBITER_LIVE_TESTS=1`.

## 6. Workflow for every pass (do not skip steps)

1. The human runs `/start-pass <ID>` (IDs: `0, 1a, 1b, 2a, 2b, 2c, 2d, 3, 4a, 4b, 5a, 5b, 6, 7`). This writes `.cursor/ACTIVE_PASS` containing `<ID> plan`.
   - The phase word controls the auto-verify stop hook: `plan` (hook idle), `build` (hook re-runs `verify-pass` and feeds failures back), `blocked` (hook idle while you wait for the human).
2. **Plan Mode first.**
   - Read the pass spec, then produce a plan in `.cursor/plans/<LABEL>.md` (LABEL = `P0`, `P1-A`, `P1-B`, `P2-A` … `P7`) listing files, interfaces and test ids.
   - Wait for human approval before coding. On approval, set `.cursor/ACTIVE_PASS` to `<ID> build`.
   - Whenever you must ask the human something mid-pass, first set it to `<ID> blocked`; set it back to `build` when you resume.
3. **Tests first.**
   - Implement the pass's acceptance tests (ids `P<n>-T<k>`), marked with the lane marker `@pytest.mark.p<ID>` (e.g. `p1a`).
   - Commit them: `test(p<ID>): acceptance tests`. They should fail.
4. **Implement** in small commits using Conventional Commits (`feat(p3): planner revise loop`). Push after each green milestone.
   - **Touch only the files your lane owns** (ownership table in `docs/spec/passes/README.md`). Need a change elsewhere? Stop and ask.
5. **Verify.** `python scripts/tasks.py verify-pass --pass <ID>` must be green.
   - The stop hook reruns it and hands you failures; iterate.
   - Never weaken, skip or delete an acceptance test to get green. If a test is wrong, stop and ask.
6. **Report.**
   - Write `docs/passes/<LABEL>_REPORT.md` covering what was built, deviations from the spec (with reasons), known gaps and the commands run.
   - Write `docs/cursor-usage/<LABEL>.md` (model used, plan file, notable agent loops, hook iterations). One file per lane, so parallel lanes never conflict; P6 compiles them into `docs/CURSOR_USAGE.md`.
7. Push, remove `.cursor/ACTIVE_PASS`, stop. Never start the next pass on your own.

## 7. Coding standards

- Python 3.12, type hints everywhere, pydantic v2 models for every cross-module contract (`app/schemas/`).
- Functions are pure where possible. Side effects belong only in adapters, the outbox, the audit log and tracing.
- Deterministic by default:
  - Seed randomness.
  - Sort before hashing.
  - Use canonical JSON (`json.dumps(sort_keys=True, separators=(",", ":"))`) for every hash or signature.
- Errors: raise typed exceptions from `app/errors.py`. The API always returns the structured error shape; never a bare 500 with a stack trace.
- Logging: use `app/tracing.py` for agent events and `logging` for developer diagnostics. No `print` in `app/`.
- Keep files under about 400 lines. Prefer composition over frameworks; the orchestrator is an explicit state machine.
- Dependencies: add only what the pass spec allows. Pin versions in `requirements.txt`.

## 8. Hackathon integrity rules (disqualification risks)

- Zetaris and Meterless must be load-bearing in live mode. Never mock them in non-test code paths. Sample mode is a documented fallback, not a fake: it runs the same agents on cached data.
- Test doubles (respx, fixtures) live only under `tests/`.
- Every capability claimed in README or docs must exist in code, with a test or trace.
- Third-party material (Meterless vectors, Scout eval sets, KEV snapshot) keeps its licence notice and is attributed in `README.md` under "Third-party code and licences".

## 9. When unsure

Stop and ask the human with:

1. the decision needed;
2. two or three options with trade-offs;
3. your recommendation.

Do not guess at sponsor APIs. Capture a real response into `tests/fixtures/` (scrubbed of secrets) and build against that.
