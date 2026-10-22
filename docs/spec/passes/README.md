# Pass plan: index, lanes, ownership and template

Arbiter is built in **8 passes (P0–P7)**, split into **14 lanes**. Independent lanes run as parallel Cursor agents in separate git worktrees. **At most three agents run at once**, because the human is the review bottleneck.

## 1. Dependency graph

```
P0 bootstrap ─┬─► P1-A data world + DuckDB ──► P1-B Zetaris live ─┐
              ├─► P2-A H-MEM port ─────────────────────────────────┤
              ├─► P2-B LLM layer + Nightshift ─────────────────────┤
              ├─► P2-C policy engine ──────────────────────────────┤
              └─► P2-D guard + contracts + audit chain ────────────┤
                                                                   ▼
                                       P3 agent loop (single lane, the core)
                                                   │
                                     ┌─────────────┴─────────────┐
                                     ▼                           ▼
                       P4-A memory, precedents, review   P4-B case store, approvals, replay, API
                                     └─────────────┬─────────────┘
                                     ┌─────────────┴─────────────┐
                                     ▼                           ▼
                           P5-A reviewer console          P5-B eval + calibration
                                     └─────────────┬─────────────┘
                                                   ▼
                                   P6 hardening, Docker, docs, examples
                                                   ▼
                                     P7 submission (human-led)
```

P3 needs P1-A, P2-B, P2-C and P2-D merged. P2-A and P1-B may land during P3, because P3 uses a null memory and the DuckDB backend. Merge order: P0 → {P1-A, P2-C, P2-A} → {P2-B, P2-D} → P3 → {P4-A, P4-B} → {P5-A, P5-B} → P6 → P7; P1-B merges whenever it is green.

## 2. Lanes

| Lane | Pass file | Branch | Marker | Suggested Cursor model | Agent time | Human time | Slot |
|---|---|---|---|---|---|---|---|
| P0 | `P0_BOOTSTRAP.md` | `p0-bootstrap` | `p0` | Composer / Grok (mechanical) | 1.5 h | 0.5 h | Thu 08:00 |
| P1-A | `P1_DATA_ZETARIS.md` §A | `p1a-data` | `p1a` | Composer / Grok | 3 h | 0.5 h | Thu 11:00 |
| P1-B | `P1_DATA_ZETARIS.md` §B | `p1b-zetaris` | `p1b` | Claude | 3 h | **2 h attended** | Thu 18:00 |
| P2-A | `P2_ENGINES.md` §A | `p2a-hmem` | `p2a` | Claude | 2.5 h | 0.3 h | Thu 11:00 |
| P2-B | `P2_ENGINES.md` §B | `p2b-llm` | `p2b` | Claude | 2.5 h | 0.5 h (Nightshift) | Fri 08:00 |
| P2-C | `P2_ENGINES.md` §C | `p2c-policy` | `p2c` | Claude or Grok | 2.5 h | 0.3 h | Thu 11:00 |
| P2-D | `P2_ENGINES.md` §D | `p2d-guard` | `p2d` | Grok / Composer | 2.5 h | 0.3 h | Fri 08:00 |
| P3 | `P3_AGENT_LOOP.md` | `p3-loop` | `p3` | Claude (strongest available) | 8–10 h | 1.5 h | Fri 13:00 to Sat 12:00 |
| P4-A | `P4_MEMORY_ACTIONS_API.md` §A | `p4a-memory` | `p4a` | Claude | 3 h | 0.5 h | Sat 12:00 |
| P4-B | `P4_MEMORY_ACTIONS_API.md` §B | `p4b-api` | `p4b` | Grok / Composer | 4 h | 1 h | Sat 12:00 |
| P5-A | `P5_UI_EVAL.md` §A | `p5a-ui` | `p5a` | Composer / Grok | 4 h | 1 h | Sun 08:00 |
| P5-B | `P5_UI_EVAL.md` §B | `p5b-eval` | `p5b` | Claude | 3 h | 1 h (live run) | Sun 08:00 |
| P6 | `P6_HARDENING_DOCS.md` | `p6-hardening` | `p6` | Claude + Composer | 4 h | 2 h | Mon 08:00 |
| P7 | `P7_SUBMISSION.md` | `p7-submission` | `p7` | – (human-led) | 1 h | 6 h | Mon PM to Tue |

Record the model actually used per lane in `docs/cursor-usage/<LABEL>.md`. Mixing Composer and Grok (Cursor with Space XAI) with Claude is deliberate, and worth stating in the sponsor explanation.

## 3. File ownership (prevents merge conflicts between parallel lanes)

P0 creates **every shared file** and a stub for every module, so later lanes only *fill* files they own.

