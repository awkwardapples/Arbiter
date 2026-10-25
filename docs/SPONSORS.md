# Sponsor technology

Every claim here points at a file in this repository and, where it is about live behaviour, at a committed trace line. The quoted ```` ```jsonl ```` lines are copied verbatim from `logs/examples/` and checked by `tests/unit/docs/test_claims.py` and `tests/unit/docs/test_sponsors.py`.

The live run quoted throughout is example 2, `run-211916c1544d` (Quillfeather Payroll Cloud Ltd, `ESCALATE`), made on 25 October 2026 against the Zetaris USL and Meterless Nightshift: `logs/examples/live/trace-run-211916c1544d.jsonl`.

## Zetaris

**What it does in Arbiter.** Zetaris is the single SQL access point. Five synthetic enterprise systems (procurement, CLM, ITSM, the GRC watchlist and the vendor trust portal) are Lightning REST tables, joined with the public CISA KEV catalogue and modelled as one Unified Semantic Layer, `vendor_risk`. Every agent query is a registry id in `app/data/queries.yaml`, sent by `app/data/zetaris.py`.

| Piece | File | Evidence |
|---|---|---|
| Lightning REST tables and SchemaStore views | `zetaris/sql/01_sources.sql`, `zetaris/sql/02_kev.sql` | `docs/ZETARIS_USL.md` §2; 9 table counts in `docs/passes/P1-B_parity.json` |
| USL `vendor_risk` (10 tables, descriptions, keys) | `zetaris/sql/03_usl.sql`, `app/data/usl_model.py` | `docs/ZETARIS_USL.md` §3; parity `query_layer: usl`, `all_green: true`, 416/416 registry comparisons |
| DQ rules | `zetaris/dq_rules.yaml` | DQ parity green; Zetaris marks contract `CTR-30028` invalid (DPA signed, no date), `docs/ZETARIS_USL.md` §5 |
| REST SQL API with request ids | `app/data/zetaris.py` | 14 queries in `run-211916c1544d`, each with a `zetaris_request_id`, 21.9 s of Zetaris time in total |
| Federated private + public join | `Q_COMPONENT_KEV` in `app/data/queries.yaml` | `run-211916c1544d`: Quillfeather's declared FortiOS joined to KEV inside Zetaris, 15 rows, `zetaris_request_id=04559cdd-f5ae-4ee7-af41-f742d4703094` |

The first live query of example 2. The `zetaris_request_id` is the `X-Request-ID` header Arbiter generates and sends with each statement:

```jsonl
{"timestamp":"2026-10-25T15:13:48.419921Z","run_id":"run-211916c1544d","trace_id":"run-211916c1544d","span_id":"0d6e6e69eef6451d","parent_span_id":null,"agent_name":"data","action":"query_zetaris","input_summary":"query_id=Q_VENDOR_PROFILE","output_summary":"rows=1 zetaris_request_id=ddbc292a-c2b4-47b6-a34e-1034e97f82c1","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":null,"route":null,"model":null,"latency_ms":881,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":"Q_VENDOR_PROFILE","rows":1,"backend":"zetaris","loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
```

The Planner reads the USL model as a compact catalogue (304 tokens) instead of raw schemas:

```jsonl
{"timestamp":"2026-10-25T15:13:48.469047Z","run_id":"run-211916c1544d","trace_id":"run-211916c1544d","span_id":"a30125dd1b714dbd","parent_span_id":null,"agent_name":"PlannerAgent","action":"usl_catalogue","input_summary":"usl_model_sha256=bb42f7626a4e693c9880ce1656f9493b5dea0541a1d5a538857982b155bf98b0","output_summary":"tokens=304","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":"plan","provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
```

The federated join: the vendor's declared components (private, the trust portal) against CISA's Known Exploited Vulnerabilities (public), in one Zetaris query:

```jsonl
{"timestamp":"2026-10-25T15:16:55.887221Z","run_id":"run-211916c1544d","trace_id":"run-211916c1544d","span_id":"2e67b49302d94d47","parent_span_id":null,"agent_name":"data","action":"query_zetaris","input_summary":"query_id=Q_COMPONENT_KEV","output_summary":"rows=15 zetaris_request_id=04559cdd-f5ae-4ee7-af41-f742d4703094","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":null,"route":null,"model":null,"latency_ms":1992,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":"Q_COMPONENT_KEV","rows":15,"backend":"zetaris","loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
```

The KEV catalogue Zetaris federates is the committed 84-row snapshot of the CISA feed (`data/kev/`), not a live pull; see `docs/ZETARIS_USL.md` §7.

## Meterless

### Nightshift Runtime

Every model call goes through the single seam `app/llm/generator.py` to `app/llm/providers/meterless.py`. Arbiter requests a lane (`meterless/fast` or `meterless/deep`); Nightshift picks the model and returns a compute receipt, which the trace keeps in `provider_meta`.

`python run.py llm proof` made one call per lane on 25 October 2026 and wrote `docs/evidence/nightshift_proof.json`:

| Lane | Arbiter sent | Routed mode | Model served | Receipt | Latency |
|---|---|---|---|---|---|
| fast | `meterless/fast` | `auto` (coerced) | `nvidia/nemotron-3.5-lightning-30b-a3b` | `rcpt_req_936ew345` | 2236 ms |
| deep | `meterless/deep` | `auto` (coerced) | `nvidia/nemotron-3.5-super-vl-120b-a12b` | `rcpt_req_wu3r6jyf` | 747 ms |

**Lane deviation, stated plainly.** The deep lane was designed for Nemotron 3 Super. That model, `nvidia/nemotron-3-super-120b-a12b`, returns HTTP 404 on this NVIDIA account (not entitled), so the deep lane is bound to `nvidia/nemotron-3.5-super-vl-120b-a12b`. Separately, Nightshift's Default app rule coerces both lanes to `auto`, which picks the model per request, so lane separation is not guaranteed. Meterless acknowledged the routing bug on 24 October 2026 and targeted a fix for its Sunday release. On Sunday 25 October the fix had not reached this build: the receipts above still record `app_policy.mode_coerced: True`, and a second proof that named exact model ids got Super VL on both lanes (`docs/evidence/history/nightshift_proof-run5-exact-ids.json`). In the live examples every successful call was served by Super VL; the calls `auto` sent to Lightning returned HTTP 502 and fell back. Human observations: `docs/evidence/nightshift_deviations.md`.

### H-MEM

`app/memory/hmem/` is the Python port of Meterless H-MEM, checked against the 13 upstream vectors in `tests/conformance/test_hmem_conformance.py`. `app/memory/precedents.py` adapts it to governed precedents. The live memory session (`docs/evidence/memory_session.md`, 6/6 steps) shows a lead-approved precedent, P-0001 from Marrowgate (VND-0011), letting the policy move Tessellate (VND-0012) to `APPROVE_WITH_CONDITIONS`. With memory reset, an analyst-role precedent, or `wrong` feedback, the same vendor escalates. The policy engine applies the exception, never a model:

```jsonl
{"timestamp":"2026-10-24T04:49:50.590441Z","run_id":"run-a1c914808974","trace_id":"run-a1c914808974","span_id":"af57aa480da94587","parent_span_id":null,"agent_name":"Orchestrator","action":"memory_check","input_summary":"failing=C05","output_summary":"candidates=1","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"auto"}}
{"timestamp":"2026-10-24T04:49:50.593255Z","run_id":"run-a1c914808974","trace_id":"run-a1c914808974","span_id":"4794b1671da3457c","parent_span_id":null,"agent_name":"MemoryKeeper","action":"precedent_applied","input_summary":"P-0001","output_summary":"ok","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"auto"}}
```

### Scout (guard and execution contracts subset)

`app/guard/scout_guard.py` screens every vendor answer and document before a model sees it; the adversarial cases are `tests/conformance/test_scout_adversarial.py`. In the live Quillfeather run each of the 16 answers passed:

```jsonl
{"timestamp":"2026-10-25T15:14:41.061636Z","run_id":"run-211916c1544d","trace_id":"run-211916c1544d","span_id":"a5f9b7fe7a224193","parent_span_id":null,"agent_name":"ScoutGuard","action":"guard_segment","input_summary":"segment_id=ans-Q01 len=34","output_summary":"level=pass score=0.000","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
```

In the live run of example 3, Oakhaven (`run-1b185078f01b`), a planted instruction in a document is blocked before any model sees it, and the case escalates:

```jsonl
{"timestamp":"2026-10-25T15:26:29.994112Z","run_id":"run-1b185078f01b","trace_id":"run-1b185078f01b","span_id":"303ab7d4daf24e4e","parent_span_id":null,"agent_name":"ScoutGuard","action":"guard_segment","input_summary":"segment_id=doc-DOC-0015-0 len=81","output_summary":"level=block score=0.920","target_agent":null,"confidence":null,"retry_count":0,"status":"blocked","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
```

Actions are HMAC-signed execution contracts (`app/actions/contracts.py`, `app/actions/executor.py`). The escalation ticket for the TPRM lead was written to the outbox only after its contract verified:

```jsonl
{"timestamp":"2026-10-25T15:17:35.658664Z","run_id":"run-211916c1544d","trace_id":"run-211916c1544d","span_id":"6ef3210fb6ae4074","parent_span_id":null,"agent_name":"ActionExecutor","action":"execute_action","input_summary":"contract=ctr-1554fd78b3d0 intent=vendor.onboarding.escalate","output_summary":"executed: ok → var/outbox/itsm/ctr-1554fd78b3d0.json","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
```

## NVIDIA: Our agents do real work on Nemotron

Every LLM step in live example 2, with its lane, the model Nightshift served and the receipt. The quoted lines follow the table.

| Step | Agent | Lane requested | Model served | Receipt | Result |
|---|---|---|---|---|---|
| plan | PlannerAgent | deep | `nvidia/nemotron-3.5-super-vl-120b-a12b` | `rcpt_req_306f1su6` | 7-query plan (`PlanOut`) |
| extract | EvidenceAgent | fast | `nvidia/nemotron-3.5-super-vl-120b-a12b` | `rcpt_req_38g5l1cf` | 16 quoted claims from 16 answers |
| critique | EvaluatorAgent | fast | `nvidia/nemotron-3.5-super-vl-120b-a12b` | `rcpt_req_yu0roar2` | Critique; the Evaluator sends the Planner back for C05–C10 and C12 |
| plan (revise) | PlannerAgent | deep | `nvidia/nemotron-3.5-super-vl-120b-a12b` | `rcpt_req_zt7h401t` | 3 follow-up queries: contract, incidents, KEV |
| plan (second revise) | PlannerAgent | deep | none: HTTP 502 empty response (Nightshift routed it to Lightning) | – | Deterministic fallback, labelled `fallback` |
| challenge | ChallengerAgent | deep | no model call in this run: the deterministic T1 rule fired first | – | Re-plan, then escalate (`CHALLENGE_T1_UNCORROBORATED`) |
| brief | ReporterAgent | deep (when enabled) | no model call in this run | – | Brief from the deterministic template (`generator=template:v2`); the report is `template:v1` |

Planning on Nemotron, with its receipt:

```jsonl
{"timestamp":"2026-10-25T15:14:39.993028Z","run_id":"run-211916c1544d","trace_id":"run-211916c1544d","span_id":"b52b708295384d10","parent_span_id":null,"agent_name":"PlannerAgent","action":"model_call","input_summary":"purpose=plan route=deep response=json attempt=1 prompt_chars=4986","output_summary":"json valid (PlanOut)","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":"meterless","route":"deep","model":"nvidia/nemotron-3.5-super-vl-120b-a12b","latency_ms":51498,"tokens_in":3773,"tokens_out":3072,"purpose":"plan","provider_meta":{"requested_model":"meterless/deep","response_id":"chatcmpl-f243a055-8ec9-4f92-aeae-2e6e46d5e019","schema":"meterless.compute_receipt.v1","receipt_id":"rcpt_req_306f1su6","decision_id":"req_306f1su6","provider_model":"meterless/auto","routed_model":"nvidia/nemotron-3.5-super-vl-120b-a12b","mode":"auto","requires_review":"False","winning_route.provider":"nvidia","winning_route.label":"Nemotron 3.5 Super VL 120B A12B","winning_route.kind":"cloud","winning_route.tier":"C","winning_route.model":"nvidia/nemotron-3.5-super-vl-120b-a12b","app_policy.app":"arbiter","app_policy.has_rule":"True","app_policy.bound_mode":"auto","app_policy.requested_mode":"deep","app_policy.routed_mode":"auto","app_policy.mode_coerced":"True","app_policy.privacy":"cloud-ok","cost.actual_usd":"0","cost.naive_usd":"0","cost.race_overhead_usd":"0","cost.verifier_usd":"0","cost.baseline.model":"nvidia/nemotron-3.5-super-vl-120b-a12b","cost.baseline.label":"Nemotron 3.5 Super VL 120B A12B","cost.baseline.source":"mode-default-frontier","savings.amount":"0","savings.currency":"USD","savings.vs":"Nemotron 3.5 Super VL 120B A12B","savings.baseline_source":"mode-default-frontier","no_think":"true"},"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
```

Claim extraction from untrusted vendor answers (after ScoutGuard):

```jsonl
{"timestamp":"2026-10-25T15:15:34.157810Z","run_id":"run-211916c1544d","trace_id":"run-211916c1544d","span_id":"d4b8606118694154","parent_span_id":null,"agent_name":"EvidenceAgent","action":"model_call","input_summary":"purpose=extract route=fast response=json attempt=1 prompt_chars=2912","output_summary":"json valid (ClaimListOut)","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":"meterless","route":"fast","model":"nvidia/nemotron-3.5-super-vl-120b-a12b","latency_ms":46664,"tokens_in":2426,"tokens_out":2467,"purpose":"extract","provider_meta":{"requested_model":"meterless/fast","response_id":"chatcmpl-6b7aa814-8823-4c67-89e0-45229da7cd97","schema":"meterless.compute_receipt.v1","receipt_id":"rcpt_req_38g5l1cf","decision_id":"req_38g5l1cf","provider_model":"meterless/auto","routed_model":"nvidia/nemotron-3.5-super-vl-120b-a12b","mode":"auto","requires_review":"False","winning_route.provider":"nvidia","winning_route.label":"Nemotron 3.5 Super VL 120B A12B","winning_route.kind":"cloud","winning_route.tier":"C","winning_route.model":"nvidia/nemotron-3.5-super-vl-120b-a12b","app_policy.app":"arbiter","app_policy.has_rule":"True","app_policy.bound_mode":"auto","app_policy.requested_mode":"fast","app_policy.routed_mode":"auto","app_policy.mode_coerced":"True","app_policy.privacy":"cloud-ok","cost.actual_usd":"0","cost.naive_usd":"0","cost.race_overhead_usd":"0","cost.verifier_usd":"0","cost.baseline.model":"nvidia/nemotron-3.5-super-vl-120b-a12b","cost.baseline.label":"Nemotron 3.5 Super VL 120B A12B","cost.baseline.source":"mode-default-frontier","savings.amount":"0","savings.currency":"USD","savings.vs":"Nemotron 3.5 Super VL 120B A12B","savings.baseline_source":"mode-default-frontier","no_think":"true"},"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
```

Critique, then the Evaluator sends work back:

```jsonl
{"timestamp":"2026-10-25T15:16:01.095792Z","run_id":"run-211916c1544d","trace_id":"run-211916c1544d","span_id":"37f993ff417d433f","parent_span_id":null,"agent_name":"EvaluatorAgent","action":"model_call","input_summary":"purpose=critique route=fast response=json attempt=1 prompt_chars=3369","output_summary":"json valid (CritiqueOut)","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":"meterless","route":"fast","model":"nvidia/nemotron-3.5-super-vl-120b-a12b","latency_ms":26905,"tokens_in":3202,"tokens_out":895,"purpose":"critique","provider_meta":{"requested_model":"meterless/fast","response_id":"chatcmpl-ee6a9ad7-60ca-4fc0-819d-33bc721ed78f","schema":"meterless.compute_receipt.v1","receipt_id":"rcpt_req_yu0roar2","decision_id":"req_yu0roar2","provider_model":"meterless/auto","routed_model":"nvidia/nemotron-3.5-super-vl-120b-a12b","mode":"auto","requires_review":"False","winning_route.provider":"nvidia","winning_route.label":"Nemotron 3.5 Super VL 120B A12B","winning_route.kind":"cloud","winning_route.tier":"C","winning_route.model":"nvidia/nemotron-3.5-super-vl-120b-a12b","app_policy.app":"arbiter","app_policy.has_rule":"True","app_policy.bound_mode":"auto","app_policy.requested_mode":"fast","app_policy.routed_mode":"auto","app_policy.mode_coerced":"True","app_policy.privacy":"cloud-ok","cost.actual_usd":"0","cost.naive_usd":"0","cost.race_overhead_usd":"0","cost.verifier_usd":"0","cost.baseline.model":"nvidia/nemotron-3.5-super-vl-120b-a12b","cost.baseline.label":"Nemotron 3.5 Super VL 120B A12B","cost.baseline.source":"mode-default-frontier","savings.amount":"0","savings.currency":"USD","savings.vs":"Nemotron 3.5 Super VL 120B A12B","savings.baseline_source":"mode-default-frontier","no_think":"true"},"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
{"timestamp":"2026-10-25T15:16:01.106320Z","run_id":"run-211916c1544d","trace_id":"run-211916c1544d","span_id":"6a0ba5b7bd4d4030","parent_span_id":null,"agent_name":"EvaluatorAgent","action":"evaluate","input_summary":"claims=16 queries=8","output_summary":"gaps: C06→Q_VENDOR_INCIDENTS; C07→Q_VENDOR_CONTRACT; C08→Q_VENDOR_CONTRACT; C09→Q_VENDOR_CONTRACT; C10→Q_VENDOR_CONTRACT; C12→Q_COMPONENT_KEV","target_agent":"PlannerAgent","confidence":null,"retry_count":0,"status":"needs_revision","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":1,"mode":{"data":"zetaris","llm":"meterless"}}
```

After the revised plan, the Evaluator finds the vendor's claim contradicted by the contract system:

```jsonl
{"timestamp":"2026-10-25T15:16:55.888882Z","run_id":"run-211916c1544d","trace_id":"run-211916c1544d","span_id":"10fb766705404e07","parent_span_id":null,"agent_name":"EvaluatorAgent","action":"contradiction_found","input_summary":"key=residency.regions control=C09","output_summary":"vendor=EU record=US system=clm record_key=contract_id=CTR-30007","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
```

The one failed call, which the trace labels honestly:

```jsonl
{"timestamp":"2026-10-25T15:17:27.642166Z","run_id":"run-211916c1544d","trace_id":"run-211916c1544d","span_id":"cd38a9debe2941bb","parent_span_id":null,"agent_name":"PlannerAgent","action":"model_call","input_summary":"purpose=plan route=deep response=json attempt=1 prompt_chars=6021","output_summary":"UpstreamError: meterless HTTP 502: provider_error api_error nvidia/nemotron-3.5-lightning-30b-a3b_empty_response","target_agent":null,"confidence":null,"retry_count":0,"status":"fallback","provider":"meterless","route":"deep","model":null,"latency_ms":31690,"tokens_in":null,"tokens_out":null,"purpose":"plan","provider_meta":{"requested_model":"meterless/deep"},"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
```

The policy engine, not a model, decides:

```jsonl
{"timestamp":"2026-10-25T15:17:34.796807Z","run_id":"run-211916c1544d","trace_id":"run-211916c1544d","span_id":"07ac0516bbc2444b","parent_span_id":null,"agent_name":"PolicyEngine","action":"decide","input_summary":"facts=34 contradictions=1 precedents=0","output_summary":"outcome=ESCALATE tier=T1 failing=C09,C12 unknown=C05","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
```

Across the 24 October live evaluation, 20 of 25 model calls succeeded: 19 served by Super VL and 1 deep-lane plan served by `nvidia/nemotron-3.5-lightning-30b-a3b` (`rcpt_req_szjmqbge`, `eval/results_live/20261024T045916036274Z/traces/trace-run-f59a50433bf5.jsonl`). The 5 failures were HTTP 502s and fell back to deterministic logic (`docs/EVALUATION.md`). `app/llm/providers/nvidia.py` is the build.nvidia.com fallback; no committed run used it.

## Cursor

Arbiter was built pass by pass from `AGENTS.md`, under five project rules (`.cursor/rules/`), four commands (`.cursor/commands/`, including `/start-pass` and `/verify-pass`) and a stop hook (`.cursor/hooks.json`) that re-runs `python scripts/tasks.py verify-pass` and feeds failures back, up to six times. Each pass has a plan in `.cursor/plans/` (24 files), a gate in `scripts/gates/`, a report in `docs/passes/` and a usage note in `docs/cursor-usage/`, compiled into `docs/CURSOR_USAGE.md`. Parallel lanes ran in separate worktrees (`.cursor/worktrees.json`).

Of the 21 pass notes, 17 record Cursor (Composer, Grok 4.7 and Claude Opus as the agent model), one names its model without the tool, and three (P14-B, P15 and P17) were done in Claude Code; see the table in `docs/CURSOR_USAGE.md`.
