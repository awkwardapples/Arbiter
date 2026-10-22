# P5-A plan: Streamlit reviewer console (API-only)

**Phase:** plan (awaiting approval). **Marker:** `p5a`. **Branch:** `p5a-ui`. `.cursor/ACTIVE_PASS` = `5a plan`.

## Goal

Deliver a Streamlit **reviewer console** so a TPRM analyst can run assessments, browse the risk-prioritised queue, drill into a case to see **why** the policy decided (controls, evidence, contradictions, counterfactuals, precedents), follow **multi-agent collaboration** on a trace timeline (graph + table), submit human review / contract approval, and inspect memory and audit integrity — **without importing orchestration code** and **only** via `httpx` to the FastAPI backend (`ARBITER_API_URL`, default `http://localhost:8000`). Accessibility: text labels on every outcome/status (never colour-only), keyboard-friendly forms, glossary for domain terms.

## Depends on (merged / consumed)

- **P3:** `POST /run`, trace JSONL shape (`TraceEvent`), six input examples.
- **P4-A:** `POST /cases/{id}/review?dry_run=`, `GET /memory/precedents`.
- **P4-B:** `GET /health`, `GET /vendors`, `GET /cases`, `GET /cases/{id}`, `GET /cases/{id}/trace`, `POST /cases/{id}/replay`, `GET /audit/verify`, `POST /contracts/{id}/approve`.
- **P5-B (optional):** `GET /eval/latest` for the Evaluation page; if missing, show an honest “not published yet” panel (no filesystem reads).

## Files to create or edit (all in lane ownership)

| Path | Action |
|---|---|
| `ui/client.py` | **Create** — typed HTTP client for all UI endpoints |
| `ui/components.py` | **Replace stub** — shared renderers + timeline/graph builders |
| `ui/app.py` | **Replace stub** — `st.navigation`, global CSS, page wiring |
| `ui/timeline.py` | **Create** (optional split if `components.py` > ~400 lines) — pure functions: parse handoffs, build DOT, tabular rows |
| `tests/unit/ui/test_imports.py` | **Create** — P5-T10 |
| `tests/unit/ui/test_components.py` | **Create** — P5-T12, parts of timeline |
| `tests/unit/ui/test_timeline.py` | **Create** — P5-T13 |
| `tests/unit/ui/test_validation.py` | **Create** — P5-T14 |
| `tests/unit/ui/test_pages_smoke.py` | **Create** — P5-T11 (`AppTest`) |
| `tests/fixtures/ui/*.json` | **Create** — captured API payloads (scrubbed); include example-2 trace JSONL as JSON array |
| `scripts/gates/p5a.py` | **Fill** — assert `ui/client.py` exists + minimum screenshot set (see gate note below) |
| `docs/img/ui_*.png` | **Create with human** after pages work (not blocking first green verify-pass) |
| `docs/passes/P5-A_REPORT.md` | **Create** at end |
| `docs/cursor-usage/P5-A.md` | **Create** at end |

**Ownership exceptions:** none planned. Will **not** edit `app/api/routes_meta.py` (`/eval/latest` is P5-B ✎).

## Interfaces (signatures)

### `ui/client.py`

Environment: `ARBITER_API_URL` (default `http://localhost:8000`), timeout 30s per request.

