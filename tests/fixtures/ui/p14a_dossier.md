# Decision dossier: Quillfeather Payroll Cloud Ltd

## Header

Vendor: Quillfeather Payroll Cloud Ltd
Decision: Escalate. A person must decide; the policy will not approve this case as it stands.
Tier: T1
Residual risk: 100
Confidence 75%. Unverified controls: C05 Current independent assurance (SOC 2 Type II or ISO 27001).

## Analyst brief

Escalate to the TPRM lead: Quillfeather Payroll Cloud Ltd says EU, but its contract (CTR-30007) shows US.

- Quillfeather Payroll Cloud Ltd says EU, but its contract (CTR-30007) shows US.
- Quillfeather Payroll Cloud Ltd runs FortiOS, which has 15 known-exploited vulnerabilities against a 30-day critical-patch SLA (policy limit 14 days).
- Current independent assurance (SOC 2 Type II or ISO 27001) is unverified. What would satisfy it: SOC 2 Type II report summary issued ≤ 12 months before as_of; or ISO 27001 certificate with expires_on ≥ as_of.

Next steps:
- Open the service-desk ticket for the TPRM lead. Owner: tprm_lead.

## Evidence

| Source | Record | Field | Value | Quote | Request |
| --- | --- | --- | --- | --- | --- |
| Contract system (CLM) | CTR-30007 | hosting_region_clause | US |  |  |
| Vendor trust portal | vendor claim | residency.regions | EU |  |  |

## Controls

- MFA enforced for privileged and remote access: met. The cited evidence meets the control.
- Credential and secret hygiene: met. The cited evidence meets the control.
- Least privilege with periodic access reviews: met. The cited evidence meets the control.
- Encryption at rest and in transit: met. The cited evidence meets the control.
- Current independent assurance (SOC 2 Type II or ISO 27001): unverified. Would need SOC 2 Type II report summary issued ≤ 12 months before as_of; or ISO 27001 certificate with expires_on ≥ as_of.
- No unremediated material incident in 24 months: met. The cited evidence meets the control.
- Personal-data breach notification within 72 hours: met. The cited evidence meets the control.
- Data Processing Agreement executed: met. The cited evidence meets the control.
- Data residency or lawful transfer mechanism: not met. Would need CLM hosting clause UK/EU; or a documented transfer mechanism (SCCs/IDTA); resolve contradiction on residency.regions.
- Sub-processor disclosure: met. The cited evidence meets the control.
- Sanctions and watchlist clear: met. The cited evidence meets the control.
- No unmitigated exposure to known-exploited vulnerabilities: not met. Would need Declared components checked against CISA KEV; or critical patch SLA ≤ 14 days with attestation.

## What would change this decision

- Current independent assurance (SOC 2 Type II or ISO 27001) (unverified to met). SOC 2 Type II report summary issued ≤ 12 months before as_of; or ISO 27001 certificate with expires_on ≥ as_of Which independent certifications or attestations do you hold?
- Data residency or lawful transfer mechanism (not met to met). CLM hosting clause UK/EU; or a documented transfer mechanism (SCCs/IDTA); resolve contradiction on residency.regions Where will our data be hosted and processed? What mechanism governs international transfers?
- No unmitigated exposure to known-exploited vulnerabilities (not met to met). Declared components checked against CISA KEV; or critical patch SLA ≤ 14 days with attestation What is your patch SLA for critical vulnerabilities? How often do you run independent penetration tests?

## Drafts

To: tprm_lead
Subject: Escalation ticket: Quillfeather Payroll Cloud Ltd

Summary: Quillfeather Payroll Cloud Ltd needs a decision from the TPRM lead.

Evidence:
- Current independent assurance (SOC 2 Type II or ISO 27001) is unverified
- Data residency or lawful transfer mechanism is not met
- No unmitigated exposure to known-exploited vulnerabilities is not met
- Claim EU does not match the record US

Risk: residual risk 100 out of 100, tier T1.

Requested decision: continue, ask Quillfeather Payroll Cloud Ltd for evidence, or decline.

## Approvals

Approvals required: none.
- ctr-0bc47ab19027: state executed, intent vendor.onboarding.escalate, signature valid.

## Precedents

No precedents were considered.

## Integrity

Policy version: 1.0.0
Policy hash: d87244d91cacbd6a8c7119595311261a1205fc9019b00426b7d9c66fa06f4857
Calibration version: cal-2026-10-26-eb975166
Record hash: 69e8afe7d8b586f256391da7512079e2bf01c55149adb6ee878c1f9a2827ebb6
Replay command: python run.py replay CASE-0007
Trace id: run-4656327b678b
Models served: none (deterministic brief)
