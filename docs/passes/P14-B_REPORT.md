# P14-B report: the analyst console

## Built

- **Case page** (`ui/case_view.py`), top to bottom: header with the decision label and meaning, tier, residual risk, and a confidence sentence that names the unverified controls. Then the brief headline as a callout. Each why-point with both refs is a claim card beside a system-of-record card, and a mismatch is red. Then the next action, controls in business terms, a checklist of what would change the decision, precedents, the agent timeline in words, the workload sentence, and the dossier downloads (HTML and Markdown). The case id is in the page title.
- **Next action panel:** the draft's recipient and subject, the full body in an editable text area, a Copy button (a small script, since Streamlit has no clipboard API), and Download .txt. A contract in `pending_approval` shows a role select, a name and a rationale. Approve and Reject call `/contracts/{id}/approve`. A rationale under 30 characters is refused in the page and never reaches the API. An executed contract says it went to the outbox. After an approval the outbox file name comes from the API response.
- **Technical details** (one collapsed expander at the foot of the Case page) holds everything with identifiers: reason codes, the control table with its evidence chips, contradictions, counterfactuals, signed contracts, raw JSON. The earlier Case-page checks (P8, P9) still pass against it.
- **New assessment** (`ui/intake.py`): tabs *Existing vendor* (name and status; no vendor ids) and *New vendor questionnaire*; JSON paste is under an *Advanced* expander. The questionnaire has selectboxes and multiselects for criticality, category, data categories and countries, a number input for spend and the patch SLA, and the 16 questions served by `GET /questions`. Each question is a Yes / No / Not answered select plus an optional "How?" box, or a single text box for the questions a yes/no does not fit. Document and component rows use `st.data_editor`. *Load an example vendor* fills everything (two presets, 16 answers each, in `ui/presets.json`). The form builds a `CaseInput`; client-side validation names each problem and an invalid form never calls `/run`. The run shows `st.status` with the approved sentence, then the measured workload, then opens the case.
- **Cases** (`ui/portfolio.py`): totals per outcome, cases waiting for approval, filters by outcome and tier, business labels, row click opens the case.
- **Sources & semantic layer** (`ui/sources_view.py`): data mode from `/health`, a graphviz ERD of the 10 tables with the foreign-key edges, a table of descriptions, row counts and the 5 data-quality rules from the committed parity file, labelled *as of the P13 parity run (23 Oct 2026)*. Reads `data/usl/vendor_risk.model.json`, `zetaris/sql/03_usl.sql` and `docs/passes/P1-B_parity.json`, all committed. It never contacts Zetaris. If the model is missing it says to run `python run.py zetaris parity`.
- **Provider proof** (`ui/provider.py`, sidebar): live shows `Nightshift: online · <url> · token hidden`, the model served per route and the last receipt id, all read from the latest case's trace `provider_meta`. Offline shows the fallback sentence. Until P15 commits `docs/evidence/nightshift_proof.json` it says *Live Nightshift proof is produced by the P15 pass. See docs/evidence/ when it lands.* Only named fields are read, so a token in the payload cannot render.
- **`scripts/capture_ui.py`:** Playwright imported lazily (prints `pip install playwright && playwright install chromium` if missing), configurable browser path, 1440x1000, seven pages, waits for Streamlit idle, refuses to capture if a secret from the environment is visible. Not run yet: see Known gaps.
- `ui/screens.py` shrank from 675 to 479 lines by moving `page_new_assessment`, `page_queue` and `page_case` out (a mechanical move; the old bodies were removed, not edited).

## Changes outside `ui/**` (approved)

- `GET /questions` (`app/api/routes_meta.py`, model `QuestionInfo` in `app/schemas/api.py`). Texts come from `app/agents/catalogue.py`, help from the policy control that uses the question, `type` is `yes_no` when the text starts with Is, Have, Do or Will, else `text`.
- `GET /cases/{id}` returns `workload`. It was computed on `/run` and dropped, so the Case page could not show it later. `Store` gains a `workloads` table (`save_workload`, `workload_for`); the orchestrator saves the same object it returns. Older cases show *The workload was not recorded for this case.*

## Deviations from the plan and spec

- The policy has no questionnaire section, only `question_ids` per control, so `/questions` is built from the catalogue and control titles. `help` is "Used to check: <control title>" rather than prose written for the form.
- Not every question is yes/no (for example "How often…", "Where…"). Those 9 get one text box, not a select.
- Median run time is not on the Cases page: the queue API carries no run time. "Waiting for approval" is counted by reading each case's contracts (first 40 cases).
- The outcome words in `ui/labels_ui.py` duplicate `app/labels.py` because `ui/` must not import `app` (P5-T10). `test_p14b_outcome_words_match_the_api_labels` fails if they drift.
- The USL descriptions are parsed from `zetaris/sql/03_usl.sql` in the UI for the same reason (the committed model JSON has none).
- The spec's "Evaluation renders the comparison table when P15 publishes it" is not done: P15 has not published one.
- Screenshot list follows the spec's seven shots (brief, next action, questionnaire, cases, sources, precedents, audit). The brief's list was the pages; `--only` takes names if you want a different set.
- Staged progress is one `st.status` plus the measured workload afterwards. The API call is a single blocking request, so showing named stages while it runs would not be real.

## Existing tests changed

All other UI tests pass unchanged. These four files were edited, and nothing was skipped or deleted:

| File | Test | Change |
|---|---|---|
| `tests/unit/ui/test_p11.py` | `test_p11_case_section_order` | `_CASE_SECTIONS` now lists the new layout (Next action, Controls, What would change this decision, Precedents considered, Agent timeline, Workload, Dossier). It still asserts the order. |
| `tests/unit/ui/test_pages_smoke.py` | `test_p5_t11_case_page_shows_outcome_text` | Looks for the business label (`Request information`) in the headings instead of the outcome code, which the copy rule now hides. |
| `tests/unit/ui/test_polish.py` | `test_p8_spinner_text_is_the_approved_sentence` | Inspects `ui.intake.run_and_open` (the function that runs the assessment now) instead of the deleted `page_new_assessment`. Same two assertions. |
| `tests/unit/ui/conftest.py` | `FakeArbiterClient` | Added `questions()` and `dossier()`. |

## Tests

`tests/unit/ui/test_p14b.py` has P14B-T1 to T8 plus a portfolio check, a label-sync check, `/questions`, and the stored workload. Fixtures in `tests/fixtures/ui/p14a_*` and `p14b_questions.json` were recorded by running examples 2 and 4 through the P14-A API in sample mode. The test double for a live provider (served models, receipt ids, a fake credential) lives in `tests/unit/ui/p14b_support.py` and is marked as a test double. The playwright import test skips when Playwright is absent.

## Known gaps

- **No screenshots yet.** Playwright and Chromium are not installed, and I did not install them into the shared virtualenv. `docs/img/ui_*.png` are still the old files. Capture with: `python run.py serve`, `streamlit run ui/app.py`, `python run.py demo-session`, `python scripts/capture_ui.py`.
- I ran the page tests (AppTest) but have not looked at the console in a browser, so layout, colour and the Copy button are unchecked visually.
- The Copy button needs a secure context (localhost counts). The text area is the fallback.
- Provider proof for a live run is covered by a fixture, not by a real Nightshift trace.

## Commands run

```
python scripts/tasks.py verify-pass --pass 14b      # green: 764 passed, 6 skipped; secret-scan ok; hardcode-check ok
ruff check ui scripts app tests/unit/ui             # clean
```
