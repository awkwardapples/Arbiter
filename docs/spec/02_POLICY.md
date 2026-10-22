# 02: Policy-as-code, decision procedure and governed exceptions

The policy is the **knowledge** in "data, knowledge, memory, reasoning". It is the only thing that maps facts to outcomes. It is versioned, hashed into every decision record, and can be replayed.

## 1. Tri-state semantics

Every fact and control is `TRUE`, `FALSE` or `UNKNOWN`.

- **Leaf operators** return UNKNOWN when the fact is missing or UNKNOWN.
- **`all`**: TRUE if every child is TRUE; FALSE if any child is FALSE; otherwise UNKNOWN.
- **`any`**: TRUE if any child is TRUE; FALSE if every child is FALSE; otherwise UNKNOWN.
- **UNKNOWN never counts as a pass.**

Leaf operators (implemented in `app/policy/dsl.py`; no `eval`):

`is_true`, `is_false`, `eq`, `ne`, `lte`, `gte`, `lt`, `gt`, `in`, `not_in`, `in_any` (list fact intersects the value list), `subset_of` (list fact ⊆ value list), `exists`.

Leaf syntax: `{fact: <key>, op: <op>, value: <v>}`.

**Named outcome predicates** (implemented in `engine.py`; the YAML refers to them by name):

| Predicate | True when |
|---|---|
| `hard_gate_decline_false` | An applicable control with `hard_gate: decline` is FALSE |
| `injection_blocked` | Any guard flag has level `block` |
| `unresolved_material_contradiction` | Any contradiction with `severity=material` and `resolved=false` |
| `hard_gate_escalate_false` | An applicable control with `hard_gate: escalate` is FALSE (and not conditionally TRUE) |
| `required_false_without_exception` | Any required control is FALSE with no exception applied |
| `required_unknown` | Any required control is UNKNOWN and not conditionally TRUE |
| `confidence_below_gate` | `confidence.value < calibration.gate(tier)` (sets `abstained=true`) |
| `any_conditional` | Any control is TRUE with `conditional=true` (contract-stage condition or precedent exception) |
| `always` | Always |

`ControlResult` gains `conditional: bool` and `condition_text: str | None` in addition to the master-spec fields.

## 2. Tiering (inherent risk)

`inherent = 2 × sensitivity + criticality + spend`, where:

- **sensitivity** is the maximum over the vendor's data categories: none 0, internal 1, personal 2, payment 3, special_category 3;
- **criticality**: low 0, medium 1, high 2;
- **spend**: < £10k 0, < £100k 1, otherwise 2.

Tier assignment:

- **T1** if `inherent ≥ 6` or any data category is `special_category`;
- **T2** if `inherent ≥ 3`;
- **T3** otherwise.

## 3. Policy file (`policy/arbiter_policy.v1.yaml`): transcribe exactly, then unit-test every control

