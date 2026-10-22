# P5-A report: Streamlit reviewer console

## Built

- **`ui/client.py`** — `httpx` client for `/health`, `/vendors`, `/run`, `/cases`, trace, replay, review, precedents, audit verify, contract approve, `/eval/latest` (404 → `ArbiterAPIError`).
- **`ui/validation.py`** — client-side `CaseInput` validation; invalid intake never reaches `run()`.
- **`ui/components.py`** — accessible badges (`APPROVE`, `ESCALATE`, …), tier chip, confidence gauge, evidence chips, controls table, glossary, timeline (Graphviz + table).
- **`ui/timeline.py`** — dashed **EvaluatorAgent → PlannerAgent** edge from example-2 `EVALUATE→PLAN` / `needs_revision` transitions.
- **`ui/screens.py`** + **`ui/pages/*.py`** — seven pages wired from **`ui/app.py`** via `st.navigation` (file pages for testability).
- **`tests/unit/ui/`** — P5-T10–T14; fixtures under `tests/fixtures/ui/` (including real example-2 trace JSON).
- **`scripts/gates/p5a.py`** — module presence gate; screenshots gated on `P5A_REQUIRE_SCREENSHOTS=1`.

## Deviations

- **Page layout:** callable pages moved to `ui/pages/*.py` + `ui/screens.py` so `AppTest.switch_page()` works (Streamlit testing API requires file pages). Behaviour matches the pass spec.
- **Memory retrieval trace:** no `hmem-retrieval-*.jsonl` API — Memory page uses `GET /memory/precedents` and `precedents_considered` on a selected case only (per your approval).

## Known gaps / next with human

- **`docs/img/ui_*.png`** — deferred until live `python run.py serve` + `python run.py ui` walkthrough with you.
- **`GET /eval/latest`** — Evaluation page shows *"Evaluation results are not published yet."* when P5-B has not added the route (tested in P5-T14 smoke).

## Commands

```bash
DOCKER=0 python scripts/tasks.py verify-pass --pass 5a
python run.py serve   # terminal 1
python run.py ui      # http://localhost:8501
```

## Explain-it (draft)

1. **Why escalated?** **Case** page: controls table + contradictions; evidence chips show `system · query_id · record_key` back to Zetaris/DuckDB provenance.
2. **Non-linear pipeline?** **Agent timeline** graph/table: dashed **EVALUATE→PLAN** loop edges and multiple agent nodes (example 2 trace).
3. **Reviewer-only actions?** **Review** (override + precedent) and contract **Approve/Reject** on **Case** — human rationale ≥ 30 chars; machines cannot self-approve contracts.
4. **Accessibility?** Every outcome/status uses visible text labels, not colour alone (P5-T12).
5. **Why no `app.orchestrator` in UI?** API boundary only; P5-T10 AST import guard enforces `app.schemas` imports.

## Screenshot list (pending)

- [ ] `docs/img/ui_new_assessment.png`
- [ ] `docs/img/ui_queue.png`
- [ ] `docs/img/ui_case.png`
- [ ] `docs/img/ui_review.png`
- [ ] `docs/img/ui_memory.png`
- [ ] `docs/img/ui_audit.png`
- [ ] `docs/img/ui_evaluation.png`