| Owner | Files and directories |
|---|---|
| **P0** (later lanes must not edit, except where marked ✎) | `pyproject.toml` (all markers declared), `requirements*.txt` (all deps pinned), `run.py` (dispatcher only), `app/cli/__init__.py`, `app/config.py` ✎P2-B (provider fields only), `app/errors.py`, `app/canon.py`, `app/tracing.py`, `app/schemas/*` ✎(additive fields only, with a note in the pass report), `app/api/main.py`, `scripts/tasks.py`, `scripts/scan_secrets.py`, `scripts/check_trace.py`, `scripts/check_hardcoding.py`, `.github/workflows/ci.yml` ✎P4-B, `.env.example` ✎P6, `.gitignore`, `.dockerignore`, `Makefile`, `docs/PRIOR_WORK.md` ✎(sha only), every `scripts/gates/p<ID>.py` stub (each lane fills its own) |
| P1-A | `data/**` (except `data/evals/injection_domain.jsonl`), `sources/**`, `app/data/{backend,registry,duckdb_backend,inline,dq,factory,status}.py` (P1-B ✎ adds the Zetaris branch to `factory.py` and `status.py`), `app/data/queries.yaml`, `zetaris/dq_rules.yaml`, `input_examples/**`, `app/cli/data.py`, `tests/unit/data/**`, `tests/contract/test_registry_*.py` |
| P1-B | `zetaris/{sql/**,sources.yaml,onboard.py,parity.py,README.md}`, `docs/passes/P1-B_parity.json`, `docs/img/zetaris_*`, `app/data/zetaris.py`, `app/cli/zetaris.py`, `tests/unit/zetaris/**`, `tests/live/test_zetaris_*.py`, `tests/fixtures/zetaris_*` |
| P2-A | `app/memory/hmem/**`, `vendor/meterless/{hmem_vectors.json,LICENSE,NOTICE.md}`, `scripts/dev/hmem_golden.py`, `tests/conformance/test_hmem_*.py`, `tests/unit/hmem/**`, `tests/fixtures/hmem_*` |
| P2-B | `app/llm/**`, `app/cli/llm.py`, `tests/unit/llm/**`, `tests/live/test_meterless_*.py`, `tests/fixtures/meterless_*`, `tests/fixtures/nvidia_*` |
| P2-C | `policy/**` (P5-B ✎ adds new files under `policy/calibration/`), `app/policy/**`, `tests/unit/policy/**` |
| P2-D | `app/guard/**`, `app/actions/{contracts,keys}.py`, `app/audit/chain.py`, `vendor/meterless/{scout_*,NOTICE-scout.md}`, `data/evals/injection_domain.jsonl`, `app/cli/guard.py`, `tests/unit/{guard,contracts,audit}/**`, `tests/conformance/test_scout_*.py` |
| P3 | `app/state.py`, `app/orchestrator.py`, `app/agents/**`, `app/confidence.py`, `app/grounding.py`, `app/facts.py`, `app/extract/**`, `app/actions/{executor,outbox}.py`, `app/store.py` (created as a JSON store; ownership passes to P4-B), `app/api/routes_run.py`, `app/cli/run_case.py`, `app/llm/prompts/*.md` ✎(prompt text only), `tests/unit/{agents,orchestrator,facts,extract,grounding}/**`, `tests/e2e/**`, P0-T6 clause (b) ✎ (delete only), `input_examples/expected.json` ✎(only if P1-A left it incomplete) |
| P4-A | `app/memory/{precedents,keeper,assessments}.py`, `app/api/routes_review.py` (includes `/memory/precedents`), `app/orchestrator.py` ✎ (memory wiring, 3 lines), `app/cli/review.py`, `tests/unit/memory/**`, `tests/e2e/test_session_*.py` |
| P4-B | `app/store.py`, `app/audit/replay.py`, `app/api/{routes_cases,routes_contracts,routes_meta}.py`, `app/cli/audit.py`, `Dockerfile`, `docker-compose.yml`, `scripts/clean_clone_check.py`, `docs/passes/clean-clone-*.md`, `tests/unit/{store,replay,api,docker}/**` |
| P5-A | `ui/**`, `docs/img/ui_*`, `tests/unit/ui/**` |
| P5-B | `eval/**`, `app/cli/eval.py`, `policy/calibration/<new>.json` + `ACTIVE`, `routes_meta.py` ✎ (`/eval/latest` only), `docs/EVALUATION.md` (generated), `tests/unit/eval/**`, `tests/evals/**` |
| P6 | `README.md`, `metadata.json`, `docs/{ARCHITECTURE,SPONSORS,DEMO_SCRIPT,trace_schema}.*`, `output_examples/**`, `logs/examples/**`, `scripts/check_metadata.py`, `app/cli/examples.py`, `.env.example` ✎ (comments only), `tests/unit/docs/**` |
| Everyone | Their own `docs/passes/<LABEL>_REPORT.md` and `docs/cursor-usage/<LABEL>.md` (never a shared file, so parallel lanes cannot conflict) |

## 4. Pass file template (every pass file has these sections)

1. **Goal**: what exists at the end, in one paragraph.
2. **Why it scores**: which rubric lines it serves.
3. **Read first**: exact spec sections.
4. **Depends on**: merged lanes and the interfaces it consumes.
5. **Deliverables**: files and responsibilities.
6. **Interfaces**: binding signatures.
7. **Acceptance tests**: ids, assertions, markers.
8. **Verification**: commands and gate script.
9. **Definition of done**: the checklist.
10. **Cut lines**: what to drop if over time.
11. **Cursor prompt**: copy-paste.
12. **Explain it**: five questions the human must be able to answer afterwards.

## 5. Generic Cursor prompt (the lane prompt in each file specialises this)

```
/start-pass <ID>
You are implementing lane <ID> of Arbiter.
Read, in order: AGENTS.md; docs/spec/00_MASTER_SPEC.md sections <…>; <other spec sections>; docs/spec/passes/<FILE> (lane <X> only).
1) Plan Mode: write .cursor/plans/<LABEL>.md listing every file you will create or edit (must be inside your lane's ownership in docs/spec/passes/README.md §3), every interface, and every acceptance test id. Stop and wait for my approval.
2) After approval: write the acceptance tests first (marker p<ID>), commit "test(p<ID>): acceptance tests", confirm they fail for the right reason.
3) Implement in small Conventional Commits until `python scripts/tasks.py verify-pass --pass <ID>` is green. Never weaken, skip or delete a test; if a test is wrong, stop and ask.
4) Write docs/passes/<LABEL>_REPORT.md (built / deviations with reasons / known gaps / commands run / Explain-it answers) and write docs/cursor-usage/<LABEL>.md.
5) Push branch <branch>, delete .cursor/ACTIVE_PASS, stop. Do not start another lane.
```
