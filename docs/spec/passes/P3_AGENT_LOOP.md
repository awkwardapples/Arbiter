# P3: The agent loop (orchestrator, five agents, facts, confidence, actions, `/run`)

## 1. Goal

`POST /run` and `python run.py assess` run a real, bounded, multi-agent loop end to end:

```
INTAKE → PLAN → GATHER → EVALUATE (↺ PLAN ≤ 2) → DECIDE₁ → MEMORY_CHECK → DECIDE₂ → CHALLENGE (↺ PLAN ≤ 1 | escalate | accept)
  → REPORT → CONTRACT → EXECUTE → DONE
```

Each run produces a schema-valid response, an honest trace, a DecisionRecord from the policy engine, a cited report, and a signed contract that is executed or pending approval. The loop is the same in live mode (Zetaris + Nightshift) and offline (DuckDB + deterministic fallbacks). All six input examples reach their expected outcomes offline.

## 2. Why it scores

This lane is most of **Technical (20)** and **Demo (15)**:

- real loops, critique, retries and escalation in traces;
- agents with distinct authority.

It also carries **Impact (30)** through the decisions and outputs, and **Innovation** ("models read, the policy decides"; the Evaluator verifies the vendor through Zetaris).

## 3. Read first

- `AGENTS.md`
- Master spec §§6, 7, 8.2–8.7, 11, 12
- `01_DATA_AND_ZETARIS.md` §§3, 6
- `02_POLICY.md` §§3–6
- The interfaces of merged lanes: `app/data/*`, `app/llm/generator.py`, `app/policy/*`, `app/guard/*`, `app/actions/contracts.py`

## 4. Depends on

P0, P1-A, P2-B, P2-C, P2-D (merged). P2-A and P1-B are optional at start: memory uses `NullMemory` until P4-A; the backend is DuckDB until P1-B.

## 5. The design: why the loops are natural, not staged

**Screen, then verify.** You cannot know which systems of record to cross-check until you have read what the vendor claims.

- **Iteration 1 (screen).** The Planner gathers:
  - the vendor profile and aliases;
  - the watchlist screen (C11 is a hard gate, always checked): `Q_WATCHLIST_SCREEN` plus `Q_WATCHLIST_ALL` for near-matches;
  - the submission, answers, documents and declared components (`Q_VENDOR_COMPONENTS`).
- **The Evaluator then:**
  - grounds every extracted claim;
  - finds controls whose only support is an *unverified vendor claim* that has a system-of-record check available (residency → CLM; "no incidents" → ITSM; components → KEV join; breach hours, DPA, sub-processors → CLM);
  - sends the Planner back with `suggested_query_ids`. This is the `needs_revision` event.
- **Iteration 2 (verify)** runs those queries. Contradictions or DQ issues may trigger **one confirming re-query** (iteration 3) before escalation.

Which queries are requested depends entirely on the case's claims, tier and data categories. A vendor with no declared components never gets a KEV query (`vuln.kev_matches = 0` by definition); a vendor with no personal data never gets contract checks for C07–C09.

## 6. Deliverables

