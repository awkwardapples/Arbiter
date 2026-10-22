# P4: Governed memory and human review (A); case store, approvals, replay and API (B)

Both lanes start after P3 is merged and run in parallel. **P4-A** owns review, precedent logic and the memory endpoints. **P4-B** owns persistence, approvals, replay, the read API **and the Docker image, CI Docker job and clean-clone check** (moved here from P6 so the "day four" check can run on Sunday). They meet only at `app/store.py`, whose full interface P3 already created (P4-A uses it; P4-B swaps its implementation without changing it).

---

# Lane P4-A: H-MEM precedents, MemoryKeeper, human review, the three-session story

## A1. Goal

Human reviews become **governed precedents** in Meterless H-MEM. A later similar case retrieves them, and the policy's `precedent_exception` clause, not the model, decides whether they change the outcome. Feedback updates trust through the H-MEM ledger. Prior assessments of the same vendor shape the next plan. `python run.py demo-session` runs the session test from 03 §3.4.

## A2. Why it scores

This is Track 3's **"memory"** and the **Demo** centrepiece: learned, retrieved, behaved differently. It is also **Innovation** (governed memory), and **Sponsor Tech** (a second load-bearing Meterless engine).

## A3. Read first

- Master spec §§6.3, 8.5
- `02_POLICY.md` §6
- `03_EVALUATION.md` §3.4
- P2-A's `app/memory/hmem` public API

## A4. Deliverables

| File | Responsibility |
|---|---|
| `app/memory/precedents.py` | **`record_precedent(review, case_bundle) -> PrecedentRef`.** Checks eligibility against the policy clause:<br>- the only failing required controls carry `precedent_exception.allowed`;<br>- the mitigation fact is TRUE;<br>- `reviewer.role` ≥ `approver_role`;<br>- the review decision is APPROVE_WITH_CONDITIONS or APPROVE.<br>If eligible, it writes an H-MEM memory with `type="factual"`, `layer="long_term"`, `confidence=0.7` (so one `wrong`, −0.20, retires it below the 0.70 gate). **Content starts with the canonical key** `precedent control c05 mitigation bridge letter tier t2 category <category>` (all lowercase, built by one function `precedent_key(control, mitigation, tier, category)`), followed by a one-sentence human summary. Tags are plain tokens: `precedent`, `c05`, `bridge_letter`, `approve_with_conditions`, `t2`. Entities are category, tier and controls; `source = "human_review:<review_id>"`; provenance carries the review; `agentId = "MemoryKeeper"`, `runId`, `taskId = case_id`. The structured payload goes to `var/precedents.json` keyed by memory id. It appends audit `precedent_created`. If ineligible it raises `PolicyIneligible` (HTTP 422) with the reasons.<br>**`find_precedents(profile, failing_controls, *, as_of) -> list[PrecedentCandidate]`.** For each failing exception-eligible control it runs an H-MEM `query` with **exactly** `precedent_key(...)` for this case (topN 5, **threshold 0.0**: H-MEM's threshold applies to the confidence-weighted score, so filtering there would hide the reason for a rejection), keeps results tagged `precedent`, and joins them with the payloads. It returns `PrecedentCandidate`s with `hmem_confidence` and `relevance` (H-MEM's score); **the policy engine** applies relevance ≥ 0.35, confidence ≥ 0.70 and the other criteria, so every rejection is recorded with `failed_criteria`. (Independent check of the reference scorer: a free-text query scores about 0.17–0.19 against a prose summary, below any useful gate; the identical key scores about 0.52 at confidence 0.7.) It writes `logs/hmem-retrieval-<run_id>.jsonl` (`retrievalReason`, scores, strategy).<br>**`feedback(precedent_id, kind)`** calls H-MEM `feedback` (helpful +0.05; not_helpful −0.03; wrong −0.20 plus a review tag). Ledger and audit `feedback_recorded` |
| `app/memory/assessments.py` | `record_assessment(record)` stores a working-layer memory per completed run: vendor ref, outcome, failing and unknown controls, contradictions. `prior_assessments(vendor_ref)` retrieves them. **Stored only because the Planner reads them** ("stored ≠ loaded") |
| `app/memory/keeper.py` | `HMemMemory` implements P3's `MemoryPort` with one H-MEM instance (`persist_dir=var/hmem`, ledger mirror on, clock = the injected clock). Trace events as `MemoryKeeper`: `retrieve_precedents`, `precedent_applied` / `precedent_rejected` (with the criteria that failed, from the engine's record), `record_assessment`. Computes the `precedent_alignment` signal (1.0 agree or none relevant, 0.5 relevant but none found, 0.0 conflicting) |
| Orchestrator wiring | Default `deps.memory = HMemMemory()` unless `ARBITER_MEMORY=off`. **Coordinate with me**: this is a 3-line change in `app/orchestrator.py` (a P3 file), allowed in this lane only |
| `app/api/routes_review.py` | `POST /cases/{case_id}/review` takes `ReviewRequest {reviewer, role, decision, rationale (≥ 30 chars), mitigations[], conditions[], create_precedent: bool}`. It stores the review via `store`, creates a **human decision record** (`outcome = review.decision`, `outcome_reasons = ["HUMAN_REVIEW"]`, linked to the machine record), issues a contract for the human decision already carrying the reviewer's approval, executes it, applies feedback to the precedents considered (agree → helpful; contradict → wrong), and creates a precedent if requested and eligible. It returns `{review_id, human_decision, contract, precedent?: PrecedentRef, eligibility: {eligible, reasons[]}}`. Audit `review_recorded`. **Also owns `GET /memory/precedents`** (list with H-MEM id, confidence and ledger history). With `?dry_run=true` it validates and returns only `eligibility`, writing nothing (the console uses this for its hint) |
| `app/cli/review.py` | `review CASE --input FILE` and `demo-session [--live] [--reset] [--yes]`, which runs 03 §3.4 steps 1–6 (cases B and C of the video) and prints a table. With `--reset` it wipes `var/hmem`, `var/precedents.json` and the case store first (asks for confirmation unless `--yes`). It never runs case A, so case A's on-camera run starts with no prior assessment and shows its verify loop |