```yaml
policy_id: arbiter-vendor-onboarding
version: "1.0.0"
owner_role: tprm_lead
effective_from: "2026-10-22"
references:
  - "Verizon DBIR 2026: third-party involvement 48% of breaches; root causes MFA, credential rotation, least privilege"
  - "CISA KEV catalogue (CC0) for exploited-vulnerability exposure"
  - "UK GDPR Art. 28 (processor contracts), Art. 33 (72h breach notification), Chapter V (transfers)"

tiering:
  sensitivity: {none: 0, internal: 1, personal: 2, payment: 3, special_category: 3}
  criticality: {low: 0, medium: 1, high: 2}
  spend_bands: [{lt: 10000, score: 0}, {lt: 100000, score: 1}, {lt: null, score: 2}]
  tiers:
    - {tier: T1, inherent_gte: 6, or_data_category: special_category}
    - {tier: T2, inherent_gte: 3}
    - {tier: T3, default: true}

conditions:   # applicability predicates
  processes_personal_data: {fact: vendor.data_categories, op: in_any, value: [personal, payment, special_category]}
  components_declared: {fact: vuln.components_declared, op: gte, value: 1}

controls:
  - id: C01
    title: MFA enforced for privileged and remote access
    weight: 3
    required_for: [T1, T2, T3]
    rule:
      all:
        - {fact: mfa.admin_enforced, op: is_true}
        - {fact: mfa.remote_enforced, op: is_true}
    evidence_required: ["Q01 and Q02 affirmative, naming the mechanism", "or assurance report noting the MFA control without exception"]
    question_ids: [Q01, Q02]
    t1_corroboration: true        # ChallengerAgent trigger: T1 needs ≥ 1 non-answer source

  - id: C02
    title: Credential and secret hygiene
    weight: 2
    required_for: [T1, T2]
    rule:
      all:
        - {fact: creds.vaulted, op: is_true}
        - {fact: creds.rotation_days, op: lte, value: 90}
    evidence_required: ["Q03 naming a secrets manager and a rotation period ≤ 90 days"]
    question_ids: [Q03]

  - id: C03
    title: Least privilege with periodic access reviews
    weight: 2
    required_for: [T1, T2]
    rule: {fact: access.review_interval_days, op: lte, value: 90}
    evidence_required: ["Q04 with review interval ≤ 90 days"]
    question_ids: [Q04]

  - id: C04
    title: Encryption at rest and in transit
    weight: 2
    required_for: [T1, T2, T3]
    rule:
      all:
        - {fact: crypto.at_rest, op: is_true}
        - {fact: crypto.in_transit_tls12, op: is_true}
    evidence_required: ["Q05 naming the standard (e.g. AES-256)", "Q06 confirming TLS 1.2+"]
    question_ids: [Q05, Q06]

  - id: C05
    title: Current independent assurance (SOC 2 Type II or ISO 27001)
    weight: 3
    required_for: [T1, T2]
    rule:
      any:
        - {fact: assurance.soc2_type2_current, op: is_true}
        - {fact: assurance.iso27001_current, op: is_true}
    evidence_required: ["SOC 2 Type II report summary issued ≤ 12 months before as_of", "or ISO 27001 certificate with expires_on ≥ as_of"]
    question_ids: [Q07]
    precedent_exception:
      allowed: true
      mitigation_fact: assurance.bridge_letter_current   # bridge letter issued ≤ 365 days, not expired
      max_precedent_age_days: 365
      approver_role: tprm_lead
      condition: "Provide a current SOC 2 Type II report or ISO 27001 certificate within 12 months of the bridge letter date; re-review at renewal."

  - id: C06
    title: No unremediated material incident in 24 months
    weight: 2
    required_for: [T1, T2, T3]
    rule: {fact: incidents.material_unremediated_24m, op: eq, value: 0}
    evidence_required: ["ITSM incident history (system of record) with RCA for material incidents"]
    question_ids: [Q08]
    contradiction_checks:
      - {claim: incidents.vendor_reported_24m, sor: incidents.itsm_vendor_related_24m, compare: claim_zero_but_sor_positive, severity: material}

  - id: C07
    title: Personal-data breach notification within 72 hours
    weight: 2
    required_for: [T1, T2]
    applies_when: processes_personal_data
    rule: {fact: breach.notify_hours, op: lte, value: 72}
    evidence_required: ["CLM contract clause ≤ 72h", "or Q09 commitment ≤ 72h while the contract is not yet signed"]
    question_ids: [Q09]
    contract_stage_condition:
      when_contract_status_in: [none, draft, negotiation]
      claim_fact: breach.notify_hours_claimed
      claim_rule: {op: lte, value: 72}
      condition: "Contract must include a breach-notification clause of 72 hours or less before go-live."
      approver_role: tprm_analyst
    contradiction_checks:
      - {claim: breach.notify_hours_claimed, sor: breach.notify_hours_contract, compare: numeric_mismatch, severity: minor}

  - id: C08
    title: Data Processing Agreement executed
    weight: 3
    required_for: [T1, T2, T3]
    applies_when: processes_personal_data
    hard_gate: escalate
    rule: {fact: dpa.signed, op: is_true}
    evidence_required: ["CLM shows DPA signed with a signature date"]
    question_ids: [Q15]
    contract_stage_condition:
      when_contract_status_in: [none, draft, negotiation]
      claim_fact: dpa.vendor_commits
      claim_rule: {op: is_true}
      condition: "Execute the Data Processing Agreement before any personal data is shared."
      approver_role: tprm_analyst

  - id: C09
    title: Data residency or lawful transfer mechanism
    weight: 3
    required_for: [T1, T2, T3]
    applies_when: processes_personal_data
    rule:
      any:
        - {fact: residency.regions, op: subset_of, value: [UK, EU]}
        - {fact: transfer.mechanism, op: in, value: [SCCs, IDTA]}
    evidence_required: ["CLM hosting clause UK/EU", "or a documented transfer mechanism (SCCs/IDTA)"]
    question_ids: [Q10, Q11]
    contradiction_checks:
      - {claim: residency.regions_claimed, sor: residency.regions_contract, compare: set_not_subset, severity: material}

  - id: C10
    title: Sub-processor disclosure
    weight: 1
    required_for: [T1, T2]
    rule: {fact: subprocessors.disclosed, op: is_true}
    evidence_required: ["Sub-processor list attached to contract", "or Q12 affirmative with list"]
    question_ids: [Q12]

  - id: C11
    title: Sanctions and watchlist clear
    weight: 3
    required_for: [T1, T2, T3]
    hard_gate: decline
    rule: {fact: sanctions.watchlist_matches, op: eq, value: 0}
    evidence_required: ["GRC watchlist screening across all vendor aliases"]
    question_ids: []

  - id: C12
    title: No unmitigated exposure to known-exploited vulnerabilities
    weight: 3
    required_for: [T1, T2, T3]
    rule:
      any:
        - {fact: vuln.kev_matches, op: eq, value: 0}
        - {fact: vuln.patch_sla_critical_days, op: lte, value: 14}
    evidence_required: ["Declared components checked against CISA KEV", "or critical patch SLA ≤ 14 days with attestation"]
    question_ids: [Q13, Q14]

outcome_rules:   # evaluated in order; first match wins
  - {id: O1, when: hard_gate_decline_false,            outcome: DECLINE,                 reason: HARD_GATE_DECLINE}
  - {id: O2, when: injection_blocked,                  outcome: ESCALATE,                reason: UNTRUSTED_CONTENT_TAMPERING}
  - {id: O3, when: unresolved_material_contradiction,  outcome: ESCALATE,                reason: CONTRADICTION}
  - {id: O4, when: hard_gate_escalate_false,           outcome: ESCALATE,                reason: HARD_GATE_ESCALATE}
  - {id: O5, when: required_false_without_exception,   outcome: ESCALATE,                reason: CONTROL_FAILED}
  - {id: O6, when: required_unknown,                   outcome: REQUEST_INFO,            reason: EVIDENCE_MISSING}
  - {id: O7, when: confidence_below_gate,              outcome: ESCALATE,                reason: LOW_CONFIDENCE_ABSTAIN}
  - {id: O8, when: any_conditional,                    outcome: APPROVE_WITH_CONDITIONS, reason: CONDITIONS}
  - {id: O9, when: always,                             outcome: APPROVE,                 reason: ALL_REQUIRED_CONTROLS_MET}

roles: {tprm_analyst: 1, tprm_lead: 2}   # rank; a higher rank satisfies a lower requirement

approvals:   # consumed by ActionExecutor when issuing contracts
  APPROVE: {T1: [tprm_analyst], T2: [], T3: []}
  APPROVE_WITH_CONDITIONS: {contract_stage_only: [tprm_analyst], precedent_exception: [tprm_lead]}
  REQUEST_INFO: []
  ESCALATE: []
  DECLINE: [tprm_lead]

residual_risk:
  tier_base: {T1: 55, T2: 35, T3: 15}
  per_false_weight: 6
  per_unknown_weight: 3
  per_material_contradiction: 10
  injection: 15
  cap: 100
```

