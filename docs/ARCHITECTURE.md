# Architecture

Arbiter is a state machine. Models plan, extract, criticise, and write. `app/policy/engine.py` is the only place an outcome is chosen.

## Layers

```mermaid
flowchart TB
  subgraph data [Data]
    sim["sources/ simulator :8100"]
    kev[CISA KEV snapshot]
    zet["Zetaris REST or DuckDB mirror"]
    reg["app/data/queries.yaml"]
  end
  subgraph build [Build]
    orch["app/orchestrator.py"]
    agents["Planner, Evidence, Evaluator, Challenger, Reporter"]
    policy["app/policy/engine.py"]
    guard["app/guard/scout_guard.py"]
    mem["app/memory/"]
    act["app/actions/"]
  end
  subgraph power [Power]
    gen["app/llm/generator.py"]
    ns["Meterless Nightshift"]
    nv["NVIDIA direct"]
    off["offline fallback"]
  end
  sim --> zet
  kev --> zet
  zet --> reg --> agents
  gen --> ns
  gen --> nv
  gen --> off
  gen --> agents
  agents --> orch
  orch --> policy
  guard --> agents
  mem --> orch
  policy --> act
```

Sample mode (`SAMPLE_MODE=true`) swaps the Zetaris client for the DuckDB mirror. Query ids and columns stay the same. See `app/data/factory.py`.

## State machine

Loops are the two edges back to `PLAN`. The Evaluator may take that edge at most twice. The Challenger may take it once.

```mermaid
stateDiagram-v2
  [*] --> INTAKE
  INTAKE --> PLAN
  PLAN --> GATHER
  GATHER --> EVALUATE
  EVALUATE --> PLAN: needs_revision and eval_loops less than 2
  EVALUATE --> DECIDE_1: sufficient or loops exhausted
  DECIDE_1 --> MEMORY_CHECK
  MEMORY_CHECK --> DECIDE_2
  DECIDE_2 --> CHALLENGE
  CHALLENGE --> PLAN: re_plan and challenge_loops less than 1
  CHALLENGE --> REPORT: escalate or accept
  REPORT --> CONTRACT
  CONTRACT --> EXECUTE
  EXECUTE --> DONE
  INTAKE --> SAFE_ESCALATE: budget or unrecoverable error
  PLAN --> SAFE_ESCALATE: budget or unrecoverable error
  GATHER --> SAFE_ESCALATE: budget or unrecoverable error
  EVALUATE --> SAFE_ESCALATE: budget or unrecoverable error
  SAFE_ESCALATE --> REPORT
```

`DECIDE_2` is the same policy function as `DECIDE_1`, with precedent candidates added. An escalate from the Challenger sets the outcome to the worse of the policy outcome and `ESCALATE`, so a `DECLINE` stays a `DECLINE`. The run budget is 600 seconds.

## Agent authority

Who is allowed to stop a line of work, or to make the Planner run again:

```mermaid
flowchart TD
  planner[PlannerAgent]
  evidence[EvidenceAgent]
  evaluator[EvaluatorAgent]
  policy[PolicyEngine]
  challenger[ChallengerAgent]
  scout[ScoutGuard]
  executor[ActionExecutor]
  evaluator -->|"needs_revision, at most twice"| planner
  challenger -->|"one re-plan, or escalate"| planner
  scout -->|"block a segment"| evaluator
  policy -->|"outcome"| challenger
  executor -->|"wait until approvals exist"| executor
```

The Planner cannot write SQL. The Evidence agent cannot mark a claim verified. The Challenger cannot approve. The policy engine does not call a model. The table in the README is the same contract.

## Data path

Registry queries are the only data path agents use. There is no connector inside an agent.

```mermaid
flowchart LR
  sim["Simulator REST :8100"]
  kev["CISA KEV JSON"]
  rest["Zetaris Lightning REST tables"]
  views["SchemaStore views"]
  usl["USL vendor_risk in lightning.metastore.arbiter"]
  reg["queries.yaml ids"]
  agent["EvidenceAgent"]
  sim --> rest
  kev --> rest
  rest --> views --> usl --> reg --> agent
```

`Q_COMPONENT_KEV` joins declared components to the KEV table. In sample mode the backend field on that event is `duckdb`. The SQL for the live model is `zetaris/sql/03_usl.sql`. Data-quality rules live in `zetaris/dq_rules.yaml` and surface as `Q_DQ_INVALID`.

## Model lanes

Agents ask `app/llm/generator.py` for a route, not a model. Planner, Challenger and Reporter use `deep`; Evidence and the Evaluator critic use `fast`. The Meterless provider sends `meterless/deep` or `meterless/fast`, and Nightshift chooses the Nemotron model and returns a receipt that the trace keeps in `provider_meta`.

In the committed live evidence the models served were `nvidia/nemotron-3.5-super-vl-120b-a12b` and `nvidia/nemotron-3.5-lightning-30b-a3b` (`docs/evidence/nightshift_proof.json`). A Nightshift app rule currently coerces both lanes to `auto`, so the lane does not fix the model; see `docs/evidence/nightshift_deviations.md`. If Nightshift is unreachable, resolution tries NVIDIA direct (`app/llm/providers/nvidia.py`) and then the offline generator.

## Memory governance

Examples in this repo are generated with `ARBITER_MEMORY=off`, so a sample trace shows `precedents=0`. The path is still the one below. A precedent changes a later outcome only through the policy's precedent-exception clause, and only after the required human role approves.

```mermaid
flowchart TD
  review["POST /cases/id/review"]
  elig["precedents.check_eligibility"]
  hmem["H-MEM record and trust ledger"]
  later["Later case MEMORY_CHECK"]
  decide["DECIDE_2 same policy function"]
  review --> elig
  elig -->|"create_precedent and eligible"| hmem
  hmem --> later --> decide
```

Retrieval does not decide. Feedback (`helpful` or `wrong`) is written back to the ledger. The conformance vectors for the port are `tests/conformance/test_hmem_conformance.py`.

## Contract signing and verification

```mermaid
flowchart TD
  draft["Reporter drafts an action"]
  sign["HMAC-SHA256 over canonical JSON"]
  store["Store the contract"]
  approve["POST /contracts/id/approve"]
  verify["Verify signature, expiry, approvals"]
  outbox["Write the outbox file"]
  draft --> sign --> store
  store --> approve --> verify --> outbox
```

The signature covers the contract without the signature field (`app/actions/contracts.py`). A child contract is issued when an approval is added. The executor refuses a missing, expired, or under-approved contract. Replay (`app/audit/replay.py`) runs the policy again and checks the policy hash, the record hash, and the contract signatures.
