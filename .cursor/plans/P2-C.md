# P2-C policy engine plan

## Goal

Transcribe `docs/spec/02_POLICY.md` §3 into `policy/arbiter_policy.v1.yaml`, load it into a typed policy whose canonical hash changes when any rule changes, and implement tiering, the tri-state DSL, the ordered outcome procedure, contract-stage conditions, the six precedent-exception criteria, counterfactuals, and residual risk as pure functions. `decide` is the only place facts become an outcome. No model calls, no data access, and no wall clock.

## Branch

`p2c-policy` (pass index). Lane id `2c`, marker `p2c`. Active pass is `2c plan` until this plan is approved.

## Defaults I will use unless you say otherwise

1. **Residual risk** = `tier_base[tier]` + `per_false_weight * Σ weight` of required controls in FALSE + `per_unknown_weight * Σ weight` of required controls in UNKNOWN + `per_material_contradiction *` unresolved material contradictions + `injection` if any guard flag has level `block`, then `min(score, cap)`. Conditionally TRUE controls add nothing. A non-required control adds nothing.
2. **`applies_when` UNKNOWN** keeps the control applicable and required (a missing data-category fact must not drop C08). FALSE means the control is omitted. TRUE means it applies.
3. **Precedent `mitigation`** must equal the policy `mitigation_fact` key (`assurance.bridge_letter_current`). Age is `inputs.as_of - created_as_of` in days. A case may use a precedent only when the case is no riskier: rank T1 > T2 > T3.
4. **Counterfactuals** include every required control that is not TRUE (conditionally TRUE does not count) plus every unresolved contradiction, material or minor. Contradiction rows use `evidence_required=["resolve contradiction on <key>"]` and the control's `question_ids`.
5. **`failed_criteria` codes** (stable, listed below). A candidate is applied only when the list is empty.

## Files

