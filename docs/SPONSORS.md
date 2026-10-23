# Sponsor technology

Every claim below points at a file in this repo and at a trace line from `logs/examples/`. The lines are from `python run.py examples` on 23 Oct 2026 with `SAMPLE_MODE=true` and `LLM_PROVIDER=offline`. They show the agent loop, the DuckDB mirror, the offline generator, the guard, and a signed outbox write. They do not show a Zetaris request id or a Nightshift model id. Those appear only when a run's `backend` is `zetaris` and its `provider` is `meterless`.

## Zetaris

Five synthetic systems (procurement, contracts, ITSM, a GRC watchlist, and the vendor trust portal) are registered as Lightning REST tables, exposed as views, and compiled into the USL `vendor_risk` in `lightning.metastore.arbiter`. The statements are `zetaris/sql/01_sources.sql`, `zetaris/sql/02_kev.sql`, and `zetaris/sql/03_usl.sql`. Data-quality rules are `zetaris/dq_rules.yaml`. The client is `app/data/zetaris.py`. Agents do not hold a connector. They send a registry id from `app/data/queries.yaml`.

On the committed sample runs the mirror answers. This line is `Q_COMPONENT_KEV` for Quillfeather (`run-3d6b7460d393`), `backend` `duckdb`, 15 rows, source system `cisa_kev`:

```jsonl
{"timestamp":"2026-10-23T01:03:17.614905Z","run_id":"run-3d6b7460d393","trace_id":"run-3d6b7460d393","span_id":"9c0193f1f4b94db7","parent_span_id":null,"agent_name":"EvidenceAgent","action":"query_run","input_summary":"query_id=Q_COMPONENT_KEV params=['vendor_id']","output_summary":"rows=15 backend=duckdb","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":null,"route":null,"model":null,"latency_ms":24,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":"cisa_kev","query_id":"Q_COMPONENT_KEV","rows":15,"backend":"duckdb","loop":null,"iteration":2,"mode":{"data":"duckdb","llm":"offline"}}
```

Live mode uses the same query id through `app/data/zetaris.py`. A live trace would set `backend` to `zetaris` and include the request id. This file does not contain that line.

A DQ failure is query `Q_DQ_INVALID` in `app/data/queries.yaml`. The Quillfeather evaluator asks for it on the second loop (`C07→Q_DQ_INVALID` in the same trace).

## Meterless Nightshift

Every model call goes through `app/llm/generator.py`. The Nightshift provider is `app/llm/providers/meterless.py` (discovery on `/v1/models`, routes `meterless/fast` and `meterless/deep`). If Nightshift is down, resolution tries NVIDIA direct (`app/llm/providers/nvidia.py`) and then `app/llm/providers/offline.py`.

The committed examples forced the offline provider. The planner line records that. It is not a Nightshift call:

```jsonl
{"timestamp":"2026-10-23T01:03:17.355806Z","run_id":"run-3d6b7460d393","trace_id":"run-3d6b7460d393","span_id":"6b883f43db174676","parent_span_id":null,"agent_name":"PlannerAgent","action":"plan","input_summary":"iteration=1 required=7","output_summary":"7 queries: Q_VENDOR_ALIASES,Q_WATCHLIST_SCREEN,Q_WATCHLIST_ALL,Q_SUBMISSION,Q_SUBMISSION_ANSWERS,Q_SUBMISSION_DOCUMENTS,Q_VENDOR_COMPONENTS","target_agent":"EvidenceAgent","confidence":null,"retry_count":0,"status":"success","provider":"offline","route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":1,"mode":{"data":"duckdb","llm":"offline"}}
```

`model` is null. `metadata.json` therefore lists no runtime model ids. The NVIDIA catalog ids in that file are the configured fallback names, not ids returned by a runtime on these traces.

## Meterless H-MEM

`app/memory/hmem/` is the Python port. `tests/conformance/test_hmem_conformance.py` runs the 13 upstream vectors. Domain retrieval and the trust ledger are `app/memory/precedents.py`. The policy applies precedent exceptions. It does not let the memory engine pick an outcome.

These examples set `ARBITER_MEMORY=off`, so the redecide step runs with no precedents. That is the line, not a claim that memory changed the outcome:

```jsonl
{"timestamp":"2026-10-23T01:03:17.719792Z","run_id":"run-3d6b7460d393","trace_id":"run-3d6b7460d393","span_id":"509622b276cb443c","parent_span_id":null,"agent_name":"Orchestrator","action":"redecide","input_summary":"precedents=0","output_summary":"outcome=ESCALATE","target_agent":"ChallengerAgent","confidence":null,"retry_count":0,"status":"success","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"duckdb","llm":"offline"}}
```

## Meterless Scout

`app/guard/scout_guard.py` screens vendor text before a model sees it. The adversarial cases are `tests/conformance/test_scout_adversarial.py`. On Oakhaven (`run-ac35d0a215a4`) a document segment is blocked and the outcome is `ESCALATE`:

