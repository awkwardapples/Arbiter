# P18-C report: the Case page and the Cases queue (lane `18c`)

Tool: Claude Code, Claude Opus 5.5. Plan: `.cursor/plans/P18-C.md` (approved with all four recommendations).
Branch `p18c-case`, built on `origin/p18b-run` (18b parts 1 and 2), for a PR into `p18-console`.

## What was built

**Cases** (`/console/cases`, `web/src/pages/cases/`):
- **Summary sentence** from `GET /cases`, for example "6 cases. 3 need the TPRM lead; 1 is waiting for the vendor; 1 approval is waiting for sign-off."
  - Sign-off is counted from `GET /cases/{id}` for at most 40 cases; a tooltip says so.
- **Filter chips** by outcome and tier, each with a count, kept in the URL (`?outcome=…&tier=…`, repeatable).
- **Table** in server order (residual risk). Columns:
  - vendor and case id (`Identifier`);
  - `OutcomeBadge`;
  - tier;
  - risk number with a bar;
  - status;
  - relative time, with the absolute UTC time in a tooltip.
- **Keyboard:** the arrow keys move between rows; Enter or a click opens the case.
- **Empty state:** "No cases yet. Start an assessment to see the agents work." with a "Start an assessment" button.

**Case** (`/console/cases/:caseId`, `web/src/pages/case/`, `web/src/features/case/`):
- **Header:**
  - vendor name (28 px);
  - `OutcomeStamp` and the outcome meaning;
  - tier and residual risk;
  - a confidence sentence that names unverified controls by title;
  - the mode chip from the case trace's `mode`;
  - the case and run ids.
- **Tabs** (`?tab=` in the URL; Animated Tabs):
  - **Decision:** the serif headline and why-points beside a Tracing Beam.
    - A why-point with both refs shows a claim card ≠ record card, with clash-red values when they differ and the Zetaris request id when there is one.
    - Next action panel: role, subject, editable serif body, Copy (clipboard, falling back to selecting the text), Download .txt.
    - Contract block: state, plus the approval form (role, name, rationale with a live "n / 30", Approve or Reject contract). It shows the toast "Contract approved" and the outbox file. An executed contract shows "Sent to the outbox: <file>".
  - **Evidence:**
    - controls in business terms with what would satisfy each one;
    - what would change this decision, de-duplicated by control, with the vendor questions;
    - precedents considered (lead, conditions, applied, and why not);
    - facts table with provenance popovers: record key, query, Zetaris request id, quote.
  - **Agent activity:** 18b's `<RunCanvas source={{kind:"events"}}>` replaying `GET /cases/{id}/trace`, paced for sample traces and played with its real gaps for live ones, plus the workload sentence.
  - **Audit trail:**
    - Timeline of case created, contracts issued, approvals and rejections (who, role, rationale), reviews, and each replay run this session.
    - Replay decision: "Decision replays identically", the diff in words, or the P19 override sentence ("Machine decision replays identically; the TPRM lead overrode it to Approve with conditions on 24 Oct 2026: …").
    - Download dossier (HTML and Markdown) and Open review.
  - **Technical details**, the only tab where codes lead:
    - reason codes with their meanings, plus the policy and record hashes;
    - control table with evidence chips;
    - contradictions and counterfactuals (raw);
    - signed contracts (id, parent, intent, state, signature prefix, issued, expires);
    - the raw `CaseDetail` JSON.
- **New kit files** (`web/src/ui/`, new only):
  - `AnimatedTabs`, `TracingBeam` and `Timeline`. These are hand-written in the style of the Aceternity components, using only the tokens: solid ink and hairline, no gradients, and they respect reduced motion.
  - `popover` (Radix).

**Gate** (`scripts/gates/p18c.py`):
- fails if the `<labels:…>` blocks in `web/src/features/case/words.ts` drift from `app/labels.py` (checked by introducing a drift on purpose);
- then runs 18b's gate steps: `npm run check`, dist freshness and the smoke when a server and Playwright are available.

