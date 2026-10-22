# P2-C policy engine report

## Built

Deterministic policy engine. The YAML in `docs/spec/02_POLICY.md` §3 is `policy/arbiter_policy.v1.yaml`. `policy/calibration/cal-initial.json` and `policy/calibration/ACTIVE` hold the initial gates (T1 0.90, T2 0.85, T3 0.80).

`app/policy/` loads that file into a typed policy, hashes the parsed document, and evaluates it with pure functions: tri-state DSL (no `eval`), tiering, ordered outcome rules, contract-stage conditions, the six precedent-exception criteria, counterfactuals, and residual risk. `decide` is the only function that turns facts into an outcome. `force_escalate` can only move a result toward ESCALATE, and a DECLINE stays a DECLINE.

Acceptance tests P2-T30 through P2-T38 are in `tests/unit/policy/`, marker `p2c`. `scripts/gates/p2c.py` checks that the default policy loads twelve controls and calibration `cal-initial`.

## Deviations

None that change the spec. The approved plan fixed five readings:

- Residual risk multiplies a failing control's own weight by `per_false_weight` (6) or `per_unknown_weight` (3), then adds contradiction and injection penalties, capped at 100. Conditionally TRUE controls add nothing.
- If `applies_when` is UNKNOWN, the control stays required. FALSE omits it.
- A precedent's `mitigation` string must equal the fact key `assurance.bridge_letter_current`.
- Counterfactuals list every required control that is not TRUE, plus every unresolved contradiction (material or minor).
- Rejected precedents use `exception_not_allowed`, `mitigation_fact`, `reviewer_authority`, `precedent_age`, `retrieval_quality`, and `tier_risk`.

`ControlResult.conditional` and `condition_text` were already on the P0 schema, so this lane did not edit `app/schemas/`. Required approvals are `required_approvals(record, policy)`, read from the policy block. Fragile controls are `fragile_controls(...)` for the P3 reporter; they are not a field on `DecisionRecord`.

`special_category` already scores inherent 6. The category override is still implemented, and P2-T37 checks it by assigning tier to inherent 5 with that category.

## Known gaps

- This lane does not derive facts. SOC currency, incident counts, residency, and KEV matches arrive as `Fact`s from later lanes.
- Calibration weights are stored and hashed with the calibration file. The confidence number is an input; `app/confidence.py` (P3) computes it.
- `conditions.components_declared` is validated and unused by any control's `applies_when`.

## Scenario decision table

Sanity check against `docs/spec/01_DATA_AND_ZETARIS.md` §4. Each row is `decide` on a minimal fact set (as_of 2026-10-22, confidence above the tier gate unless noted). It does not read eval labels. Every outcome matches the scenario's expected outcome.

| Code | Minimal facts | Outcome | First reason |
|---|---|---|---|
| S01 | T3, internal, low, £0, signed. C01, C04, C06, C11, C12 true. Personal-data controls do not apply. | APPROVE | ALL_REQUIRED_CONTROLS_MET |
| S02 | T2, personal, low, £20k, signed. All required controls true, including current SOC 2, signed DPA, UK residency, 72h notice. | APPROVE | ALL_REQUIRED_CONTROLS_MET |
| S03 | T1, personal and payment, high, £150k, signed. Same affirmative facts. Approval role is `tprm_analyst`. | APPROVE | ALL_REQUIRED_CONTROLS_MET |
| S04 | T2, personal, draft. No SOC 2 or ISO, no breach-notice fact, DPA unsigned, vendor commits to the DPA. | REQUEST_INFO | EVIDENCE_MISSING |
| S05 | T2, personal, signed. MFA and encryption facts absent. | REQUEST_INFO | EVIDENCE_MISSING |
| S06 | T2, personal, signed. Residency `[US]`, no SCCs/IDTA, unresolved material contradiction on `residency.regions`. | ESCALATE | CONTRADICTION |
| S07 | T2, personal, signed. One unremediated material incident, plus an unresolved material contradiction on that claim. | ESCALATE | CONTRADICTION |
| S08 | T3, internal, signed. Admin MFA false. | ESCALATE | CONTROL_FAILED |
| S09 | T2, personal, signed. Two KEV matches, critical patch SLA 30 days. | ESCALATE | CONTROL_FAILED |
| S10 | T2, personal, signed. One watchlist match. Approval role is `tprm_lead`. | DECLINE | HARD_GATE_DECLINE |
| S11 | T2 clean facts, plus a guard flag at level `block`. | ESCALATE | UNTRUSTED_CONTENT_TAMPERING |
| S12 | T2, personal, signed. SOC 2 and ISO false, bridge letter true. No precedent. | ESCALATE | CONTROL_FAILED |
| S12 | Same facts, plus one precedent that meets all six C05 criteria. Approval role is `tprm_lead`. | APPROVE_WITH_CONDITIONS | CONDITIONS |
| S13 | T2, personal, signed. `dpa.signed` UNKNOWN. | REQUEST_INFO | EVIDENCE_MISSING |
| S14 | T2, personal, signed. `dpa.signed` false. | ESCALATE | HARD_GATE_ESCALATE |

## Commands

```bash
python scripts/tasks.py verify-pass --pass 2c
```

Result: lint, 64 `p2c` tests, 77 non-live tests, gate, secret-scan, and hardcode-check all passed.

## Explain-it

1. **Why does UNKNOWN never count as a pass?** A missing fact is not evidence that the control holds. A leaf with a missing or UNKNOWN fact returns UNKNOWN. `all` is TRUE only when every child is TRUE, and `any` is TRUE only when some child is TRUE. The outcome rules then ask for evidence instead of approving.

2. **Contradiction and a missing SOC 2.** An unresolved material contradiction matches O3. A missing SOC 2 makes C05 UNKNOWN, which matches O6 (`REQUEST_INFO`). O3 is earlier, so the outcome is ESCALATE with reason CONTRADICTION. `EVIDENCE_MISSING` is still listed later in `outcome_reasons` if C05 is required, and it does not decide.

3. **What lets a precedent change a decision?** Only C05 allows it, and only when all six criteria hold: the bridge-letter fact is TRUE, the reviewer rank is at least `tprm_lead`, the prior decision was APPROVE or APPROVE_WITH_CONDITIONS for that same mitigation, the precedent is at most 365 days old, H-MEM confidence is at least 0.70 and relevance at least 0.35, and the case is no riskier than the precedent's tier (T1 > T2 > T3). The control becomes conditionally TRUE. If nothing else fails, the outcome is APPROVE_WITH_CONDITIONS and still needs `tprm_lead` to execute. A broken criterion is stored on `precedents_considered` and the exception is not applied.

4. **What does monotonicity guarantee?** With confidence at or above the gate, and no contradictions or blocks, changing a control TRUE → UNKNOWN → FALSE never produces a better outcome. At any confidence, worsening a control never creates an APPROVE or APPROVE_WITH_CONDITIONS, and never turns a conditional approval into a clean one. An UNKNOWN can still yield REQUEST_INFO where a FALSE yields ESCALATE. Asking for the missing evidence is the intended response.

5. **Why does `created_at` come from `as_of`?** It is `as_of` at 00:00 UTC. The engine never reads the wall clock, so a replay with the same inputs hashes to the same record. Certificate currency, the incident window, and precedent age all use that same date.
