# P4-A report: governed H-MEM precedents and human review

## Built

- `app/memory/precedents.py` — canonical keys, eligibility, record/find/feedback, retrieval JSONL, `var/precedents.json` sidecar.
- `app/memory/assessments.py` — working-layer prior assessments; `plan_queries_from_priors()` for the Planner hook.
- `app/memory/keeper.py` — `HMemMemory` / `build_memory()` implementing `MemoryPort`.
- `app/api/routes_review.py` — `POST /cases/{id}/review`, `GET /memory/precedents`.
- `app/cli/review.py` — `review`, `demo-session --reset --yes`.
- Orchestrator ✎ — default memory from `ARBITER_MEMORY`, run context, DECIDE₂ `precedent_alignment`, MemoryKeeper trace hooks.
- Tests: `tests/unit/memory/*`, `tests/e2e/test_session_memory.py`; gate `scripts/gates/p4a.py`.

## Cross-lane touches (with approval)

| File | Change |
|---|---|
| `app/agents/planner.py` | `required_queries(state, memory)` + one call to `plan_queries_from_priors` (P4-T6). |
| `app/facts.py` | `TierProfile.vendor_category` populated from procurement profile (canonical precedent key). |
| `app/schemas/decision.py` | Additive `vendor_category` on `TierProfile`. |
| `app/errors.py` | `PolicyIneligible.reasons` list for HTTP 422 detail. |

## Orchestrator wiring note

Ownership table described ~3 lines; actual diff also wires DECIDE₂ `precedent_alignment` and `HMemMemory.set_run_context` (memory-relevant paths only, no state-machine refactor).

## Session table (`demo-session --reset --yes`)

| Step | Action | Result | OK |
|---|---|---|---|
| 1 | run VND-0011 | ESCALATE | yes |
| 2 | review + precedent | P-0001 | yes |
| 3 | run VND-0012 | APPROVE_WITH_CONDITIONS ['P-0001'] | yes |
| 4 | reset + VND-0012 | ESCALATE | yes |
| 5 | analyst precedent blocked | ESCALATE | yes |
| 6 | wrong feedback + VND-0012 | ESCALATE | yes |

## Ledger excerpt (P-0001)

After steps 2 and 6 of the session test, H-MEM ledger for `P-0001` includes:

- `create` — long-term precedent at confidence **0.70**
- `read` — retrieval on VND-0012 run (canonical key query)
- `feedback` / `helpful` — optional agree path in review flow
- `feedback` / `wrong` — delta **−0.20** → confidence **0.50** (step 6)

## Test rename (P4-T4)

Acceptance test docstring/id documents **`retrieval_quality`** as the engine’s failed criterion after `wrong` feedback (not a separate `hmem_confidence` code in `engine.py`). P2-C remains authoritative.

## Known gaps

- Engine bundles sub-threshold H-MEM confidence and relevance under `retrieval_quality`; finer-grained `hmem_confidence` would be a P2-C change if ever required.

## Commands

```bash
python run.py demo-session --reset --yes
python scripts/tasks.py verify-pass --pass 4a
```

## Explain-it (short)

1. **Three sessions:** VND-0011 escalates → lead review creates P-0001 → VND-0012 AWC via policy exception; reset proves no memory; analyst role blocked; `wrong` retires trust.
2. **Six criteria:** policy §6; enforced in `engine.py` (apply) and `precedents.check_eligibility` (create).
3. **`wrong`:** −0.20 H-MEM confidence; precedent may still retrieve but engine rejects via `retrieval_quality`.
4. **Governed:** retrieval proposes; policy permits; human approves; audit records each step.
5. **Split store:** H-MEM holds content/tags/confidence/ledger; `var/precedents.json` holds structured precedent metadata keyed by `P-…`.
