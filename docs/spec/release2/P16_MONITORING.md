# P16 (stretch): continuous exposure monitoring, so the agent remembers and acts after approval

Build this only if P13 and P14-A are merged by **Sat 24 Oct 14:00**. Otherwise it becomes a "future work" slide.

## 1. Goal

Onboarding is not the last decision. Arbiter re-checks every approved vendor's declared components against CISA's Known Exploited Vulnerabilities catalogue (live through the Zetaris USL; snapshot in sample mode). When a vulnerability is added **after** the vendor was approved, Arbiter:

1. opens a re-assessment case;
2. retrieves the vendor's prior assessment from H-MEM (working-layer assessment memory) and cites it;
3. re-runs the policy with today's evidence;
4. drafts the next action (patch-status request to the vendor, or an escalation ticket) under a signed contract.

This is the track's "agents that plan, remember and act", demonstrated beyond a single request with a **real** historical event.

## 2. The real scenario (no invented vulnerability data)

**Northbridge Secure Transfer Ltd** is a synthetic, clearly labelled inline vendor. It runs *Progress MOVEit Transfer*, has a 30-day critical patch SLA, and is otherwise clean.

- It is assessed **as of 15 May 2023**. KEV evidence counts only entries with `dateAdded ≤ as_of`, so there is no MOVEit entry yet and the vendor is **APPROVED**.
- CISA added **CVE-2023-34362** (MOVEit Transfer SQL injection, known ransomware use) on **2 June 2023**. It is in the committed snapshot and in the live feed.
- `monitor` (as of the configured date) finds the new exposure. The re-assessment fails C12 (KEV exposure plus a patch SLA over 14 days) and escalates with a ticket naming the CVE, its KEV due date and the ransomware flag.

## 3. Deliverables

| File | Responsibility |
|---|---|
| `app/facts.py` ✎ (KEV only) | `vuln.kev_matches` counts only KEV rows with `date_added ≤ as_of`. This is time-correct evidence: a decision can only know what was published by its date. The label oracle and e2e outcomes are unchanged, because all current KEV dates precede 2026-10-26 (prove it with a test) |
| `data/monitor/northbridge_2023.json` | The inline `VendorSubmission` (synthetic, labelled), with `as_of: 2023-05-15` carried in the request options |
| `app/schemas/api.py` ✎ | Additive: `RunOptions.as_of: date \| None` (defaults to `ARBITER_AS_OF`) and `trigger: dict \| None` |
| `app/monitor.py` | `scan(store, backend, *, as_of) -> list[MonitorAlert]`. For each APPROVE / APPROVE_WITH_CONDITIONS case, re-run `Q_COMPONENT_KEV` (vendor cases) or `Q_KEV_BY_PRODUCTS` (inline cases). Any CVE with `date_added > case.as_of` and `≤ as_of` that is not already alerted is **new exposure**. `reassess(alert) -> RunResponse` re-runs the vendor with `trigger={kind: "kev_new_exposure", cve_ids, prior_case_id}`. The Planner sees the prior assessment via memory, so iteration 1 includes the KEV and patch-SLA checks. Alerted CVEs are recorded in the store, so the scan is idempotent |
| `app/cli/monitor.py` | `python run.py monitor [--seed-history] [--reassess] [--as-of DATE]`. `--seed-history` runs the real assessment of `northbridge_2023.json` as of 2023-05-15 (memory on) so the store contains the historical approval |
| `app/api/routes_monitor.py`, `app/api/main.py` ✎ (one include line) | `POST /monitor/kev {reassess: bool, as_of?: date}` returns alerts and created case ids |
| Trace | Agent `MonitorAgent`: `scan`, `alert` (CVE, vendor, dateAdded), `reassess` (target Orchestrator) |
| Brief (via P14-A reporter) | When `trigger` is set, the headline starts *"Re-assessment: CISA added CVE-2023-34362 (MOVEit Transfer, known ransomware use) after this vendor was approved on 15 May 2023…"* |

## 4. Acceptance tests (marker `p16`)

| Id | Test |
|---|---|
| P16-T1 | Time-correct KEV: Northbridge as of 2023-05-15 gives APPROVE with `kev_matches = 0`; as of 2023-06-10 gives C12 FALSE. The six e2e examples are unchanged |
| P16-T2 | `scan` after `--seed-history` returns exactly CVE-2023-34362 for Northbridge, and nothing for other approved cases |
| P16-T3 | `reassess` creates a new case whose trace shows `MemoryKeeper` retrieving the 2023 assessment, the Planner running the KEV check in iteration 1, outcome ESCALATE, and an ITSM draft naming the CVE, due date and ransomware flag |
| P16-T4 | A second `scan` creates no new case (idempotent) |
| P16-T5 | No code reads labels or expected files; dates come from settings or request options |

## 5. Demo use (P17)

A 20-second segment:

1. *"Arbiter approved Northbridge in May 2023."*
2. Run the monitor.
3. *"On 2 June CISA added the MOVEit vulnerability behind the Cl0p campaign. Arbiter remembered the vendor, re-ran the policy and opened an escalation automatically, with a signed contract."*

## 6. Cursor prompt

```
/start-pass 16
You are implementing P16 (stretch) of Arbiter Release 2: continuous KEV exposure monitoring with time-correct evidence and memory-driven re-assessment.
Read: AGENTS.md; docs/spec/release2/README.md; docs/spec/release2/P16_MONITORING.md; app/facts.py (KEV derivation only); app/memory/assessments.py; app/data/queries.yaml; app/orchestrator.py (entry points only); app/schemas/api.py.
Plan Mode: .cursor/plans/P16.md with files and tests P16-T1..P16-T5. Wait for approval.
Tests first (marker p16) → commit → implement until `python scripts/tasks.py verify-pass --pass 16` is green.
Finish with docs/passes/P16_REPORT.md + docs/cursor-usage/P16.md; push p16-monitor; delete .cursor/ACTIVE_PASS; stop.
```