| File | Responsibility |
|---|---|
| `app/state.py` | `CaseState` (pydantic):<br>- `case_id`, `run_id`, `as_of`, `input`, `mode`, `budget_deadline`;<br>- `profile`, `tier_hint`;<br>- `plans[]`, `executed_queries: dict[query_id → QueryResult]`;<br>- `segments[]` (guarded text with GuardResult), `claims[]`, `facts[]`, `contradictions[]`, `dq_flags[]`, `guard_flags[]`, `evaluations[]`;<br>- `decision`, `precedents_considered[]`, `challenge`, `report`, `contracts[]`;<br>- counters `eval_loops`, `challenge_loops`;<br>- `evidence_index` (E-ids → provenance) |
| `app/orchestrator.py` | An explicit state machine (`enum State`; a `transition(state) -> State` table; no framework). It enforces the loop bounds (`MAX_EVAL_LOOPS=2`, `MAX_CHALLENGE_LOOPS=1`) and the run budget (`RUN_BUDGET_SECONDS`, checked before every state). Every transition is traced. **DECIDE₁ → MEMORY_CHECK → DECIDE₂** (02 §5): DECIDE₁ runs with no precedents; MEMORY_CHECK asks the memory port for candidates for DECIDE₁'s failing exception-eligible controls and recomputes confidence; DECIDE₂ runs the same `decide` with the candidates (traced `redecide`). `as_of` for every case is `settings.ARBITER_AS_OF`. `SAFE_ESCALATE` handles any unexpected exception or `BudgetExceeded`: it runs `decide` on the facts gathered so far plus `force_escalate("SYSTEM_<ErrorType>")`; if `decide` itself fails, it uses `DecisionRecord.safe_escalation(...)` (additive classmethod in schemas). The template report follows, and then the contract. `run(case_input, *, options) -> RunResponse`. Dependencies are injected (backend factory, generator, memory port, sink, clock) for tests |
| `app/agents/base.py` | `Agent` protocol (`name`, `role`, `__call__(state, ctx) -> state`). `AgentContext` holds tracer, backend, generator, policy, calibration, memory, settings and clock. Helper `llm_or_fallback(fn_llm, fn_det, *, purpose)`: on `OfflineProvider`, `ParseFailure`, `UpstreamTimeout`, `UpstreamError` or `Unauthorized` it runs the deterministic version and traces `status=fallback, provider=offline`. On the three upstream errors it also marks the provider degraded **for the rest of the run**, so later steps go straight to their fallbacks instead of waiting on timeouts |
| `app/agents/llm_schemas.py` | `PlanOut`, `ClaimListOut`, `CritiqueOut`, `ChallengeOut`, `ReportOut` (strict, `extra="forbid"`) |
| `app/agents/planner.py` | `PlannerAgent` (deep). The **deterministic planner** is §5 exactly. For inline cases it uses `Q_WATCHLIST_ALL` / `Q_INCIDENTS_BY_NAME` / `Q_KEV_BY_PRODUCTS`. It adds prior-assessment verify queries in iteration 1 when memory returns them (P4-A). The **LLM planner** gets the registry catalogue (id, description, control_ids), profile, gaps, the challenge request and the budget, and returns `PlanOut {queries: [{query_id, reason}], extraction_targets, rationale}`. **Validator (always runs):** it drops unknown or already-run ids, builds params in code (never from the model), and re-adds mandatory queries (iteration 1 screen set; the Evaluator's required suggestions). Corrections are traced (`action="plan_corrected"`) |
| `app/agents/evidence.py` | `EvidenceAgent` (fast). It runs the plan's queries through the backend, then guards every answer and document text with `scout_guard.guard(...)`: a `block` withholds the segment and adds a guard flag; PII is redacted. It **extracts** claims from the redacted, unblocked text: LLM `ClaimListOut` in one batched call (answers keyed by question id, wrapped in `<vendor_text>`); keys must be allowed for that question (01 §3); each claim needs a `quote`. The deterministic fallback is `app/extract/deterministic.py`. It also extracts supporting claims from document text (C01 corroboration, C05 metadata). Each query, guard result and extraction is traced |
| `app/extract/deterministic.py` | A rule-based extractor per question (below). Quotes are the exact source sentence. Pure and unit-tested |
| `app/grounding.py` | `is_grounded(quote, source) -> bool`: casefold, collapse whitespace, normalise quotes and dashes, then substring. Paraphrase fails |
| `app/facts.py` | `derive(state, policy) -> (facts, contradictions)` per 02 §4. SoR beats claim. `contradiction_checks` come from the policy. DQ flags downgrade to UNKNOWN. Fact ids are `F-<control>-<n>`; evidence ids are `E-<system>-<record_key>` |
| `app/agents/evaluator.py` | `EvaluatorAgent` (fast + code). Grounds claims (ungrounded → state UNKNOWN; affecting a required control → a re-extraction target). Runs `facts.derive`. Computes coverage per applicable required control (tier via `policy.tiering`). Builds gaps with `suggested_query_ids` from the control → verify-query map (below), excluding queries already run. If a contradiction is material and its SoR query has run only once, it requests one confirming re-query. **LLM critic** (optional): `CritiqueOut {downgrades: [{claim_id, reason}]}`, which may only downgrade TRUE→UNKNOWN (validated). `sufficient` means no suggestions and no pending re-extractions. Traces `needs_revision` to PlannerAgent, listing the gap controls, or `success` to PolicyEngine |
| `app/confidence.py` | `compute(state, calibration) -> ConfidenceBreakdown` (master spec §8.6; `precedent_alignment` = 1.0 until memory is present) |
| `app/agents/memory_port.py` | `MemoryPort` protocol: `find_precedents(profile, failing_controls) -> list[PrecedentCandidate]`, `prior_assessments(vendor_ref) -> list[...]`, `record_assessment(record)`. `NullMemory` returns empty lists. P4-A provides the H-MEM implementation |
| `app/agents/challenger.py` | `ChallengerAgent` (deep). **Deterministic triggers:**<br>(a) T1 and C01 TRUE supported only by `vendor_answer` provenance: re-plan for corroborating documents if a loop is left, else escalate `CHALLENGE_T1_UNCORROBORATED`;<br>(b) an applied precedent with any `wrong` feedback: escalate `CHALLENGE_PRECEDENT_DISPUTED`;<br>(c) `sanctions.near_matches ≥ 1` at T1: escalate `CHALLENGE_NEAR_MATCH`.<br>**LLM challenge** (only when the candidate is APPROVE or APPROVE_WITH_CONDITIONS): `ChallengeOut {action: accept\|re_plan\|escalate, category: uncorroborated_claim\|stale_evidence\|precedent_mismatch\|scope_gap\|other, cited_fact_ids, suggested_query_ids, rationale}`. Validator: cited ids must exist; `other` can only accept; `re_plan` needs new valid query ids and a loop left. **It can never return a better outcome.** Escalation goes through `engine.force_escalate`. Traces `request_replan` / `escalated` / `success` |
| `app/agents/reporter.py` | `ReporterAgent` (deep). `ReportOut`: summary (≤ 120 words), rationale sentences each with `citations` (fact, rule, precedent and evidence ids), recommended actions, a clarification email (REQUEST_INFO, built from counterfactual `question_ids` with question texts) or an escalation note, and limitations. **Validator:** it drops sentences with unknown or no citations; it rejects a summary whose stated outcome differs from the record (then uses the template). The template report (`template:v1`) is built deterministically from the record. `Report.generator` records which one was used |
| `app/actions/executor.py` | `execute(contract, *, now) -> ExecutionResult`. `contracts.verify` first; if required approvals are present, it writes the outbox, otherwise returns `pending_approval`. Traced (`action="execute_action"`) |
| `app/actions/outbox.py` | Writes `var/outbox/<system>/<contract_id>.json` (system from capability: `procurement`, `email`, `itsm`) with the drafted payload |
| `app/store.py` | **Created here** (JSON files under `var/cases/`) with the **full interface both P4 lanes need**: `save(bundle)`, `get(case_id)`, `list(order="risk")`, `put_contract(contract)`, `contracts_for(case_id)`, `put_review(review)`, `reviews_for(case_id)`, `put_human_decision(record)`. P4-B swaps the implementation to SQLite behind the same interface and takes ownership |
| `app/api/routes_run.py` | `POST /run` takes `RunRequest` and returns `RunResponse`. `options.sample_mode` forces DuckDB for that run. Errors use the structured shape |
| `app/cli/run_case.py` | `assess --input FILE [--sample] [--llm offline] [--out FILE]` prints a readable summary plus the JSON path |
| `app/llm/prompts/*.md` | Final prompt texts (text only; the template mechanism belongs to P2-B) |
| `tests/e2e/test_examples_offline.py` | See P3-T9 |

**Deterministic extractor rules** (`app/extract/deterministic.py`; test every rule):

| Question kind | Rule |
|---|---|
| Boolean (Q01, Q02, Q05, Q06, Q12, Q15) | Split into sentences; take the first sentence mentioning the topic keyword. **Future or hedged** (`planned`, `roadmap`, `next year`, `Q[1-4]`, `in progress`, `aim to`, `will be`) gives FALSE. **Vague** (`industry-standard`, `where appropriate`, `as needed`, `best practice` with no specifics) gives UNKNOWN. **Negation** (`not`, `no`, `never`, `do not`, `don't`, `isn't`) scoped to the topic word gives FALSE, except double-negation patterns that affirm (`no longer allow password-only`, `not only … but`), which give TRUE. **Affirm** (`yes`, `enforced`, `required`, `mandatory`, `always`) gives TRUE |
| Q03 | Rotation days: `every N days`, `monthly`=30, `quarterly`=90, `annually`/`yearly`=365. Vaulted: any of `vault`, `secrets manager`, `key vault`, `kms`, `hsm` |
| Q04 | Review interval days: as Q03 |
| Q07 | `assurance.claimed`: the set of {`SOC 2 Type II`, `ISO 27001`} mentioned (case-insensitive, allowing `SOC2` and `ISO/IEC 27001`) |
| Q08 | `no`/`none`/`zero` incidents gives 0; a number word or digit gives N |
| Q09 | Hours: `N hours`, `Nh`, `N days`×24 |
| Q10 | Regions from a gazetteer (EU: EU, European Union, Frankfurt, Dublin, Amsterdam, Paris; UK: UK, United Kingdom, London; US: US, USA, United States, Virginia, Oregon, Ohio). "only" means the set is exact |
| Q11 | `SCC`, `standard contractual clauses` → SCCs; `IDTA` → IDTA; `none`/`not applicable` → NONE |
| Q13 | Patch SLA days: `N days`, `two weeks`=14, `N business days`×1.4 rounded |
| Q14 | Pen-test interval months: `annually`=12, `twice a year`=6, `quarterly`=3 |

**Control → verify-query map** (Evaluator suggestions):

| Control | Query |
|---|---|
| C06 | `Q_VENDOR_INCIDENTS` (inline: `Q_INCIDENTS_BY_NAME`) |
| C07, C08, C09, C10 | `Q_VENDOR_CONTRACT` (+ `Q_DQ_INVALID` once contract rows exist) |
| C12 | `Q_COMPONENT_KEV` if components are declared (inline: `Q_KEV_BY_PRODUCTS`) |
| C05 | `Q_SUBMISSION_DOCUMENTS` with `doc_types` [soc2_type2_summary, iso27001_certificate, bridge_letter] if not yet run |
| C11 | Always in iteration 1 |

## 7. Interfaces

```python
def run(case_input: CaseInput, *, options: RunOptions, deps: Deps | None = None) -> RunResponse
class RunOptions(BaseModel): sample_mode: bool | None = None; llm: Literal["auto","meterless","nvidia","offline"] | None = None
class Deps(BaseModel): backend_factory; generator; memory: MemoryPort; sink; clock; tracer_factory
```

The `RunResponse.output` fields follow master spec §7: `findings` come from report rationale; `contradictions`, `counterfactuals` and `precedents` come from the record; `actions` from contracts; `artifacts` are outbox paths; `limitations` from the report plus mode notes (for example, "LLM offline: deterministic extraction used").

## 8. Acceptance tests (marker `p3`)

| Id | Test |
|---|---|
| P3-T1 | State machine with fake agents (table-driven): the happy path; evaluator loops capped at 2; challenger re-plan capped at 1; exception → SAFE_ESCALATE → REPORT → CONTRACT → DONE; every transition traced |
| P3-T2 | Deterministic extractor: ≥ 4 cases per row of the rules table, including tricky negations; every quote is a substring of the source |
| P3-T3 | Grounding: passes for whitespace, case and quote-style variants; fails for paraphrase and partial-word matches |
| P3-T4 | Fact derivation (table-driven over 02 §4): SoR precedence, contradiction creation with severity, DQ downgrade, inline submissions (`contract.status=none` → contract-stage path) |
| P3-T5 | Evaluator: an unverified residency claim suggests `Q_VENDOR_CONTRACT`; components suggest `Q_COMPONENT_KEV`; no components means no KEV suggestion; a material contradiction requests one confirm re-query, then becomes sufficient |
| P3-T6 | Planner validator: unknown ids dropped; mandatory re-added (traced `plan_corrected`); LLM `ParseFailure` → deterministic plan (traced `fallback`); params never taken from model output (a fake LLM returns a malicious `vendor_id`, and it is ignored) |
| P3-T7 | **Challenger cannot upgrade** (property test): random records × random `ChallengeOut` give a final outcome rank ≤ the candidate's. A cited non-existent fact id is rejected |
| P3-T8 | Reporter validator: uncited sentences dropped; outcome-mismatch summary → template; the template mentions every failing control and counterfactual |
| P3-T9 | **E2E offline:** every `input_examples/*.json` with `SAMPLE_MODE=true LLM_PROVIDER=offline ARBITER_MEMORY=off` and a fresh temporary `var/` gives the `expected.json` outcome. The response validates. `check_trace --require-collaboration` passes for **all six** (every example has at least one verify loop: its Q08 claim needs an ITSM check). Example 2's trace contains `needs_revision` and `query_id=Q_COMPONENT_KEV` |
| P3-T10 | **Integrity:** (a) the six examples give six distinct `record_sha256` values and at least four distinct outcomes; (b) mutation: rewrite example 1's Q01 answer to a denial and the outcome becomes ESCALATE with C01 FALSE; (c) a random inline submission (seeded) gives a valid decision |
| P3-T11 | API (this supersedes P0-T6 clause (b); delete that clause in this lane and note it in the report): `POST /run` with the bare and wrapped shapes; a bad body gives 400; `options.sample_mode=true` works with an empty env; `execution_time_seconds` > 0; `log_file` exists |
| P3-T12 | Injection: for example 3, the blocked segment's text never reaches `generate()` (spy captures all prompts; a canary is absent). The outcome is ESCALATE with `UNTRUSTED_CONTENT_TAMPERING` |
| P3-T13 | **Trace honesty:** with spies, the number of `model_call` events equals the number of generator invocations, and the number of `query_*` events equals backend calls. No event is emitted without its action having run |
| P3-T14 | Budget: `RUN_BUDGET_SECONDS=1` with a slow fake backend gives SAFE_ESCALATE, status `partial_success` or `escalated`, and a valid response in under 5 s |
| P3-T16 | **Label oracle:** for all 32 vendors and 4 inline cases, feeding `data/evals/truth_facts.jsonl` (plus the planted contradictions and guard expectations) straight into `policy.decide` reproduces the labelled outcome. This catches authoring errors in labels before the eval. The test may read `data/evals/`; `app/` may not |
| P3-T15 `live` | `example_2` through Zetaris and Nightshift: `check_trace --require-live --require-collaboration` passes; the outcome is ESCALATE; the trace has `zetaris_request_id` and `provider=meterless` |

## 9. Verification

```
SAMPLE_MODE=true LLM_PROVIDER=offline python run.py assess --input input_examples/example_2.json
python scripts/tasks.py verify-pass --pass 3
python scripts/tasks.py e2e-sample
ARBITER_LIVE_TESTS=1 pytest -m "p3 and live"      # with Zetaris + Nightshift up
```

The gate `scripts/gates/p3.py` runs `check_trace.py --require-collaboration` on the e2e traces and `check_hardcoding.py`.

## 10. Milestones (commit and push after each; tell the human)

| Milestone | Content |
|---|---|
| M1 | State, orchestrator and fake agents (P3-T1, T14) |
| M2 | Deterministic extractor, grounding, facts and evaluator (T2–T5) |
| M3 | Deterministic planner, challenger triggers, template reporter, executor → **e2e offline green** (T9, T10, T12, T13) |
| M4 | LLM paths for planner, extraction, critic, challenger and reporter, plus validators (T6–T8) |
| M5 | API and CLI (T11) |
| M6 | Live run with the human (T15) |

## 11. Definition of done

- [ ] All non-live tests are green and T15 is green live.
- [ ] The report includes:
  - the transition diagram (mermaid);
  - an excerpt of example 2's trace showing the loop;
  - the offline-versus-live outcome table for the six examples;
  - timings (p50 per example, live).

## 12. Cut lines (in order)

1. LLM critic in the Evaluator.
2. LLM challenge (keep the deterministic triggers and re-plan).
3. LLM planner (keep the deterministic planner, with the LLM used for rationale only).

Never cut: the loops, grounding, contradictions, guard integration, the policy decision, contracts and the trace.

## 13. Cursor prompt

```
/start-pass 3
You are implementing pass P3 of Arbiter: the bounded multi-agent loop. This is the core of the project.
Read: AGENTS.md; docs/spec/00_MASTER_SPEC.md §§6, 7, 8.2–8.7, 11, 12; docs/spec/01_DATA_AND_ZETARIS.md §§3, 6; docs/spec/02_POLICY.md §§3–6; docs/spec/passes/P3_AGENT_LOOP.md; and the public interfaces of app/data, app/llm/generator.py, app/policy, app/guard, app/actions/contracts.py.
Invariants that tests enforce: LLMs never decide (only app/policy/engine.py); the Challenger can never improve an outcome; params are built in code, never from model output; blocked vendor text never reaches the generator; every trace event corresponds to executed code.
Plan Mode: .cursor/plans/P3.md with the state table, agent I/O, the milestone plan M1–M6 and tests P3-T1..P3-T16. Wait for approval.
Tests first (marker p3) → commit → implement milestone by milestone, pushing after each green milestone and telling me.
Finish with docs/passes/P3_REPORT.md + docs/cursor-usage/<LABEL>.md; push p3-loop; delete .cursor/ACTIVE_PASS; stop.
```

## 14. Explain it

1. Walk through example 2's trace: which agent changed which other agent's work, and why?
2. Why is "screen, then verify" a genuine loop and not a staged one?
3. What exactly may an LLM do in this system, and what is it structurally prevented from doing?
4. What does a judge see if Nightshift is down mid-run?
5. How is the cited report kept honest?
