# P14-A report — decision quality and analyst brief

## Built

- **B1.** `outcome_reasons` keeps every matching rule in order, and keeps `ALL_REQUIRED_CONTROLS_MET` only when that always-rule is the sole match (the outcome is APPROVE). Each new record stores `policy_engine_version: "1.1"` before `record_sha256`.
- **B2.** A required control counts toward coverage only when its state is TRUE or FALSE and every fact it cites has verified provenance. Required controls whose state is UNKNOWN are listed on `unknown_controls`. That list is display-only and is not a weighted signal. `python run.py calibrate` wrote `policy/calibration/cal-2026-10-26-eb975166.json` (gates T1, T2 and T3 all 0.95, `unsafe_approvals` 0). `ACTIVE` points at that version. `cal-initial.json` stays, because older records name it.
- **B3.** One counterfactual per control id. Policy `evidence_required` and `question_ids` are merged in order and de-duplicated. An unresolved contradiction appends `resolve contradiction on <key>` onto that control's row, including when the control is already TRUE.
- **Brief.** The cited report stays `template:v1`, so the offline `Report.generator` contract is unchanged. A separate deterministic brief is `template:v2`: a headline, at most four why-points, and next steps. Wording comes from `app/labels.py` (outcome, reason, control title, system, question). A deep-route model may replace only `headline` and `why[].text`. A number or a name that is not in the case is rejected; the brief stays `template:v2` and the trace status is `fallback`.
- **Drafts.** REQUEST_INFO is an email to the vendor listing every counterfactual question and the evidence that would satisfy it. ESCALATE is an ITSM ticket. DECLINE is a memo to the business owner. APPROVE and APPROVE_WITH_CONDITIONS are an approval memo. `clarification_email` is still filled.
- **Workload.** Counted from the run that just executed: `queries` from `query_run` trace events, `model_calls` and `models` from `model_call` events, row and claim counts from `CaseState`. System names are the business labels. `RunOutput.summary` is the brief headline.
- **Dossier.** `render(bundle, fmt)` writes header, brief, evidence, controls, counterfactuals, drafts, approvals with a signature check, precedents, and integrity (policy version and hash, calibration version, record hash, `python run.py replay <case>`, trace id, models). HTML is self-contained. `GET /cases/{id}/dossier?format=md|html` and `python run.py dossier` serve the same renderer.

## Before and after

Example 2 (CASE-0007, Quillfeather Payroll Cloud Ltd) stays **ESCALATE**.

Before, from the committed sample output:

> Outcome ESCALATE: CONTRADICTION, CONTROL_FAILED, EVIDENCE_MISSING, LOW_CONFIDENCE_ABSTAIN, ALL_REQUIRED_CONTROLS_MET. Failing controls: C05, C09, C12.

That record reported coverage 1.0. C05 was unverified and still counted as covered.

After, `SAMPLE_MODE=true LLM_PROVIDER=offline python run.py assess --input input_examples/example_2.json` (`template:v2`):

> Escalate to the TPRM lead: Quillfeather Payroll Cloud Ltd says EU, but its contract (CTR-30007) shows US.

Why:

1. Quillfeather Payroll Cloud Ltd says EU, but its contract (CTR-30007) shows US.
2. Quillfeather Payroll Cloud Ltd runs FortiOS, which has 15 known-exploited vulnerabilities against a 30-day critical-patch SLA (policy limit 14 days).
3. Current independent assurance (SOC 2 Type II or ISO 27001) is unverified. What would satisfy it: SOC 2 Type II report summary issued ≤ 12 months before as_of; or ISO 27001 certificate with expires_on ≥ as_of.

On that run, coverage is 0.9167, `unknown_controls` is `C05`, the gate is 0.95, and confidence is 0.75. The vendor name, residency values, contract id, product, and KEV count are read from the case facts and the executed query rows. Counterfactuals are one row each for C05, C09, and C12. The C09 row includes `resolve contradiction on residency.regions`.

Example 4 (CASE-0022, Fennimore Survey Tools Ltd) stays **REQUEST_INFO**.

Before:

> Outcome REQUEST_INFO: EVIDENCE_MISSING, ALL_REQUIRED_CONTROLS_MET. Failing controls: C01, C04.

After:

