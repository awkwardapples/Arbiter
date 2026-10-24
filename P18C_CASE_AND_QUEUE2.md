# P18-C: the Case page and the Cases queue (lane `18c`)

Branch `p18c-case` from `p18-console`, after P18-B part 1 is merged there. One PR into `p18-console` by **Sun 25, 14:00 GMT**. Sonnet or Opus.

## 1. Goal

Everything the Streamlit Case and Cases pages show today (design §9 rows "Cases" through "Technical details"), rebuilt in the console's design, plus:

- an **Agent activity** tab that replays the case's own trace on the bench (`<RunCanvas source={{kind:"events"}}>` from P18-B);
- an **Audit trail** tab with replay and the human override (after P19).

## 2. Read first

- `CLAUDE.md`
- `docs/spec/release3/README.md`
- `docs/spec/release3/P18_00_DESIGN.md` (§3, §4, §5, §9, §10, §12)
- `web/src/ui/**` and `web/src/run/RunCanvas.tsx` (from P18-B)
- `ui/case_view.py` and `ui/portfolio.py`: what is shown today, in what order, with what copy
- `app/api/routes_cases.py`, `app/api/routes_contracts.py`, `app/api/routes_review.py` (request and response shapes)
- `app/schemas/report.py`, `app/schemas/decision.py`

## 3. Deliverables

### 3.1 Cases (`/console/cases`, `web/src/pages/cases/`)

- **Summary sentence** built from `GET /cases`, for example "7 cases. 3 need the TPRM lead; 1 is waiting for the vendor; 2 approvals are waiting for sign-off."
  - "Waiting for sign-off" counts contracts in `pending_approval`. Read them from `GET /cases/{id}` for at most 40 cases, as Streamlit does today, and say so in a tooltip.
- **Filter chips** by outcome and by tier, each with its count. Filters are kept in the URL query string.
- **Table**, sorted by residual risk (server order). Columns:
  - Case: the vendor name as the primary text, with the case id below it as an `Identifier`;
  - Decision (`OutcomeBadge`);
  - Tier;
  - Residual risk, as a number with a small bar;
  - Status;
  - Created (relative time with the absolute time in a tooltip).
- **Rows** open `/console/cases/:caseId`. Keyboard: arrow keys move between rows, Enter opens.
- **Empty state:** "No cases yet. Start an assessment to see the agents work." with a **Start an assessment** button.

### 3.2 Case (`/console/cases/:caseId`, `web/src/pages/case/`, `web/src/features/case/`)

