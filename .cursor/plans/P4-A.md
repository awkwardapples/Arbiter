# P4-A plan: H-MEM precedents, MemoryKeeper, human review, demo session

## Goal

Wire governed precedent memory on the existing Meterless H-MEM port so human reviews can create durable, policy-eligible precedents, later cases retrieve them via canonical keys (policy applies the six exception criteria), feedback updates H-MEM trust, and prior vendor assessments shape the next plan. Expose `POST /cases/{case_id}/review`, `GET /memory/precedents`, and CLI `review` / `demo-session` so `python run.py demo-session --reset --yes` proves the six-step session story from `03_EVALUATION.md` §3.4 offline.

## Depends on (already merged / consumed)

- P2-A: `app/memory/hmem` (`HMEM.add`, `query`, `feedback`, ledger mirror).
- P2-C: `app/policy/engine.py` `_apply_precedents` / `_failed_criteria` (policy-only exception application).
- P2-D: `app/audit/chain.py` (`AuditChain.append` for `precedent_created`, `feedback_recorded`, `review_recorded`).
- P3: orchestrator `MEMORY_CHECK` → `DECIDE_2`, `MemoryPort`, JSON `Store` (`put_review`, `put_human_decision`, `save`).
- P1-A: sample data for `VND-0011` / `VND-0012` (scenario S12).

## Files to create or edit

| Path | Owner | Action |
|---|---|---|
| `app/memory/precedents.py` | P4-A | Implement domain adapter (see interfaces). |
| `app/memory/assessments.py` | P4-A | Working-layer assessment store/retrieve. |
| `app/memory/keeper.py` | P4-A | `HMemMemory` implementing `MemoryPort` + alignment helper. |
| `app/api/routes_review.py` | P4-A | Review + precedents list routes. |
| `app/cli/review.py` | P4-A | `review` and `demo-session` commands. |
| `app/orchestrator.py` | P4-A ✎ | Default memory from `ARBITER_MEMORY`; DECIDE₂ confidence uses real `precedent_alignment` (spec §02 §decide loop). |
| `tests/unit/memory/**` | P4-A | Acceptance tests P4-T1, T2, T4, T5, T6, T9. |
| `tests/e2e/test_session_*.py` | P4-A | P4-T3, T7, T8 (and session steps embedded in T7). |
| `scripts/gates/p4a.py` | P4-A (lane gate stub) | Run `demo-session --reset --yes` or delegate to pytest marker. |

### Ownership exceptions (need your approval before build)

| Path | Why |
|---|---|
| `app/agents/planner.py` | **P4-T6** requires iteration-1 `Q_VENDOR_CONTRACT` when a prior assessment of the same vendor escalated on C09. Spec assigns this to the Planner reading `prior_assessments`; file is P3-owned and has no hook today. **Proposal:** add ~15 lines in `required_queries()` (iteration 1 only): if any prior assessment has outcome `ESCALATE` and failing control `C09`, append `(Q_VENDOR_CONTRACT, "prior assessment: verify contract after C09 escalation")`. **Alternative (cut line A8):** store assessments only, skip T6. |
| `app/schemas/api.py` | Additive response models (`ReviewResponse`, `PrecedentListItem`, `EligibilityOut`) — allowed as ✎ additive with note in report. |

No other P3/P4-B files touched.

## Interfaces (signatures)

### `app/memory/precedents.py`

```python
def precedent_key(control_id: str, mitigation_fact: str, tier: Tier, category: str) -> str: ...

def check_eligibility(review: ReviewRequest, bundle: CaseBundle, policy: Policy) -> tuple[bool, list[str]: ...

def record_precedent(
    review: ReviewRequest,
    bundle: CaseBundle,
    *,
    hmem: HMEM,
    audit: AuditChain,
    precedents_path: Path,
    run_id: str,
) -> PrecedentRef: ...  # raises PolicyIneligible(reasons=...) when ineligible

def find_precedents(
    profile: TierProfile,
    failing_controls: list[str],
    *,
    hmem: HMEM,
    as_of: date,
    run_id: str,
    log_dir: Path = Path("logs"),
) -> list[PrecedentCandidate]: ...

def feedback(precedent_id: str, kind: Literal["helpful", "not_helpful", "wrong"], *, hmem: HMEM, audit: AuditChain) -> float: ...
```

- Eligibility mirrors policy §6 + deliverable table (exception-eligible failing controls only, mitigation TRUE, role rank, decision AWC/APPROVE).
- `record_precedent`: H-MEM long-term memory (`type=factual`, `confidence=0.7`, tags/entities/source/agent fields per spec); sidecar payload in `var/precedents.json`; stable public id `P-0001`, …; audit `precedent_created`.
- `find_precedents`: per failing control, `hmem.query(precedent_key(...), top_n=5, threshold=0.0)`; filter `precedent` tag; join payload; write `logs/hmem-retrieval-<run_id>.jsonl`.
- `feedback`: delegate to `hmem.feedback`; audit `feedback_recorded`.

### `app/memory/assessments.py`

```python
def record_assessment(record: DecisionRecord, *, hmem: HMEM) -> None: ...
def prior_assessments(vendor_ref: str, *, hmem: HMEM) -> list[dict[str, Any]]: ...
```

Working-layer factual memories keyed by vendor; content/tags sufficient for planner hook (vendor_ref, outcome, failing_controls, unknown_controls, contradictions summary).

### `app/memory/keeper.py`