## A5. Acceptance tests (marker `p4a`)

| Id | Test |
|---|---|
| P4-T1 | `record_precedent` writes an H-MEM long-term record (tags, entities, source, agent fields), the payload, a ledger entry and an audit `precedent_created` |
| P4-T2 | Ineligible creation (wrong role; a non-exception control failing; mitigation FALSE) gives 422 with the specific reasons; nothing is written |
| P4-T3 | `find_precedents` returns VND-0011's precedent for VND-0012's profile. The engine applies it and gives APPROVE_WITH_CONDITIONS with `exceptions_applied=[P-…]` and a contract pending `tprm_lead` |
| P4-T4 | Feedback deltas are exact (+0.05, −0.03, −0.20). After a `wrong` (0.70 → 0.50), the next VND-0012 run still *retrieves* the precedent but the engine rejects it (`failed_criteria` contains `hmem_confidence`), giving ESCALATE with `precedent_rejected` traced |
| P4-T9 | Retrieval sanity: with the canonical key, VND-0012's query returns P-0001 with relevance ≥ 0.35; a precedent for a different control or category is returned below 0.35 or not at all, and is rejected |
| P4-T5 | The retrieval trace file has `retrievalReason`, per-memory scores and the strategy label |
| P4-T6 | **Memory shapes planning:** re-assessing a vendor previously escalated for C09 makes iteration 1 include `Q_VENDOR_CONTRACT`, so the trace shows one fewer evaluator loop than the first run (`plan_reason` cites the prior assessment) |
| P4-T7 | **Session test offline:** `demo-session --reset --yes` passes all six steps of 03 §3.4 |
| P4-T8 | Review endpoint: rationale < 30 chars gives 400; the human decision record links to the machine record; the review contract is executed immediately with the reviewer's approval recorded |

## A6. Verification

```
python run.py demo-session --reset --yes
python scripts/tasks.py verify-pass --pass 4a
```

## A7. Definition of done

- [ ] The session table is pasted into the report.
- [ ] The ledger excerpt for P-0001 shows `created`, `helpful` and `wrong`.

## A8. Cut line

P4-T6 (prior assessments shaping the plan) can drop to "stored and shown in the UI only" if time is short. Tell me.

## A9. Cursor prompt