```jsonl
{"timestamp":"2026-10-23T01:03:18.097380Z","run_id":"run-ac35d0a215a4","trace_id":"run-ac35d0a215a4","span_id":"ef084c66f9384acb","parent_span_id":null,"agent_name":"ScoutGuard","action":"guard_segment","input_summary":"segment_id=doc-DOC-0015-0 len=81","output_summary":"level=block score=0.920","target_agent":null,"confidence":null,"retry_count":0,"status":"blocked","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"duckdb","llm":"offline"}}
```

Actions are HMAC-signed execution contracts in `app/actions/contracts.py`. Quillfeather's escalate action was executed into the outbox only after that contract path:

```jsonl
{"timestamp":"2026-10-23T01:03:17.829358Z","run_id":"run-3d6b7460d393","trace_id":"run-3d6b7460d393","span_id":"d11c6202581c459b","parent_span_id":null,"agent_name":"ActionExecutor","action":"execute_action","input_summary":"contract=ctr-3748bd79b936 intent=vendor.onboarding.escalate","output_summary":"executed: ok → var/outbox/itsm/ctr-3748bd79b936.json","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"duckdb","llm":"offline"}}
```

The Challenger cannot approve. On the same run it escalates:

```jsonl
{"timestamp":"2026-10-23T01:03:17.826918Z","run_id":"run-3d6b7460d393","trace_id":"run-3d6b7460d393","span_id":"9e0da5bc487b4f18","parent_span_id":null,"agent_name":"ChallengerAgent","action":"challenge","input_summary":"outcome=ESCALATE loops_left=0","output_summary":"escalate CHALLENGE_T1_UNCORROBORATED source=deterministic","target_agent":"ReporterAgent","confidence":null,"retry_count":0,"status":"escalated","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"duckdb","llm":"offline"}}
```

## NVIDIA

Configured model ids, in `.env.example`, are `nvidia/nemotron-3.5-lightning-30b-a3b` (fast) and `nvidia/nemotron-3-super-120b-a12b` (deep). Live traffic is meant to reach them through Nightshift. The direct client is `app/llm/providers/nvidia.py`. No committed example trace contains those ids. The offline planner line quoted above is the evidence for how this sample run was labelled.

## Cursor

The build ran in Cursor from `AGENTS.md` and `.cursor/rules/`. Each pass has a plan under `.cursor/plans/`. Commands are `.cursor/commands/`. The verify hook is `.cursor/hooks.json`. Per-lane notes are compiled in `docs/CURSOR_USAGE.md`.

The Evaluator sending work back, which is the loop the plans required, is this line from `run-3d6b7460d393`:

```jsonl
{"timestamp":"2026-10-23T01:03:17.508010Z","run_id":"run-3d6b7460d393","trace_id":"run-3d6b7460d393","span_id":"95e884fa1ad74355","parent_span_id":null,"agent_name":"EvaluatorAgent","action":"evaluate","input_summary":"claims=16 queries=8","output_summary":"gaps: C06→Q_VENDOR_INCIDENTS; C07→Q_VENDOR_CONTRACT; C08→Q_VENDOR_CONTRACT; C09→Q_VENDOR_CONTRACT; C10→Q_VENDOR_CONTRACT; C12→Q_COMPONENT_KEV","target_agent":"PlannerAgent","confidence":null,"retry_count":0,"status":"needs_revision","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":1,"mode":{"data":"duckdb","llm":"offline"}}
```

Pellucid (`run-a1ad72bed1f3`) completing as `APPROVE` is the policy outcome, not a model choice:

```jsonl
{"timestamp":"2026-10-23T01:03:17.254553Z","run_id":"run-a1ad72bed1f3","trace_id":"run-a1ad72bed1f3","span_id":"e2cfec8c69844372","parent_span_id":null,"agent_name":"Orchestrator","action":"complete_run","input_summary":"case_id=CASE-0003","output_summary":"APPROVE in 0.477s","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"duckdb","llm":"offline"}}
```

## What was unique

1. The policy decides. Models plan, extract, criticise, and write. The `APPROVE` line above is `Orchestrator/complete_run` after `app/policy/engine.py` has run. The implementation is `app/policy/engine.py`.
2. The Evaluator checks the vendor against systems of record and KEV. The `needs_revision` line names `Q_COMPONENT_KEV`, and the query line shows that id running.
3. Memory is governed. The redecide line shows the hook. With memory off, `precedents=0`. A precedent can move a later outcome only through the policy exception in `policy/arbiter_policy.v1.yaml` and a human review in `app/api/routes_review.py`.
4. Signed contracts. The ActionExecutor line is the outbox write for `vendor.onboarding.escalate`. Verification and replay are `app/actions/contracts.py` and `app/audit/replay.py`.