**Header:**
- vendor name (28 px);
- `OutcomeStamp`;
- the outcome meaning (from the API labels);
- Tier;
- Residual risk;
- a confidence sentence with the unverified controls in words;
- the mode chip (from the case trace's `mode`);
- the case id and run id as `Identifier`s.

Tabs use Aceternity *Animated Tabs*, recoloured.

| Tab | Content (parity with Streamlit, design §9) |
|---|---|
| **Decision** | <ul><li>The brief headline (Source Serif 4, 21 px)</li><li>The why-points: each point with both refs renders as a **claim card** (`claim` colour, vendor value, source, quote if any) beside a **record card** (`record` colour, system, record key, field, value, Zetaris request id if present), with a `≠` between them and `clash` text when they differ</li><li>Other why-points (for example KEV) are plain serif sentences</li><li>Aceternity *Tracing Beam* down the left of this column</li></ul>**Next action panel** (right column, sticky):<ul><li>recipient role, subject;</li><li>the body in an editable textarea (Source Serif 4);</li><li>**Copy** (clipboard API, with a fallback that selects the text);</li><li>**Download .txt**.</li></ul>**Contract block:**<ul><li>status;</li><li>for `pending_approval`: role select (from the policy roles in the case or contract), name, rationale (≥ 30 characters, counted live);</li><li>**Approve contract** and **Reject contract** call `POST /contracts/{id}/approve`. On success, the toast "Contract approved" and the outbox file name from the response;</li><li>for an executed contract: "Sent to the outbox: <file>"</li></ul> |
| **Evidence** | <ul><li>Controls in business terms: status (met, not met, unverified) with what would satisfy each one</li><li>"What would change this decision" (counterfactuals, de-duplicated by control)</li><li>Precedents considered (id, lead, conditions, applied or not, and why)</li><li>Facts table: control, fact in words, value, source system, and a provenance chip that opens a popover with record key, query and Zetaris request id or quote</li></ul> |
| **Agent activity** | `<RunCanvas source={{kind:"events", events: GET /cases/{id}/trace, mode}}>`, paced by default with a speed control. Under it, the workload sentence from `CaseDetail.workload` (or "The workload was not recorded for this case.") |
| **Audit trail** | <ul><li>Aceternity *Timeline*: case created; each contract issued, approved or rejected (who, role, rationale); each review; each replay done in this session</li><li>**Replay decision** (`POST /cases/{id}/replay`) shows "Decision replays identically" or the exact diff. After P19 it also shows "Machine decision replays identically; the TPRM lead overrode it to Approve with conditions on <date>: <rationale>"</li><li>**Download dossier** (HTML and Markdown)</li><li>**Open review** goes to `/console/review/:caseId` (18d)</li></ul> |
| **Technical details** | <ul><li>Reason codes with their meanings</li><li>The control table with evidence chips (ids in `Identifier`)</li><li>Contradictions (raw), counterfactuals (raw), signed contracts (ids, signature prefix, issued, expires)</li><li>The raw `CaseDetail` JSON in a collapsible viewer</li></ul>This is the only tab where codes lead |

## 4. Acceptance tests (Vitest with mocked fetch; recorded API payloads only)

Fixtures are the payloads P14-B already recorded under `tests/fixtures/ui/p14a_*` (examples 2 and 4, sample mode). Read them from the repo. **Do not hand-write API payloads.** If you need another payload, record it from a real sample-mode API call with a script and commit the script.

| Id | Test |
|---|---|
| P18C-T1 | Cases: rows sorted as the API returns them; the outcome filter in the URL filters rows; the summary sentence counts match the payload |
| P18C-T2 | Case, example 2: the stamp reads "Escalate"; the claim card shows EU and the record card shows US with `CTR-30007`; no element outside Technical details contains a reason code (regex for `[A-Z_]{8,}` and `C\d\d` at the start of text) |
| P18C-T3 | Next action: the body is editable; Download produces a `.txt` blob with the edited text |
| P18C-T4 | Contract approval: a rationale under 30 characters disables the button and never calls the API. With 30 or more, `POST /contracts/{id}/approve` is called with `{by, role, decision, rationale}` and the toast shows |
| P18C-T5 | Replay: a `{match:false, diff:["outcome"]}` payload shows the diff in words. A payload with `human_override` (P19 shape) shows the override sentence |
| P18C-T6 | Agent activity: renders `<RunCanvas>` with the trace payload; the counters match the reducer for that trace |
| P18C-T7 | Parity: a test walks the design §9 rows owned by 18c and asserts each one has a rendered element (by test id) |

## 5. Definition of done

- `npm run check` and `verify-pass --pass 18c` are green.
- Smoke extended: after the run, the Case page opens, each tab renders, and the replay shows a match.
- Screenshots `docs/img/console_case_*.png` (Decision and Agent activity) at 1440×900.

## 6. Claude Code prompt

```
/start-pass 18c
You are implementing P18-C of Arbiter Release 3: the Case page (Decision, Evidence, Agent activity, Audit trail, Technical details) and the Cases queue in the web console.
Read: CLAUDE.md; docs/spec/release3/README.md; docs/spec/release3/P18_00_DESIGN.md §3–§5, §9, §10, §12; docs/spec/release3/P18C_CASE_AND_QUEUE.md; web/src/ui; web/src/run/RunCanvas.tsx; ui/case_view.py; ui/portfolio.py; app/api/routes_cases.py, routes_contracts.py, routes_review.py; app/schemas/report.py and decision.py.
Edit only web/src/pages/case, web/src/pages/cases, web/src/features/case and new files in web/src/ui. Ask before touching anything else.
Plan first: .cursor/plans/P18-C.md with components and tests P18C-T1..T7. Wait for my approval.
Tests first → implement → smoke → screenshots → verify-pass 18c green → PR into p18-console.
Finish with docs/passes/P18-C_REPORT.md and docs/cursor-usage/P18-C.md; delete .cursor/ACTIVE_PASS; stop.
```