```python
class ArbiterAPIError(Exception):
    message: str  # from ErrorResponse.error.message when present

class ArbiterClient:
    def __init__(self, base_url: str | None = None, *, client: httpx.Client | None = None) -> None: ...

    def health(self) -> HealthResponse: ...
    def list_vendors(self) -> list[dict[str, object]]: ...
    def run(self, case: CaseInput, *, options: RunRequestOptions | None = None) -> RunResponse: ...
    def list_cases(self) -> list[QueueItem]: ...  # mirrors routes_cases.QueueItem JSON
    def get_case(self, case_id: str) -> CaseDetail: ...
    def get_trace(self, case_id: str) -> list[dict[str, Any]]: ...
    def replay(self, case_id: str) -> ReplayResult: ...
    def submit_review(self, case_id: str, body: ReviewRequest, *, dry_run: bool = False) -> ReviewResponse | EligibilityOut: ...
    def list_precedents(self) -> list[dict[str, Any]]: ...
    def audit_verify(self) -> AuditVerifyResponse: ...
    def approve_contract(self, contract_id: str, body: ApprovalRequest) -> dict[str, Any]: ...
    def eval_latest(self) -> dict[str, Any]: ...  # raises ArbiterAPIError on 404
```

Parsing uses **`app.schemas` only** (`HealthResponse`, `CaseInput`, `RunResponse`, `ReviewRequest`, `ApprovalRequest`, etc.). Non-2xx: map JSON `ErrorResponse` to `ArbiterAPIError`; network/timeout to a short user-facing string.

**Test seam:** `tests/unit/ui/conftest.py` provides `FakeArbiterClient` implementing the same methods from `tests/fixtures/ui/*.json`, injected via `st.session_state["api_client"]` (set in `AppTest` before `run()`).

### `ui/components.py`

```python
OUTCOME_LABELS: dict[Outcome, str]  # icon + human text, e.g. "⬆ ESCALATE"

def decision_badge(outcome: Outcome | str) -> None: ...  # st markdown with visible text
def tier_chip(tier: Tier | str) -> None: ...
def confidence_gauge(value: float, gate: float, abstained: bool) -> None: ...
def evidence_chip(provenance: Provenance, *, fact: Fact | None = None) -> None: ...
def control_table(controls: list[ControlResult], facts: list[Fact]) -> None: ...
def status_label(status: str) -> str: ...  # P5-T12: always non-empty text + optional icon
def glossary() -> None: ...  # expander: SoR, KEV, USL, DQ, precedent, counterfactual
def timeline(events: list[dict[str, Any]], *, filters: TimelineFilters | None = None) -> None: ...
```

`timeline()` composes:

- **Graph:** `st.graphviz_chart(build_timeline_dot(events))`
- **Table:** columns time, agent, action, target, status (text via `status_label`), summary, provider/model, query_id/rows, latency
- **Filters:** agent multiselect, status multiselect; Zetaris rows (`backend`/`source_system`) and Meterless LLM rows (`provider`) get distinct icons in the table (text label still present)

### `ui/timeline.py` (pure, no Streamlit)

```python
@dataclass
class TimelineEdge:
    src: str
    dst: str
    dashed: bool
    label: str

def agent_nodes(events: list[dict[str, Any]]) -> set[str]: ...
def extract_edges(events: list[dict[str, Any]]) -> list[TimelineEdge]: ...
def build_timeline_dot(events: list[dict[str, Any]]) -> str: ...
def timeline_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]: ...
```

**Edge rules (aligned with orchestrator traces):**

- Primary handoffs: consecutive distinct `agent_name` on successful agent events (Planner → Evidence → Evaluator → …).
- **Loop edges:** any Orchestrator `transition` with `output_summary` matching `EVALUATE→PLAN` and `status == needs_revision` → dashed edge **EvaluatorAgent → PlannerAgent** (or phase nodes `EVALUATE` → `PLAN` if we render phase labels on loop rows); label = gap control ids from summary `(gaps: …)`.
- **CHALLENGE → PLAN:** dashed when present in trace.
- Node set for P5-T13: expect agents **PlannerAgent, EvidenceAgent, EvaluatorAgent, ChallengerAgent, ReporterAgent, Orchestrator** (exact set asserted against fixture, not hardcoded vendor ids).

### `ui/app.py`

```python
def main() -> None: ...  # streamlit entry: set_page_config, inject CSS (max-width ~1100px), st.navigation(pages)

def page_new_assessment() -> None: ...
def page_queue() -> None: ...
def page_case() -> None: ...
def page_review() -> None: ...
def page_memory() -> None: ...
def page_audit() -> None: ...
def page_evaluation() -> None: ...
```