## 4. Derived facts (computed by EvidenceAgent and EvaluatorAgent, never by the LLM)

| Fact | Derivation |
|---|---|
| `vendor.data_categories` | Procurement `data_categories` split on commas (or the inline submission) |
| Claim-derived facts (`mfa.*`, `creds.*`, `access.*`, `crypto.*`, `pentest.*`, `*_claimed`, `assurance.claimed`, `dpa.vendor_commits`, `incidents.vendor_reported_24m`) | The grounded claim's value and state. An ungrounded claim, or one whose segment the guard warned on for a hard-gate control, gives UNKNOWN |
| `assurance.soc2_type2_current` | **TRUE:** a `soc2_type2_summary` with `issued_on ≥ as_of − 365 days`, not DQ-flagged and not guard-blocked. **FALSE:** Q07's grounded claim names neither SOC 2 Type II nor ISO 27001 (e.g. "bridge letter only"), or only stale SOC 2 documents exist. **UNKNOWN:** no SOC 2 document and Q07 unanswered, ungrounded, or claiming SOC 2 without a document (then REQUEST_INFO asks for the report) |
| `assurance.iso27001_current` | **TRUE:** an `iso27001_certificate` with `expires_on ≥ as_of`. **FALSE / UNKNOWN:** same rules as SOC 2 above, for ISO |
| `assurance.bridge_letter_current` | `bridge_letter` with `issued_on ≥ as_of − 365 days` and `expires_on ≥ as_of` |
| `incidents.itsm_vendor_related_24m` | Count of ITSM incidents for any alias with `opened_at ≥ as_of − 730 days` and category in (`third_party_breach`, `data_exposure`). Outages and other categories do not contradict a truthful "no security incidents" |
| `incidents.material_unremediated_24m` | Count of those with severity in (P1, P2), category in (third_party_breach, data_exposure), and (`rca_completed` is not true or status is open) |
| `breach.notify_hours` | CLM `breach_notification_hours` if the contract is signed; otherwise UNKNOWN (contract-stage condition may apply) |
| `dpa.signed` | CLM `dpa_signed` if the contract is signed and the DQ rule passes; UNKNOWN if DQ fails |
| `residency.regions` | If the contract is **signed**: CLM `hosting_region_clause` mapped to a set (EU→{EU}, UK→{UK}, US→{US}, GLOBAL→{US, EU, UK, OTHER}). Otherwise the claimed set from Q10 (a draft clause is not yet binding) |
| `transfer.mechanism` | CLM `transfer_mechanism` if the contract is signed, otherwise the Q11 claim |
| `subprocessors.disclosed` | CLM `subprocessor_list_attached` if the contract is signed, otherwise the Q12 claim |
| `sanctions.watchlist_matches` | Count of watchlist entries whose normalised name exactly equals any normalised alias (vendor cases: `Q_WATCHLIST_SCREEN`; inline: Python over `Q_WATCHLIST_ALL`) |
| `sanctions.near_matches` | Count of entries with difflib ratio ≥ 0.92 but not exact (Python over `Q_WATCHLIST_ALL`). Informational: it does not fail C11; at T1 it triggers the Challenger |
| `vuln.components_declared` | Row count of `Q_VENDOR_COMPONENTS` (inline: the submission's `declared_components`) |
| `vuln.kev_matches` | 0 when `components_declared = 0` (no KEV query runs); otherwise the count of distinct KEV CVEs from `Q_COMPONENT_KEV` (inline: `Q_KEV_BY_PRODUCTS`), UNKNOWN until that query has run |
| `vuln.patch_sla_critical_days` | Submission `patch_sla_critical_days`, otherwise the Q13 claim |

Precedence rule: system-of-record values beat claims. A disagreement creates a `Contradiction`; the SoR value is still used as the fact. Material contradictions trigger O3 unless resolved: the Planner may query once more to confirm that the SoR row is current.

## 5. Decision procedure (`app/policy/engine.py`)

```python
def decide(inputs: PolicyInputs, policy: Policy, calibration: Calibration) -> DecisionRecord:
    tier, inherent = tiering(inputs.profile, policy)
    controls = [
        evaluate_control(c, inputs.facts, tier, inputs.as_of)
        for c in policy.controls_applicable(tier, inputs)
    ]
    controls = apply_contract_stage_conditions(controls, inputs, policy)
    controls = apply_precedent_exceptions(controls, inputs.precedents, inputs.facts, policy, inputs.as_of)
    matched = matching_outcome_rules(
        policy.outcome_rules, controls, inputs, confidence=inputs.confidence, gate=calibration.gate(tier)
    )
    outcome, outcome_reasons = (
        matched[0].outcome,
        [r.reason for r in matched],
    )  # all matching reasons, first decides
    counterfactuals = compute_counterfactuals(controls, inputs.contradictions, policy)
    residual = residual_risk(tier, controls, inputs, policy)
    return DecisionRecord(..., record_sha256=canonical_hash(...))
```

- **Confidence is an input** computed before `decide`, by `app/confidence.py`. Confidence never depends on the outcome.
- **Two decisions per run (memory without circularity).** DECIDE₁ runs with no precedents (and `precedent_alignment = 1.0`). MEMORY_CHECK retrieves precedents for DECIDE₁'s failing exception-eligible controls and recomputes confidence with the real `precedent_alignment`. DECIDE₂ then runs the *same* pure function with the candidates. Both records are traced; only DECIDE₂ is stored as the case decision.
- **`force_escalate(record, reason)`** (from the Challenger or SAFE_ESCALATE) returns a copy with `outcome = worse_of(outcome, ESCALATE)` (rank order APPROVE > APPROVE_WITH_CONDITIONS > REQUEST_INFO > ESCALATE > DECLINE), so a DECLINE stays DECLINE, and appends `reason` to `escalation_reasons`. It never improves an outcome.
- **Time:** `as_of` comes from `inputs.as_of` (configured `ARBITER_AS_OF`); `created_at` is `as_of` at 00:00 UTC. Nothing in `decide` reads the wall clock.
- **Roles:** `policy.roles` ranks roles (`tprm_analyst: 1`, `tprm_lead: 2`). A requirement for role R is satisfied by any approver whose rank ≥ rank(R).
- **Counterfactuals:** every required control not TRUE, and not conditionally TRUE, produces one counterfactual with `evidence_required` and `question_ids` from the policy. Each unresolved contradiction adds "resolve contradiction on `<key>`". For APPROVE outcomes, list *fragile* controls (supported by a single vendor claim only) under `limitations`.

## 6. Governed precedent exceptions (where memory meets policy)

A precedent may justify an exception **only** when all of these hold:

1. The control has `precedent_exception.allowed: true`. In v1 only C05 qualifies.
2. The case has `mitigation_fact` TRUE (for example, a current bridge letter, grounded).
3. The precedent was created by a human review with role rank ≥ rank(`approver_role`), decision `APPROVE_WITH_CONDITIONS` or `APPROVE`, citing this control, with the same mitigation.
4. The precedent's age (this case's `as_of` minus the precedent case's `as_of`) is at most `max_precedent_age_days`.
5. The precedent's H-MEM confidence is ≥ 0.70 and its retrieval relevance ≥ 0.35.
6. The case tier is no riskier than the precedent's tier (T1 > T2 > T3).

**Effect:**

- The control becomes TRUE with `conditional=true` and `exception_applied=P-…`.
- The decision becomes `APPROVE_WITH_CONDITIONS` (if nothing else fails) and needs `tprm_lead` approval to execute.
- A `wrong` feedback from a reviewer later reduces the precedent's confidence by 0.20 (H-MEM delta), which can retire it.

**This is the governance story:** memory proposes, the policy permits, a human approves, and the audit log records all three.

## 7. Required unit tests (P2-C lane, marker `p2c`; ids match `passes/P2_ENGINES.md` §C5)

- **P2-T30:** every control returns TRUE, FALSE or UNKNOWN for crafted fact sets (table-driven, ≥ 3 cases per control).
- **P2-T31:** the outcome rule order matches §3 (a decline gate beats everything; injection beats contradiction; REQUEST_INFO only when nothing failed).
- **P2-T32:** contract-stage conditions yield APPROVE_WITH_CONDITIONS with `tprm_analyst` approval.
- **P2-T33:** a precedent exception requires all six criteria. Mutate each criterion → no exception.
- **P2-T34:** counterfactuals list exactly the non-TRUE required controls plus unresolved contradictions.
- **P2-T35:** safety monotonicity (seeded loop over ≥ 2,000 random control-result sets), two properties:
  1. With confidence ≥ the gate and no contradictions or guard flags, degrading any **control result** TRUE → UNKNOWN → FALSE never improves the outcome rank (APPROVE > APPROVE_WITH_CONDITIONS > REQUEST_INFO > ESCALATE > DECLINE).
  2. For any confidence, degrading any control result or fact never moves a non-approval into APPROVE or APPROVE_WITH_CONDITIONS, and never moves APPROVE_WITH_CONDITIONS into APPROVE.
  (Strict rank monotonicity over raw facts does not hold by design: an UNKNOWN can yield REQUEST_INFO where a FALSE yields ESCALATE, and asking for evidence is the correct response to missing evidence.)
- **P2-T36:** determinism. The same inputs give the same `record_sha256`; key order in input dicts does not matter.
- **P2-T37:** tiering boundaries (inherent 2/3/5/6, special_category override).
- **P2-T38:** the policy loader rejects unknown operators, unknown fact keys (checked against `app/schemas/facts.py` `FACT_KEYS`) and duplicate control ids.