```
/start-pass 4a
You are implementing lane P4-A of Arbiter: governed precedent memory on Meterless H-MEM, human review, and the three-session demo.
Read: AGENTS.md; docs/spec/00_MASTER_SPEC.md §§6.3, 8.5; docs/spec/02_POLICY.md §6; docs/spec/03_EVALUATION.md §3.4; docs/spec/passes/P4_MEMORY_ACTIONS_API.md lane A; the public API of app/memory/hmem and app/agents/memory_port.py.
Rule: memory proposes, the policy permits, a human approves. Never let a precedent change an outcome outside app/policy/engine.py.
Plan Mode: .cursor/plans/P4-A.md with files and tests P4-T1..P4-T9. Wait for approval.
Tests first (marker p4a) → commit → implement until `python scripts/tasks.py verify-pass --pass 4a` is green.
Finish with docs/passes/P4-A_REPORT.md (session table + ledger excerpt) + docs/cursor-usage/<LABEL>.md; push p4a-memory; delete .cursor/ACTIVE_PASS; stop.
```

## A10. Explain it

1. Tell the three-session story using the actual trace and ledger lines.
2. List the six criteria a precedent must meet. Who enforces them?
3. What does a `wrong` feedback do, numerically and behaviourally?
4. Why is memory "governed" rather than just retrieval-augmented?
5. What is stored in H-MEM versus in `var/precedents.json`, and why?

---

# Lane P4-B: Case store (SQLite), approvals, replay, audit verification, read API

## B1. Goal

Cases, decisions, reports, contracts and reviews persist in SQLite. Pending contracts can be approved or rejected by role. Any decision **replays identically**. The audit chain verifies over HTTP. The queue is sorted by residual risk.

## B2. Why it scores

- **Track 3 "reliable"** (replay).
- **Technical** (persistence, error shapes).
- **Product & UX** (the queue and approvals the console needs).
- **Responsible AI** (human approvals).

## B3. Read first

- Master spec §§8.7–8.9
- `02_POLICY.md` §3 (approvals)
- P3's `app/store.py` interface

## B4. Deliverables