**Smoke** (`scripts/capture_web.py`, one function and one call added): after the run, the smoke opens the Case page, clicks every tab, replays (expecting a match) and takes two screenshots: `docs/img/console_case_decision.png` and `console_case_activity.png` at 1440×900.

## Acceptance tests (Vitest, recorded payloads only)

| Id | File | Result |
|---|---|---|
| P18C-T1 | `web/src/pages/cases/__tests__/cases.test.tsx` (7 tests, including the superseded-contract case) | pass |
| P18C-T2 | `features/case/__tests__/decision.test.tsx` | pass |
| P18C-T3 | `next-action.test.tsx` | pass |
| P18C-T4 | `contract.test.tsx` | pass |
| P18C-T5 | `replay.test.tsx` | pass |
| P18C-T6 | `activity.test.tsx` (counters compared with `replay(trace, registry)`) | pass |
| P18C-T7 | `parity.test.tsx` (every design §9 row 18c owns) | pass |

## Deviations and exceptions (all approved in the plan)

- **Base:** built on `origin/p18b-run` because PR #34 was not yet merged into `p18-console`. Merging `p18-console` after #34 lands should only touch `web/dist/`; rebuild it.
- **Fixtures outside the lane (new files only):**
  - `scripts/record_p18c_fixtures.py` runs the six examples through the API in-process in sample mode;
  - it writes `tests/fixtures/ui/p18c_*.json` (queue, the pending DECLINE case and its trace, the approval result, the approved case, the contradiction case and its trace, replay match, review, replay with `human_override`, registry, agents);
  - the recorded P14-A payloads had no pending contract and no replay results.
- **Words mirrored from `app/labels.py`:** outcome meanings, reason meanings, system labels and state words. The API does not serve them, so `words.ts` copies them and the gate checks for drift.
- **`scripts/capture_web.py`** (18b's file) gained `smoke_case` and one call. **`docs/img/console_case_*.png`** (P20's folder) gained two files.

## Findings and known gaps

- **Superseded contracts.** Approving a contract stores an executed child, but the parent stays `pending_approval` in the store, and Streamlit still counts it as waiting. The console treats a contract as superseded when another contract names it as `parent_id`, both in the summary count and in the contract block.
- **Outbox file names.** `/audit/recent` does not return payloads. For contracts the run executed, the file name is read from the trace's `ActionExecutor execute_action` line. For approvals made in the console, it comes from the approval response. A contract approved in another session with no trace line shows "The <action> was sent to the outbox." with no file name.
- **Role choices.** The role select offers the contract's required roles and any role seen in approvals. Only when a contract names none does it offer `tprm_analyst` and `tprm_lead` (the policy's ranked roles, which no API serves).
- **Precedents.** In sample mode with memory off, no precedents are considered, so the precedents table was exercised only in its empty state.
- **Secret history scan (blocked, outside this lane).** `tests/unit/docs/test_secrets_history.py::test_p6_t5_history_clean` fails.
  - Cause: `scripts/scan_secrets.py --history` attributes the lines of a deleted file (`+++ /dev/null`) to the previous file in the diff. Deleting an old Tailwind bundle under `web/dist/assets/` therefore reports a Tailwind mask utility class (it fits the `sk-` key pattern) against `web/dist/.source-hash`, which is not allowlisted.
  - It is a false positive: no key is involved. It affects every lane that rebuilds `web/dist` (18b's `48355ff` and `bd5ac01` delete bundles too).
  - Not changed here; raised with the human.

## Commands run

```
.venv/bin/python scripts/record_p18c_fixtures.py
cd web && npm ci && npm run check && npm run build
SAMPLE_MODE=true LLM_PROVIDER=offline .venv/bin/python run.py serve
.venv/bin/python scripts/capture_web.py --smoke --out <scratch>   # smoke: ok
.venv/bin/python scripts/tasks.py verify-pass --pass 18c           # see the secret history scan above
```