Sidebar: `/health` → mode strings (data backend, LLM provider, model ids when present), link to glossary.

**Submission validation (New assessment):**

```python
def parse_case_input(raw: dict[str, Any] | str) -> tuple[CaseInput | None, list[str]]: ...
```

Uses `CaseInput.model_validate`; errors → friendly field messages; **no** `client.run` when invalid (P5-T14).

---

## Page wireframes (ASCII)

### New assessment

```
┌─ New assessment ─────────────────────────────────────┐
│ Run mode: [health.data] [health.provider]            │
│ ○ Pick vendor [dropdown from GET /vendors]           │
│ ○ Paste / upload JSON (VendorSubmission wrapper)     │
│ [ Validate ]  [ Run assessment ]                     │
│ errors: ...                                          │
└──────────────────────────────────────────────────────┘
```

Run → spinner polling is **not** needed (sync POST /run); show `RunResponse.status` + agent names; `st.session_state["last_case_id"]`; navigate to Case.

### Queue

```
┌─ Queue ──────────────────────────────────────────────┐
│ Filter outcome [ ]  tier [ ]                         │
│ ┌ card ───────────────────────────────────────────┐  │
│ │ ESCALATE · Acme Ltd · T1 · risk 72 · 2h ago     │  │
│ │ status: pending_approval                         │  │
│ └ [Open case] ────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

Sort: API order (residual risk desc).

### Case (`?case_id=`)

```
┌─ Case VND-… ─────────────────────────────────────────┐
│ [ESCALATE] summary sentence · confidence gauge      │
│ ─ Why ─ control_table                               │
│ ─ Contradictions ─ two columns                      │
│ ─ What would change ─ counterfactual checklist      │
│ ─ Precedents ─ considered / applied                 │
│ ─ Actions ─ contract state · Approve/Reject form    │
│ ─ Agent timeline ─ graph + filtered table           │
│ ─ Report ─ markdown                                   │
│ ▼ Raw JSON (record, report)                         │
└──────────────────────────────────────────────────────┘
```

Evidence chips: `system · query_id · record_key`; expander shows fact value / quote (no prompt leakage).

### Review

```
┌─ Review case [select] ───────────────────────────────┐
│ decision [ ]  rationale (30+ chars, live count)      │
│ mitigations / conditions                             │
│ [ ] create precedent  → eligibility hint (dry_run)   │
│ [ Submit review ]                                    │
└──────────────────────────────────────────────────────┘
```

### Memory

```
┌─ Memory ─────────────────────────────────────────────┐
│ Precedents table (GET /memory/precedents)            │
│ Ledger expander per row                              │
│ Case picker → GET /cases/{id} → precedents_considered│
│ (full hmem-retrieval JSONL not on API — see risks)   │
└──────────────────────────────────────────────────────┘
```

### Audit

```
┌─ Audit ──────────────────────────────────────────────┐
│ [ Verify chain ]  ok / first_bad_seq                 │
│ Per case: [ Replay ] → match + diff                  │
└──────────────────────────────────────────────────────┘
```

### Evaluation

```
┌─ Evaluation ─────────────────────────────────────────┐
│ GET /eval/latest → render markdown (or placeholder)  │
└──────────────────────────────────────────────────────┘
```

---

## Acceptance tests (marker `@pytest.mark.p5a`)

| Id | How we test |
|---|---|
| **P5-T10** | AST/walk over `ui/**/*.py`: any import from `app` must be under `app.schemas` only (allow `from app.schemas...` and `import app.schemas`). Fail on `app.orchestrator`, `app.data`, etc. |
| **P5-T11** | `streamlit.testing.v1.AppTest.from_file("ui/app.py")` with `FakeArbiterClient` fixtures for **each** nav page; `run()` without exception; assert presence of outcome text (e.g. `ESCALATE`), controls table header, timeline section title. One parametrized test per page. |
| **P5-T12** | Unit test: for every `Outcome` and every trace `status` literal in `TraceEvent`, `status_label` / `decision_badge` output contains a non-empty alphabetic label (not only emoji/colour). |
| **P5-T13** | Generate fixture once: offline `run(example_2)` → save trace events to `tests/fixtures/ui/example_2_trace.json` (committed, no secrets). `build_timeline_dot` contains dashed edge attribute (`style=dashed`) for EVALUATE→PLAN loop; `agent_nodes` equals expected frozenset (derived from first capture, stable across seeds). |
| **P5-T14** | Unit test `parse_case_input`: invalid JSON / both vendor_id and submission / missing required fields → errors non-empty, and a mock client’s `run` assert not called; valid vendor_id payload → ok. |

**Fixture capture command (build step, not in CI secrets):**

```bash
SAMPLE_MODE=true LLM_PROVIDER=offline ARBITER_MEMORY=off python -c "
from pathlib import Path
import json
from app.orchestrator import RunOptions, run
from tests.e2e.support import load_example
r = run(load_example('example_2.json'), options=RunOptions())
Path('tests/fixtures/ui').mkdir(parents=True, exist_ok=True)
# ... also snapshot minimal CaseDetail-shaped dicts from a seeded store or synthetic builder
"
```

For AppTest, prefer **hand-built** minimal JSON matching `CaseDetail` / `HealthResponse` schemas rather than importing `app.orchestrator` inside `ui/` tests (orchestrator import stays in the one-off fixture writer script under `tests/`).

## Gate `scripts/gates/p5a.py`

After implementation:

- Require files: `ui/client.py`, `ui/app.py`, `ui/components.py`.
- Optionally require ≥1 `docs/img/ui_*.png` only when an env var `P5A_REQUIRE_SCREENSHOTS=1` (default off) so CI stays green before the human screenshot pass.

## Verification

```bash
python scripts/tasks.py verify-pass --pass 5a
# Manual smoke (human):
python run.py serve &
python run.py ui   # http://localhost:8501
```

## Risks and questions for Josh

1. **H-MEM retrieval JSONL on Memory page:** Spec mentions `logs/hmem-retrieval-<run_id>.jsonl`, but there is **no API route** today. **Proposal:** show `GET /memory/precedents` + per-case `precedents_considered` from `GET /cases/{id}`; document gap in P5-A report. **Alternative:** block and add a read-only API in P4-A/P4-B (out of lane). **Recommendation:** API-only approximation unless you want a small additive route elsewhere.

2. **`GET /eval/latest`:** Likely absent until P5-B merges. **Proposal:** Evaluation page handles 404 with clear copy; no reading `eval/results/` from the UI process. OK?

3. **Fixture freshness:** Example-2 trace fixture will be generated from current orchestrator (offline). If P3 trace shape changes, P5-T13 may need fixture refresh — acceptable?

4. **Screenshots:** Spec asks for `docs/img/ui_*.png` with you in the loop after pages work. Confirm we defer gate enforcement until that session.

5. **Branch / merge base:** Confirm this worktree should track `p5a-ui` from current `main` (any lanes not merged yet?).

## Cut lines (if time runs short — spec order)

1. Memory + Audit pages (endpoints unchanged).
2. Evaluation page.
3. Graph view (keep timeline table only).

## Definition of done (from pass file)

- [ ] All pages work against live API (`serve` + `ui`).
- [ ] Screenshots saved under `docs/img/ui_*.png` (with human).
- [ ] `docs/passes/P5-A_REPORT.md` lists screenshots + UX gaps + Explain-it answers.

---

**Waiting for your approval** to set `.cursor/ACTIVE_PASS` to `5a build` and begin tests-first implementation.