| File | Responsibility |
|---|---|
| `app/store.py` | SQLite `var/arbiter.db` (WAL), with tables `cases(case_id PK, run_id, vendor_ref, legal_name, created_at, status, outcome, tier, residual_risk, decision_json, report_json, trace_path, mode_json)`, `contracts(contract_id PK, case_id, parent_id, state, json)`, `reviews(review_id PK, case_id, json)` and `human_decisions(id PK, case_id, json)`. Same public interface as P3's JSON store, plus `list(order="risk")`, `put_contract`, `contracts_for(case_id)`, `put_review`. A one-shot migration imports any `var/cases/*.json` |
| `app/api/routes_cases.py` | `GET /cases` (queue: `case_id`, vendor, outcome badge text, tier, residual risk, status, created; sorted by risk descending, then created ascending). `GET /cases/{id}` (record, report, contracts, reviews, trace path). `GET /cases/{id}/trace` (parsed events). `POST /cases/{id}/replay` |
| `app/api/routes_contracts.py` | `POST /contracts/{id}/approve` takes `ApprovalRequest {by, role, decision: approve\|reject, rationale ≥ 30}`. It calls `contracts.add_approval` to make a child contract, then the executor once all required roles are present. A wrong role gives 403 with the required roles; an expired contract gives 409; reject sets the state to `rejected`. Audit events throughout |
| `app/api/routes_meta.py` | Extends `/health`: data backend status, provider status (`app.llm.status`), H-MEM record count (via `app.memory.keeper.count()` if present), audit chain length. `GET /vendors` (via the registry's `Q_VENDOR_LIST`, for the console picker). `GET /audit/verify` |
| `app/audit/replay.py` | `replay(case_id) -> {match, diff[], checks: {policy_hash, record_hash, contract_signatures}}` per master spec §8.8: load the stored record; load `policy/arbiter_policy.v<major>.yaml` and check `policy_sha256`; load `policy/calibration/<calibration_version>.json`; run `decide(record.policy_inputs, …)`; re-apply stored `escalation_reasons` via `force_escalate`; compare `record_sha256`; verify every contract signature |
| `app/cli/audit.py` | `replay CASE`, `audit-verify` |
| `Dockerfile` | `python:3.12-slim`; `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`, `PORT=8000`. `pip install --no-cache-dir -r requirements.txt` at **build** time, then `COPY . .` (filtered by `.dockerignore`, so `run.py`, `app/`, `ui/`, `eval/`, `policy/`, `zetaris/dq_rules.yaml`, `data/sample`, `data/kev`, `input_examples` and `vendor/` are all included). Non-root user that owns `logs/` and `var/`. `EXPOSE 8000 8501`. `HEALTHCHECK` with a Python one-liner (`python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"`; slim images have no curl). `CMD ["python", "run.py", "serve"]`. No secrets at build time; no downloads at runtime |
| `docker-compose.yml` | Services `api` (8000), `ui` (8501, `ARBITER_API_URL=http://api:8000`) and `sources` (8100, profile `zetaris`). Live Nightshift needs the API to run natively (Nightshift binds to the host's 127.0.0.1) |
| `.github/workflows/ci.yml` ✎ | Adds a `docker` job: build; run with `SAMPLE_MODE=true` and **no env file**; wait for health; POST every input example; assert outcomes against `expected.json`; upload logs as an artefact |
| `scripts/clean_clone_check.py` | 04 §6 steps 1–8; writes `logs/clean-clone-report.md` and copies it to `docs/passes/clean-clone-<date>.md` (committed evidence) |

## B5. Acceptance tests (marker `p4b`)

| Id | Test |
|---|---|
| P4-T10 | Replay `match=true` for all six e2e examples (run offline in the test) |
| P4-T11 | Tampering with one stored fact value gives `match=false` with a diff naming the fact. A tampered policy file gives `policy_hash` false |
| P4-T12 | `GET /audit/verify` passes; directly tampering with one audit row returns `{ok:false, first_bad_seq}` |
| P4-T13 | Approvals: example 5 (DECLINE) is `pending_approval`. Approval as `tprm_analyst` gives 403; as `tprm_lead` the contract is executed and an outbox file written. An expired contract (clock injected) gives 409 |
| P4-T14 | `GET /cases` ordering by residual risk, then created; badges carry text |
| P4-T15 | Persistence across restart: the store reopens and all endpoints return the same data |
| P4-T16 | Every error path returns `ErrorResponse` with no traceback (parametrised over 404, 400, 403, 409, 422) |
| P4-T17 | Docker sample smoke (CI job; locally with `ARBITER_DOCKER_TESTS=1`): image builds; container started with no env file answers `/health` and all six examples with the expected outcomes |
| P4-T18 | `clean_clone_check.py --local .` (clone of the local repo) passes steps 1–8 on the developer's machine |

## B6. Verification

```
python run.py replay CASE-0001 ; python run.py audit-verify
python scripts/tasks.py verify-pass --pass 4b
```

## B7. Definition of done

- [ ] Replay is green for every example.
- [ ] The report contains a replay output sample and the approval flow sequence.

## B8. Cut line

The JSON-to-SQLite migration (start clean instead).

## B9. Cursor prompt

```
/start-pass 4b
You are implementing lane P4-B of Arbiter: SQLite case store, contract approvals, replay, audit verification and the read API.
Read: AGENTS.md; docs/spec/00_MASTER_SPEC.md §§8.7–8.9, 10, 14; docs/spec/02_POLICY.md §3 (approvals, roles); docs/spec/04_SUBMISSION_PLAYBOOK.md §6; docs/spec/passes/P4_MEMORY_ACTIONS_API.md lane B; the current app/store.py interface (keep it stable: lane P4-A depends on it).
Plan Mode: .cursor/plans/P4-B.md with schema, endpoints, Docker/CI plan and tests P4-T10..P4-T18. Wait for approval.
Tests first (marker p4b) → commit → implement until `python scripts/tasks.py verify-pass --pass 4b` is green.
Finish with docs/passes/P4-B_REPORT.md + docs/cursor-usage/<LABEL>.md; push p4b-api; delete .cursor/ACTIVE_PASS; stop.
```

## B10. Explain it

1. What exactly does replay recompute, and what would make it fail?
2. Why does approval create a child contract?
3. Who can approve a DECLINE, and where is that rule written?
4. How is the queue ordered, and why?
5. What does `/audit/verify` prove to an auditor?