> Request information to the vendor: MFA enforced for privileged and remote access is unverified. What would satisfy it: Q01 and Q02 affirmative, naming the mechanism; or assurance report noting the MFA control without exception.

The vendor email lists each counterfactual question (privileged MFA, remote MFA, encryption at rest, encryption in transit) and the evidence that would satisfy it.

The other four offline examples keep the outcomes in `input_examples/expected.json` (APPROVE, ESCALATE, DECLINE, APPROVE).

## Deviations

- `Report.brief` defaults to `None` and `Report.drafts` defaults to `[]`, so existing `Report(...)` constructors keep working. The spec table shows `brief` as a required field. The cited-report generator remains `template:v1`.
- The spec's example headline packs residency and the KEV count into one sentence. The brief uses the first why-point as the headline and puts the KEV count in the second why-point. Both facts are in the brief, which is what P14A-T5 checks.
- `policy_engine_version` defaults to `"1.1"` on the model. A stored row written before 1.1 loads as 1.1 and will not hash-match. `app/audit/replay.py` was left as it is. New records replay. The demo store is regenerated with 1.1 records.
- `build_brief`, `build_drafts`, and `accept_brief_wording` live in `app/labels.py`, which the plan named as the label module. `app/agents/reporter.py` calls them. `labels.py` is about 430 lines and `app/orchestrator.py` was already past the 400-line guide before the workload helper.
- P2-T34 and P2-T36 stay. Their expected reason list and counterfactual rows now match the 1.1 contract.

## Known gaps

- Policy `evidence_required` text is copied into the "what would satisfy it" clause, so question ids such as Q01 and the field name `as_of` still appear there. Headline and why text for example 2 contain none of the T5 code patterns.
- The analyst console (`ui/`) is lane 14b and was not changed. The brief is on the API, the CLI dossier, and `RunOutput`.
- `output_examples/` was not regenerated. Pass 15 owns published examples.

## Commands

```
python scripts/tasks.py verify-pass --pass 14a
SAMPLE_MODE=true LLM_PROVIDER=offline python run.py assess --input input_examples/example_2.json
python run.py dossier CASE-0007 --format html --out /tmp/dossier.html
```

`verify-pass --pass 14a` passed: ruff clean, 13 p14a tests passed, regression 695 passed and 6 skipped, secret-scan ok, hardcode-check ok. The dossier HTML (5366 bytes) contains every section, the replay command, the vendor, CTR-30007, and FortiOS, and it contains no secret marker and no external URL.

## Explain it

1. **When is `ALL_REQUIRED_CONTROLS_MET` recorded?** Only when it is the only matching rule, which is an APPROVE. Any earlier match drops the always-rule from `outcome_reasons`. The record is stamped `policy_engine_version` 1.1 before the hash.
2. **What counts as covered?** A required control is covered when the same DSL the engine uses evaluates it to TRUE or FALSE and every cited fact has verified provenance. UNKNOWN required controls go to `unknown_controls` and are left out of the weighted sum. Example 2 coverage moved from 1.0 to 0.9167 because C05 is unverified. The outcome stayed ESCALATE, so the lane was not blocked. Recalibration raised every tier gate to 0.95 with zero unsafe approvals, and the six example outcomes still match `input_examples/expected.json`.
3. **How are counterfactuals merged?** One row per control. Failing required controls come first. An unresolved contradiction adds its resolve line and question ids onto that control, creating the row when the control is already TRUE. Resolved contradictions are omitted.
4. **What may the model change?** Only the headline and the why text, on the deep route. Evidence refs and citations stay from the template. A number or a personal or vendor name that is not already in the case is rejected, the brief stays `template:v2`, and the trace status is `fallback`. Offline runs never call the model, so they stay on the template.
5. **Where do example 2's figures come from?** The vendor legal name, the EU claim, the US contract value, the `CTR-30007` record key, the FortiOS component row from `Q_VENDOR_COMPONENTS`, and the KEV and patch-SLA fact values. There is no branch on vendor id or case id.
6. **What does workload count?** Events in `logs/trace-<run_id>.jsonl` for queries and model calls, plus claims, rows, contradictions, DQ flags, and guard blocks already on the case state. Example 2 offline: 14 queries, 39 rows, 16 answers, 16 grounded claims, 1 contradiction, 0 model calls.
