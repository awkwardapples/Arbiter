# Sponsor technology

Every claim here points at a file in this repository and, where it is about live behaviour, at a committed trace line. The quoted ```` ```jsonl ```` lines are copied verbatim from `logs/examples/` and checked by `tests/unit/docs/test_claims.py` and `tests/unit/docs/test_sponsors.py`.

The live run quoted throughout is example 1, `run-83de5da137c0` (Pellucid Forms Ltd, `APPROVE`), made on 24 October 2026 against the Zetaris USL and Meterless Nightshift: `logs/examples/live/trace-run-83de5da137c0.jsonl`.

## Zetaris

**What it does in Arbiter.** Zetaris is the single SQL access point. Five synthetic enterprise systems (procurement, CLM, ITSM, the GRC watchlist and the vendor trust portal) are Lightning REST tables, joined with the public CISA KEV catalogue and modelled as one Unified Semantic Layer, `vendor_risk`. Every agent query is a registry id in `app/data/queries.yaml`, sent by `app/data/zetaris.py`.

| Piece | File | Evidence |
|---|---|---|
| Lightning REST tables and SchemaStore views | `zetaris/sql/01_sources.sql`, `zetaris/sql/02_kev.sql` | `docs/ZETARIS_USL.md` §2; 9 table counts in `docs/passes/P1-B_parity.json` |
| USL `vendor_risk` (10 tables, descriptions, keys) | `zetaris/sql/03_usl.sql`, `app/data/usl_model.py` | `docs/ZETARIS_USL.md` §3; parity `query_layer: usl`, `all_green: true`, 416/416 registry comparisons |
| DQ rules | `zetaris/dq_rules.yaml` | DQ parity green; Zetaris marks contract `CTR-30028` invalid (DPA signed, no date), `docs/ZETARIS_USL.md` §5 |
| REST SQL API with request ids | `app/data/zetaris.py` | 12 queries in `run-83de5da137c0`, each with a `zetaris_request_id` |
| Federated private + public join | `Q_COMPONENT_KEV` in `app/data/queries.yaml` | Live eval run `run-257c86984507` (Quillfeather): 15 KEV rows, `zetaris_request_id=75b06ff3-786b-45f2-9f74-cefdba9b659b`, in `eval/results_live/20261024T045916036274Z/traces/trace-run-257c86984507.jsonl` |

The first live query of example 1. The `zetaris_request_id` is the `X-Request-ID` header Arbiter generates and sends with each statement:

```jsonl
{"timestamp":"2026-10-24T04:41:21.164571Z","run_id":"run-83de5da137c0","trace_id":"run-83de5da137c0","span_id":"9ff44f96653943a7","parent_span_id":null,"agent_name":"data","action":"query_zetaris","input_summary":"query_id=Q_VENDOR_PROFILE","output_summary":"rows=1 zetaris_request_id=55bf9cc1-e25e-4a48-9b41-f2bda35d935d","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":null,"route":null,"model":null,"latency_ms":1024,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":"Q_VENDOR_PROFILE","rows":1,"backend":"zetaris","loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
```

The Planner reads the USL model as a compact catalogue (304 tokens) instead of raw schemas:

```jsonl
{"timestamp":"2026-10-24T04:41:21.209131Z","run_id":"run-83de5da137c0","trace_id":"run-83de5da137c0","span_id":"5f09b3729bc24ba3","parent_span_id":null,"agent_name":"PlannerAgent","action":"usl_catalogue","input_summary":"usl_model_sha256=bb42f7626a4e693c9880ce1656f9493b5dea0541a1d5a538857982b155bf98b0","output_summary":"tokens=304","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":"plan","provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
```

`Q_VENDOR_360`, the USL merge of vendor, contract, submission, components and KEV, running live:

```jsonl
{"timestamp":"2026-10-24T04:43:58.965629Z","run_id":"run-83de5da137c0","trace_id":"run-83de5da137c0","span_id":"1567838ce4344570","parent_span_id":null,"agent_name":"data","action":"query_zetaris","input_summary":"query_id=Q_VENDOR_360","output_summary":"rows=1 zetaris_request_id=2dea34da-d128-4093-9032-6128b331ae04","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":null,"route":null,"model":null,"latency_ms":4312,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":"Q_VENDOR_360","rows":1,"backend":"zetaris","loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
```

The KEV catalogue Zetaris federates is the committed 84-row snapshot of the CISA feed (`data/kev/`), not a live pull; see `docs/ZETARIS_USL.md` §7.

## Meterless

### Nightshift Runtime

Every model call goes through the single seam `app/llm/generator.py` to `app/llm/providers/meterless.py`. Arbiter requests a lane (`meterless/fast` or `meterless/deep`); Nightshift picks the model and returns a compute receipt, which the trace keeps in `provider_meta`.

`python run.py llm proof` made one call per lane and wrote `docs/evidence/nightshift_proof.json`:

| Lane | Arbiter sent | Routed mode | Model served | Receipt | Latency |
|---|---|---|---|---|---|
| fast | `meterless/fast` | `auto` (coerced) | `nvidia/nemotron-3.5-lightning-30b-a3b` | `rcpt_req_924f14pn` | 5728 ms |
| deep | `meterless/deep` | `auto` (coerced) | `nvidia/nemotron-3.5-super-vl-120b-a12b` | `rcpt_req_p412l7ql` | 615 ms |

**Lane deviation, stated plainly.** The deep lane was designed for Nemotron 3 Super. That model, `nvidia/nemotron-3-super-120b-a12b`, returns HTTP 404 on this NVIDIA account (not entitled), so the deep lane is bound to `nvidia/nemotron-3.5-super-vl-120b-a12b`. Separately, Nightshift's Default app rule coerces both lanes to `auto`, which picks the model per request, so lane separation is not guaranteed: in the live runs most calls on both lanes were served by Super VL. Meterless acknowledged the routing bug on 24 October 2026, with a fix targeted for its Sunday release. Every receipt records it (`app_policy.mode_coerced: True`). Human observations: `docs/evidence/nightshift_deviations.md`.

### H-MEM

`app/memory/hmem/` is the Python port of Meterless H-MEM, checked against the 13 upstream vectors in `tests/conformance/test_hmem_conformance.py`. `app/memory/precedents.py` adapts it to governed precedents. The live memory session (`docs/evidence/memory_session.md`, 6/6 steps) shows a lead-approved precedent, P-0001 from Marrowgate (VND-0011), letting the policy move Tessellate (VND-0012) to `APPROVE_WITH_CONDITIONS`. With memory reset, an analyst-role precedent, or `wrong` feedback, the same vendor escalates. The policy engine applies the exception, never a model:

```jsonl
{"timestamp":"2026-10-24T04:49:50.590441Z","run_id":"run-a1c914808974","trace_id":"run-a1c914808974","span_id":"af57aa480da94587","parent_span_id":null,"agent_name":"Orchestrator","action":"memory_check","input_summary":"failing=C05","output_summary":"candidates=1","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"auto"}}
{"timestamp":"2026-10-24T04:49:50.593255Z","run_id":"run-a1c914808974","trace_id":"run-a1c914808974","span_id":"4794b1671da3457c","parent_span_id":null,"agent_name":"MemoryKeeper","action":"precedent_applied","input_summary":"P-0001","output_summary":"ok","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"auto"}}
```

### Scout (guard and execution contracts subset)

`app/guard/scout_guard.py` screens every vendor answer and document before a model sees it; the adversarial cases are `tests/conformance/test_scout_adversarial.py`. In the live run each of the 16 segments passed:

```jsonl
{"timestamp":"2026-10-24T04:41:36.414432Z","run_id":"run-83de5da137c0","trace_id":"run-83de5da137c0","span_id":"2561938c32e24646","parent_span_id":null,"agent_name":"ScoutGuard","action":"guard_segment","input_summary":"segment_id=ans-Q01 len=34","output_summary":"level=pass score=0.000","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
```

In the offline sample Oakhaven (`run-ac35d0a215a4`) a planted instruction in a document is blocked, and the case escalates:

```jsonl
{"timestamp":"2026-10-23T01:03:18.097380Z","run_id":"run-ac35d0a215a4","trace_id":"run-ac35d0a215a4","span_id":"ef084c66f9384acb","parent_span_id":null,"agent_name":"ScoutGuard","action":"guard_segment","input_summary":"segment_id=doc-DOC-0015-0 len=81","output_summary":"level=block score=0.920","target_agent":null,"confidence":null,"retry_count":0,"status":"blocked","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"duckdb","llm":"offline"}}
```

Actions are HMAC-signed execution contracts (`app/actions/contracts.py`, `app/actions/executor.py`). The live run's approval was written to the outbox only after its contract verified:

```jsonl
{"timestamp":"2026-10-24T04:43:58.997247Z","run_id":"run-83de5da137c0","trace_id":"run-83de5da137c0","span_id":"caae5cb7aa4d44e3","parent_span_id":null,"agent_name":"ActionExecutor","action":"execute_action","input_summary":"contract=ctr-2326d46143bf intent=vendor.onboarding.approve","output_summary":"executed: ok → var/outbox/procurement/ctr-2326d46143bf.json","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
```

## NVIDIA: Our agents do real work on Nemotron

Every LLM step in live example 1, with its lane, the model Nightshift served and the receipt. The quoted lines follow the table.

| Step | Agent | Lane requested | Model served | Receipt | Result |
|---|---|---|---|---|---|
| plan | PlannerAgent | deep | `nvidia/nemotron-3.5-super-vl-120b-a12b` | `rcpt_req_ltd0d684` | 7-query plan (`PlanOut`) |
| extract | EvidenceAgent | fast | `nvidia/nemotron-3.5-super-vl-120b-a12b` | `rcpt_req_y39h16ui` | 16 quoted claims from 15 answers |
| critique | EvaluatorAgent | fast | `nvidia/nemotron-3.5-super-vl-120b-a12b` | `rcpt_req_rfbsdjpm` | Critique; Evaluator sends the Planner back for C06, C09 |
| plan (revise) | PlannerAgent | deep | `nvidia/nemotron-3.5-super-vl-120b-a12b` | `rcpt_req_cdh75z4f` | 2 follow-up queries |
| challenge | ChallengerAgent | deep | `nvidia/nemotron-3.5-super-vl-120b-a12b` | `rcpt_req_7r1o2wvc` | Re-plan request (uncorroborated claim) |
| plan (after challenge) | PlannerAgent | deep | none: HTTP 502 empty response from Nightshift | – | Deterministic fallback, labelled `fallback` |
| brief | ReporterAgent | – | not a model call | – | Deterministic template by design (P14-A), so every brief sentence is checkable |

Planning on Nemotron, with its receipt:

```jsonl
{"timestamp":"2026-10-24T04:41:35.414838Z","run_id":"run-83de5da137c0","trace_id":"run-83de5da137c0","span_id":"b644cd34198c4a27","parent_span_id":null,"agent_name":"PlannerAgent","action":"model_call","input_summary":"purpose=plan route=deep response=json attempt=1 prompt_chars=4985","output_summary":"json valid (PlanOut)","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":"meterless","route":"deep","model":"nvidia/nemotron-3.5-super-vl-120b-a12b","latency_ms":14180,"tokens_in":3368,"tokens_out":3148,"purpose":"plan","provider_meta":{"requested_model":"meterless/deep","response_id":"chatcmpl-02a396e9-0707-4dab-bfd1-542a5ae7ff5a","schema":"meterless.compute_receipt.v1","receipt_id":"rcpt_req_ltd0d684","decision_id":"req_ltd0d684","provider_model":"meterless/auto","routed_model":"nvidia/nemotron-3.5-super-vl-120b-a12b","mode":"auto","requires_review":"False","winning_route.provider":"nvidia","winning_route.label":"Nemotron 3.5 Super VL 120B A12B","winning_route.kind":"cloud","winning_route.tier":"C","winning_route.model":"nvidia/nemotron-3.5-super-vl-120b-a12b","app_policy.app":"arbiter","app_policy.has_rule":"True","app_policy.bound_mode":"auto","app_policy.requested_mode":"deep","app_policy.routed_mode":"auto","app_policy.mode_coerced":"True","app_policy.privacy":"cloud-ok","cost.actual_usd":"0","cost.naive_usd":"0","cost.race_overhead_usd":"0","cost.verifier_usd":"0","cost.baseline.model":"nvidia/nemotron-3.5-super-vl-120b-a12b","cost.baseline.label":"Nemotron 3.5 Super VL 120B A12B","cost.baseline.source":"mode-default-frontier","savings.amount":"0","savings.currency":"USD","savings.vs":"Nemotron 3.5 Super VL 120B A12B","savings.baseline_source":"mode-default-frontier","no_think":"true"},"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
```

Claim extraction from untrusted vendor answers (after ScoutGuard):

```jsonl
{"timestamp":"2026-10-24T04:42:23.525566Z","run_id":"run-83de5da137c0","trace_id":"run-83de5da137c0","span_id":"88b6ca1f4c7e475b","parent_span_id":null,"agent_name":"EvidenceAgent","action":"model_call","input_summary":"purpose=extract route=fast response=json attempt=1 prompt_chars=2923","output_summary":"json valid (ClaimListOut)","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":"meterless","route":"fast","model":"nvidia/nemotron-3.5-super-vl-120b-a12b","latency_ms":41203,"tokens_in":1840,"tokens_out":1988,"purpose":"extract","provider_meta":{"requested_model":"meterless/fast","response_id":"chatcmpl-82cb08ef-d269-40bf-9683-1b9113c901c0","schema":"meterless.compute_receipt.v1","receipt_id":"rcpt_req_y39h16ui","decision_id":"req_y39h16ui","provider_model":"meterless/auto","routed_model":"nvidia/nemotron-3.5-super-vl-120b-a12b","mode":"auto","requires_review":"False","winning_route.provider":"nvidia","winning_route.label":"Nemotron 3.5 Super VL 120B A12B","winning_route.kind":"cloud","winning_route.tier":"C","winning_route.model":"nvidia/nemotron-3.5-super-vl-120b-a12b","app_policy.app":"arbiter","app_policy.has_rule":"True","app_policy.bound_mode":"auto","app_policy.requested_mode":"fast","app_policy.routed_mode":"auto","app_policy.mode_coerced":"True","app_policy.privacy":"cloud-ok","cost.actual_usd":"0","cost.naive_usd":"0","cost.race_overhead_usd":"0","cost.verifier_usd":"0","cost.baseline.model":"nvidia/nemotron-3.5-super-vl-120b-a12b","cost.baseline.label":"Nemotron 3.5 Super VL 120B A12B","cost.baseline.source":"mode-default-frontier","savings.amount":"0","savings.currency":"USD","savings.vs":"Nemotron 3.5 Super VL 120B A12B","savings.baseline_source":"mode-default-frontier","no_think":"true"},"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
```

Critique, then the Evaluator sends work back:

```jsonl
{"timestamp":"2026-10-24T04:42:44.295663Z","run_id":"run-83de5da137c0","trace_id":"run-83de5da137c0","span_id":"2731ae25cfeb47d4","parent_span_id":null,"agent_name":"EvaluatorAgent","action":"model_call","input_summary":"purpose=critique route=fast response=json attempt=1 prompt_chars=3380","output_summary":"json valid (CritiqueOut)","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":"meterless","route":"fast","model":"nvidia/nemotron-3.5-super-vl-120b-a12b","latency_ms":20745,"tokens_in":2645,"tokens_out":1309,"purpose":"critique","provider_meta":{"requested_model":"meterless/fast","response_id":"chatcmpl-c921211f-0aa5-4984-9dec-65a65d0bb9a8","schema":"meterless.compute_receipt.v1","receipt_id":"rcpt_req_rfbsdjpm","decision_id":"req_rfbsdjpm","provider_model":"meterless/auto","routed_model":"nvidia/nemotron-3.5-super-vl-120b-a12b","mode":"auto","requires_review":"False","winning_route.provider":"nvidia","winning_route.label":"Nemotron 3.5 Super VL 120B A12B","winning_route.kind":"cloud","winning_route.tier":"C","winning_route.model":"nvidia/nemotron-3.5-super-vl-120b-a12b","app_policy.app":"arbiter","app_policy.has_rule":"True","app_policy.bound_mode":"auto","app_policy.requested_mode":"fast","app_policy.routed_mode":"auto","app_policy.mode_coerced":"True","app_policy.privacy":"cloud-ok","cost.actual_usd":"0","cost.naive_usd":"0","cost.race_overhead_usd":"0","cost.verifier_usd":"0","cost.baseline.model":"nvidia/nemotron-3.5-super-vl-120b-a12b","cost.baseline.label":"Nemotron 3.5 Super VL 120B A12B","cost.baseline.source":"mode-default-frontier","savings.amount":"0","savings.currency":"USD","savings.vs":"Nemotron 3.5 Super VL 120B A12B","savings.baseline_source":"mode-default-frontier","no_think":"true"},"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
{"timestamp":"2026-10-24T04:42:44.302557Z","run_id":"run-83de5da137c0","trace_id":"run-83de5da137c0","span_id":"070a17b8d08d4146","parent_span_id":null,"agent_name":"EvaluatorAgent","action":"evaluate","input_summary":"claims=16 queries=8","output_summary":"gaps: C06→Q_VENDOR_INCIDENTS; C09→Q_VENDOR_CONTRACT","target_agent":"PlannerAgent","confidence":null,"retry_count":0,"status":"needs_revision","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":1,"mode":{"data":"zetaris","llm":"meterless"}}
```

The Challenger attacks the candidate `APPROVE`, and can only re-plan or escalate:

```jsonl
{"timestamp":"2026-10-24T04:43:24.291804Z","run_id":"run-83de5da137c0","trace_id":"run-83de5da137c0","span_id":"fc0d935e07014bf6","parent_span_id":null,"agent_name":"ChallengerAgent","action":"model_call","input_summary":"purpose=challenge route=deep response=json attempt=1 prompt_chars=7771","output_summary":"json valid (ChallengeOut)","target_agent":null,"confidence":null,"retry_count":0,"status":"success","provider":"meterless","route":"deep","model":"nvidia/nemotron-3.5-super-vl-120b-a12b","latency_ms":23444,"tokens_in":2750,"tokens_out":1081,"purpose":"challenge","provider_meta":{"requested_model":"meterless/deep","response_id":"chatcmpl-a0416d01-d9ba-47e4-a778-7e52ee698517","schema":"meterless.compute_receipt.v1","receipt_id":"rcpt_req_7r1o2wvc","decision_id":"req_7r1o2wvc","provider_model":"meterless/auto","routed_model":"nvidia/nemotron-3.5-super-vl-120b-a12b","mode":"auto","requires_review":"False","winning_route.provider":"nvidia","winning_route.label":"Nemotron 3.5 Super VL 120B A12B","winning_route.kind":"cloud","winning_route.tier":"C","winning_route.model":"nvidia/nemotron-3.5-super-vl-120b-a12b","app_policy.app":"arbiter","app_policy.has_rule":"True","app_policy.bound_mode":"auto","app_policy.requested_mode":"deep","app_policy.routed_mode":"auto","app_policy.mode_coerced":"True","app_policy.privacy":"cloud-ok","cost.actual_usd":"0","cost.naive_usd":"0","cost.race_overhead_usd":"0","cost.verifier_usd":"0","cost.baseline.model":"nvidia/nemotron-3.5-super-vl-120b-a12b","cost.baseline.label":"Nemotron 3.5 Super VL 120B A12B","cost.baseline.source":"mode-default-frontier","savings.amount":"0","savings.currency":"USD","savings.vs":"Nemotron 3.5 Super VL 120B A12B","savings.baseline_source":"mode-default-frontier","no_think":"true"},"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
{"timestamp":"2026-10-24T04:43:24.292293Z","run_id":"run-83de5da137c0","trace_id":"run-83de5da137c0","span_id":"043fc690db06493c","parent_span_id":null,"agent_name":"ChallengerAgent","action":"request_replan","input_summary":"outcome=APPROVE loops_left=1","output_summary":"re_plan CHALLENGE_UNCORROBORATED_CLAIM source=llm","target_agent":"PlannerAgent","confidence":null,"retry_count":0,"status":"success","provider":null,"route":null,"model":null,"latency_ms":null,"tokens_in":null,"tokens_out":null,"purpose":null,"provider_meta":null,"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
```

The one failed call, which the trace labels honestly:

```jsonl
{"timestamp":"2026-10-24T04:43:53.808317Z","run_id":"run-83de5da137c0","trace_id":"run-83de5da137c0","span_id":"4e753849e22a4972","parent_span_id":null,"agent_name":"PlannerAgent","action":"model_call","input_summary":"purpose=plan route=deep response=json attempt=1 prompt_chars=5617","output_summary":"UpstreamError: meterless HTTP 502: provider_error api_error nvidia/nemotron-3.5-lightning-30b-a3b_empty_response","target_agent":null,"confidence":null,"retry_count":0,"status":"fallback","provider":"meterless","route":"deep","model":null,"latency_ms":29435,"tokens_in":null,"tokens_out":null,"purpose":"plan","provider_meta":{"requested_model":"meterless/deep"},"source_system":null,"query_id":null,"rows":null,"backend":null,"loop":null,"iteration":null,"mode":{"data":"zetaris","llm":"meterless"}}
```

Across the live evaluation, 20 of 25 model calls succeeded: 19 served by Super VL and 1 deep-lane plan served by `nvidia/nemotron-3.5-lightning-30b-a3b` (`rcpt_req_szjmqbge`, `eval/results_live/20261024T045916036274Z/traces/trace-run-f59a50433bf5.jsonl`). The 5 failures were HTTP 502s and fell back to deterministic logic (`docs/EVALUATION.md`). `app/llm/providers/nvidia.py` is the build.nvidia.com fallback; no committed run used it.

## Cursor

Arbiter was built pass by pass from `AGENTS.md`, under five project rules (`.cursor/rules/`), four commands (`.cursor/commands/`, including `/start-pass` and `/verify-pass`) and a stop hook (`.cursor/hooks.json`) that re-runs `python scripts/tasks.py verify-pass` and feeds failures back, up to six times. Each pass has a plan in `.cursor/plans/` (24 files), a gate in `scripts/gates/`, a report in `docs/passes/` and a usage note in `docs/cursor-usage/`, compiled into `docs/CURSOR_USAGE.md`. Parallel lanes ran in separate worktrees (`.cursor/worktrees.json`).

Of the 21 pass notes, 17 record Cursor (Composer, Grok 4.7 and Claude Opus as the agent model), one names its model without the tool, and three (P14-B, P15 and P17) were done in Claude Code; see the table in `docs/CURSOR_USAGE.md`.