```python
class HMemMemory:
    name = "hmem"

    def __init__(self, *, var_dir: Path, clock: Callable[[], datetime], tracer: Tracer | None = None) -> None: ...

    def find_precedents(self, profile: TierProfile, failing_controls: list[str]) -> list[PrecedentCandidate]: ...
    def prior_assessments(self, vendor_ref: str) -> list[dict[str, Any]]: ...
    def record_assessment(self, record: DecisionRecord) -> None: ...

    def precedent_alignment(self, precedents: list[PrecedentCandidate], decision: DecisionRecord) -> float: ...
    def trace_precedent_outcomes(self, decision: DecisionRecord) -> None: ...  # applied / rejected + failed_criteria

def build_memory(settings: Settings, *, var_dir: Path, clock: Callable[[], datetime], tracer: Tracer | None = None) -> MemoryPort: ...
```

- Single shared `HMEM(persist_dir=var_dir / "hmem", ledger_mirror=logs/hmem-ledger.jsonl, clock=ms from injected datetime).
- `build_memory`: returns `NullMemory()` when `settings.ARBITER_MEMORY == "off"`, else `HMemMemory`.

### `app/orchestrator.py` (✎)

```python
# In run(), before AgentContext:
memory = deps.memory if deps.memory is not None else build_memory(settings, var_dir=deps.var_dir, clock=clock, tracer=tracer)

# In DECIDE_2 path (_decide): when precedents passed, compute alignment via ctx.memory if HMemMemory else 1.0
```

Keep diff minimal; no change to state machine topology.

### `app/api/routes_review.py`

```python
@router.post("/cases/{case_id}/review")
def submit_review(case_id: str, body: ReviewRequest, dry_run: bool = False) -> ReviewResponse: ...

@router.get("/memory/precedents")
def list_precedents() -> list[PrecedentListItem]: ...
```

- Validate rationale ≥ 30 (Pydantic on `ReviewRequest`; map validation error to 400).
- `dry_run=true`: run `check_eligibility` only.
- Else: `store.put_review`, human `DecisionRecord` linked to machine (`first_decision` or prior machine record), issue+execute review contract with reviewer approval, optional `record_precedent`, feedback on `precedents_considered`, audit `review_recorded`.

### `app/cli/review.py`

```python
def cmd_review(args: argparse.Namespace) -> int: ...  # POST review from JSON file
def cmd_demo_session(args: argparse.Namespace) -> int: ...  # 03 §3.4 steps 1–6; --reset wipes var/hmem, var/precedents.json, case store
```

## Acceptance tests (`@pytest.mark.p4a`)

| Id | Approach |
|---|---|
| **P4-T1** | Unit: eligible synthetic review + S12-like bundle → assert H-MEM record fields, `var/precedents.json` entry, ledger line, audit `precedent_created`. |
| **P4-T2** | Unit/parametrize: wrong role, non-exception failing control, mitigation FALSE → `PolicyIneligible` / HTTP 422 with stable reason codes; no H-MEM file growth. |
| **P4-T3** | E2E offline: run VND-0011 → review AWC + `bridge_letter` + `create_precedent` → run VND-0012 → outcome AWC, `exceptions_applied` contains `P-0001`, contract pending `tprm_lead`. |
| **P4-T4** | Unit: assert `FEEDBACK_DELTAS`; after `wrong`, confidence 0.50; full run VND-0012 retrieves candidate but engine rejects → ESCALATE, trace includes `precedent_rejected`, `failed_criteria` includes low-confidence signal (see risk: engine uses `retrieval_quality`). |
| **P4-T5** | Unit: `find_precedents` writes JSONL with `retrievalReason`, per-memory scores, strategy label. |
| **P4-T6** | E2E/unit: vendor with prior ESCALATE on C09 → second run iteration-1 plan includes `Q_VENDOR_CONTRACT` and fewer eval loops; trace `plan_reason` cites prior assessment. **Blocked on planner ✎ approval.** |
| **P4-T7** | E2E: invoke `demo-session --reset --yes` (subprocess or direct handler) asserts all six §3.4 expectations. |
| **P4-T8** | API TestClient: rationale too short → 400; successful review → human decision linked in store, contract executed with approval recorded. |
| **P4-T9** | Unit: canonical key query relevance ≥ 0.35 for P-0001 on VND-0012 profile; mismatched control/category candidate below gate or absent; policy rejects non-matching. |

## Verification

```bash
python run.py demo-session --reset --yes
python scripts/tasks.py verify-pass --pass 4a
```

Fill `scripts/gates/p4a.py` to run the demo-session command (or fail if step table mismatch).

## Risks and questions

1. **Planner ownership (P4-T6)** — Approve minimal `planner.py` change above, or invoke cut line A8 (assessments stored only, drop T6)?
2. **`failed_criteria` naming (P4-T4)** — Policy engine today emits `retrieval_quality` for both low relevance and low H-MEM confidence (`engine.py`). Test doc says `hmem_confidence`. Prefer asserting `retrieval_quality` unless you want a P2-C engine split.
3. **Orchestrator scope** — Spec mentions “3-line” memory default; DECIDE₂ `precedent_alignment` likely needs a few extra lines in `_decide` / DECIDE_2 handler. OK to expand slightly while staying in orchestrator ✎?
4. **Human decision linkage** — Confirm: human record should copy machine `policy_inputs` but replace `outcome` / `outcome_reasons` with review decision and `HUMAN_REVIEW`, preserving `run_id` link via shared `case_id` + pointer field in review payload?
5. **Parallel P4-B** — We only use the P3 JSON `Store` interface; no SQLite assumptions.

## Build order (after approval)

1. Set `.cursor/ACTIVE_PASS` → `4a build`.
2. Commit failing tests (`test(p4a): acceptance tests`).
3. Implement precedents → assessments → keeper → orchestrator wiring → API → CLI → gate script.
4. Green `verify-pass --pass 4a`; report + cursor-usage; push `p4a-memory`; delete `ACTIVE_PASS`.

---

**Waiting for your approval** before writing code.
