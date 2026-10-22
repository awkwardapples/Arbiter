# Cursor usage — P4-A

- **Model:** Composer (Cursor agent)
- **Plan:** `.cursor/plans/P4-A.md` (approved with planner hook, `retrieval_quality` assertion, expanded orchestrator wiring)
- **Notable loop:** Planner `TypeError` from `isinstance(..., MemoryPort)` without `@runtime_checkable` — fixed via `hasattr` guard in `plan_queries_from_priors`.
- **Verify:** `python scripts/tasks.py verify-pass --pass 4a` green (includes demo-session gate).