All paths are inside P2-C ownership (`docs/spec/passes/README.md` §3: `policy/**`, `app/policy/**`, `tests/unit/policy/**`, this lane's gate, and the two finish docs). No exceptions.

`ControlResult.conditional` and `condition_text` are already on `app/schemas/decision.py`. No schema edit. Approvals stay a pure function over the policy block (master spec §8.7); they are not a new `DecisionRecord` field. Loader failures raise the existing `PolicyError`.

| File | Action |
|---|---|
| `policy/arbiter_policy.v1.yaml` | Create. 02 §3 verbatim |
| `policy/calibration/cal-initial.json` | Create. Version, gates, and weights from the pass deliverable |
| `policy/calibration/ACTIVE` | Create. Text `cal-initial` |
| `app/policy/loader.py` | Typed `Policy` / `Calibration`, validation, `policy_sha256` |
| `app/policy/dsl.py` | `evaluate` with no `eval` |
| `app/policy/tiering.py` | Inherent score and tier assignment |
| `app/policy/engine.py` | `decide`, predicates, conditions, exceptions, `worse_of`, `force_escalate`, `required_approvals` |
| `app/policy/counterfactuals.py` | Counterfactuals and fragile-control ids |
| `app/policy/residual.py` | Residual score |
| `app/policy/__init__.py` | `load_default()` |
| `scripts/gates/p2c.py` | This lane's gate: `load_default()` yields 12 controls C01–C12 and calibration `cal-initial` |
| `tests/unit/policy/test_dsl_controls.py` | P2-T30 |
| `tests/unit/policy/test_outcomes.py` | P2-T31, P2-T32 |
| `tests/unit/policy/test_precedent.py` | P2-T33 |
| `tests/unit/policy/test_counterfactuals.py` | P2-T34 |
| `tests/unit/policy/test_monotonicity.py` | P2-T35 |
| `tests/unit/policy/test_determinism.py` | P2-T36 |
| `tests/unit/policy/test_tiering.py` | P2-T37 |
| `tests/unit/policy/test_loader.py` | P2-T38 |
| `docs/passes/P2-C_REPORT.md` | Finish only. Includes the S01–S14 decision table |
| `docs/cursor-usage/P2-C.md` | Finish only |

Not touched: `app/schemas/**`, `app/errors.py`, `app/canon.py`, agents, eval labels, `data/evals/`. The S01–S14 table is produced by calling `decide` on minimal fact sets and written only in the report. The engine will not branch on scenario or vendor ids.

## Interfaces

```python
def evaluate(rule: Mapping[str, Any], facts: dict[str, Fact]) -> TriState: ...

def tier(profile: TierProfile, policy: Policy) -> tuple[Tier, int]: ...

def decide(inputs: PolicyInputs, policy: Policy, calibration: Calibration) -> DecisionRecord: ...

def force_escalate(record: DecisionRecord, reason: str) -> DecisionRecord: ...

def worse_of(current: Outcome, proposed: Outcome) -> Outcome: ...

def required_approvals(record: DecisionRecord, policy: Policy) -> list[str]: ...

def compute_counterfactuals(
    controls: list[ControlResult],
    contradictions: list[Contradiction],
    policy: Policy,
) -> list[Counterfactual]: ...

def fragile_controls(controls: list[ControlResult], facts: list[Fact]) -> list[str]: ...

def residual_risk(
    tier: Tier, controls: list[ControlResult], inputs: PolicyInputs, policy: Policy
) -> int: ...

def load_default() -> tuple[Policy, Calibration]: ...
```

`Calibration.gate(tier) -> float`. `policy_sha256` is `sha256_hex` of the parsed policy (`app.canon`). `record_sha256` hashes the decision record with `record_sha256` excluded. `created_at` is `inputs.as_of` at 00:00 UTC. Collections on the record are sorted (facts by `fact_id`, precedents by `precedent_id`, controls in policy order) so dict and list order cannot change the hash. `decide` does not mutate its inputs. Confidence on the record gets `gate` from calibration and `abstained=True` exactly when `confidence_below_gate` matches.

### DSL

Leaf form `{fact, op, value}`. Missing fact, `state == UNKNOWN`, or a comparison with no value returns UNKNOWN. UNKNOWN never counts as a pass.

| Op | TRUE when the fact is known and |
|---|---|
| `is_true` / `is_false` | `state` is TRUE / FALSE (FALSE state makes `is_true` return FALSE) |
| `eq` `ne` `lt` `lte` `gt` `gte` | value compares; numbers compare numerically (`90` and `90.0` match) |
| `in` / `not_in` | scalar value is / is not in the value list |
| `in_any` | list value intersects the value list (empty list is FALSE) |
| `subset_of` | every item of the list value is in the value list (empty list is TRUE) |
| `exists` | fact is present and not UNKNOWN |

`all`: TRUE if every child is TRUE; FALSE if any child is FALSE; otherwise UNKNOWN. `any`: TRUE if any child is TRUE; FALSE if every child is FALSE; otherwise UNKNOWN.

### Named predicates

Evaluated in YAML order. First match sets the outcome. `outcome_reasons` lists every match.

| Predicate | True when |
|---|---|
| `hard_gate_decline_false` | An applicable control with `hard_gate: decline` is FALSE |
| `injection_blocked` | Any guard flag has level `block` |
| `unresolved_material_contradiction` | Any contradiction has `severity=material` and `resolved=false` |
| `hard_gate_escalate_false` | An applicable control with `hard_gate: escalate` is FALSE and `conditional` is false |
| `required_false_without_exception` | Any required control is FALSE and `exception_applied` is empty |
| `required_unknown` | Any required control is UNKNOWN and `conditional` is false |
| `confidence_below_gate` | `confidence.value < calibration.gate(tier)` |
| `any_conditional` | Any control is TRUE with `conditional=true` |
| `always` | Always |

### Tiering

`inherent = 2 * sensitivity + criticality + spend` using the policy tables. Sensitivity is the max category score. Spend uses the first band with `lt` above the amount, else the `lt: null` band. T1 if `inherent >= 6` or any category is `special_category`. Else T2 if `inherent >= 3`. Else T3. `special_category` scores 3, so a real profile that includes it already has inherent ≥ 6. The override is still implemented, and T37 calls the assignment helper with inherent 5 plus `special_category` to show the category rule is not only the score.

### Contract-stage conditions and approvals

After the rule result, if the control is not TRUE, `profile.contract_status` is in `when_contract_status_in`, and `claim_fact` satisfies `claim_rule`, set state TRUE, `conditional=true`, and `condition_text` to the policy sentence. C07 and C08 both name `tprm_analyst`.

`required_approvals` reads `policy.approvals` only:

- APPROVE → the list for that tier
- APPROVE_WITH_CONDITIONS → `precedent_exception` when any control has `exception_applied`, otherwise `contract_stage_only`
- REQUEST_INFO and ESCALATE → `[]`
- DECLINE → the DECLINE list

Role rank is `policy.roles`. A higher rank satisfies a lower requirement. The function returns the policy's role list for the matching key (T32 expects `["tprm_analyst"]`).

### Precedent exceptions

Consider a candidate only for its `control_id`. Apply the first qualifying candidate in `(relevance, hmem_confidence, precedent_id)` order. Effect: state TRUE, `conditional=true`, `exception_applied=precedent_id`, `condition_text` from the policy. Every candidate is copied into `precedents_considered`.

| Code | Criterion fails when |
|---|---|
| `exception_not_allowed` | Control has no `precedent_exception.allowed` |
| `mitigation_fact` | Mitigation fact is missing or not TRUE |
| `reviewer_authority` | Role rank is below `approver_role`, decision is not APPROVE or APPROVE_WITH_CONDITIONS, control id differs, or mitigation string differs |
| `precedent_age` | Age in days is greater than `max_precedent_age_days` |
| `retrieval_quality` | `hmem_confidence < 0.70` or `relevance < 0.35` |
| `tier_risk` | Case tier is riskier than the precedent tier |

### Counterfactuals and residual

Control row: `from_state` is the control state, `to_state` is TRUE, `evidence_required` and `question_ids` come from the policy. Fragile controls (returned separately, not stored on `DecisionRecord`): required, TRUE, not conditional, every supporting fact's provenance is only `vendor_answer` or `vendor_document`, and `derived_from_claims` has exactly one id. P3's reporter owns `Report.limitations`.

`force_escalate` returns a copy with `outcome = worse_of(outcome, ESCALATE)` and `reason` appended to `escalation_reasons`, then recomputes `record_sha256`. Rank from best to worst: APPROVE, APPROVE_WITH_CONDITIONS, REQUEST_INFO, ESCALATE, DECLINE. DECLINE stays DECLINE.

## Acceptance tests

Marker `@pytest.mark.p2c`. Each test name or docstring carries its id. Written first and committed as `test(p2c): acceptance tests` while the stubs still fail. Fixed seed `20261022` for T35; the assertion message includes the seed and the failing pair.

| Id | How |
|---|---|
| P2-T30 | Table of ≥ 3 fact sets per C01–C12 (pass, fail, and missing/UNKNOWN), including C05 `any`, C09 `subset_of` / `in`, and C11 `eq` |
| P2-T31 | One fixture per rule O1–O9 where that rule is the first match, plus stacked cases: sanctions FALSE beats a block flag; a block flag beats a material contradiction; a material contradiction beats C08 FALSE; C08 FALSE beats an ordinary FALSE; an ordinary FALSE beats UNKNOWN; UNKNOWN beats low confidence; low confidence beats a conditional TRUE; conditional TRUE beats a clean approve |
| P2-T32 | Draft contract, personal data, C07 claim ≤ 72 and C08 `dpa.vendor_commits` TRUE, every other required control TRUE → APPROVE_WITH_CONDITIONS, both condition sentences, `required_approvals` == `["tprm_analyst"]` |
| P2-T33 | One C05 candidate that meets all six criteria is applied. Six copies, each breaking one criterion, are not applied, and `failed_criteria` contains that criterion's code |
| P2-T34 | Required FALSE and UNKNOWN controls appear once with the policy's evidence and question ids; conditionally TRUE controls do not; each unresolved contradiction adds one `resolve contradiction on <key>` row; a resolved contradiction does not |
| P2-T35 | Seeded loop, 2,000 trials. Property 1: confidence at or above the gate, no contradictions, no guard flags; degrading one control TRUE→UNKNOWN or UNKNOWN→FALSE never improves rank. Property 2: at any confidence, the same degradation never enters APPROVE or APPROVE_WITH_CONDITIONS from outside them, and never turns APPROVE_WITH_CONDITIONS into APPROVE |
| P2-T36 | Same inputs, shuffled fact and mapping order, equal `record_sha256`. `created_at` is `as_of` 00:00 UTC. A case that matches more than one rule lists those reason codes in YAML order. `force_escalate` on DECLINE stays DECLINE and still records the reason |
| P2-T37 | Profiles with inherent 2 → T3, 3 → T2, 5 → T2, 6 → T1. `special_category` at low criticality and £0 spend is T1 with inherent 6. Assignment helper: inherent 5 and `special_category` is T1; inherent 5 and `personal` is T2 |
| P2-T38 | Loader raises `PolicyError` naming the fault for an unknown op, a fact key outside `FACT_KEYS`, a duplicate control id, and an unknown outcome predicate. Changing one rule's value changes `policy_sha256` |

## Verification

`python scripts/tasks.py verify-pass --pass 2c` (lint, `p2c` tests, full non-live regression, gate, secret scan, hardcode check). This worktree's existing tests are P0 only, so regression should stay green.

## Risks

- Residual weights and the UNKNOWN applicability rule are interpretations. The defaults above are what I will code on approval.
- `engine.py` must stay under about 400 lines. Predicates and exception checks move into functions in that module first; a sibling module under `app/policy/` only if the file will not fit.
- T35 builds control states through facts so it exercises `decide`, not a second outcome table.
- The report's S01–S14 table is a sanity check against 01 §4. It is not an acceptance test and it does not read `data/evals/`.

## Questions

Approval can be "go with the defaults". The five defaults at the top are the only choices I would not want to guess past in silence.
