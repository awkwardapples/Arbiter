# P19: fixes a judge would find (lane `19`)

Branch `p19-fixes` from `main`. One PR into `main` by **Sat 24, 18:00 BST**. Sonnet. Independent of P18: the Streamlit fallback gets better too.

Each item cites its finding in `R3_00_ASSESSMENT.md`.

## F1: Zetaris time in IMPACT (C1)

- `docs/IMPACT.md` §3: "33 s of Zetaris time" becomes "16.6 s of Zetaris time".
  - That is the sum of `latency_ms` over the 12 `data/query_zetaris` events in `logs/examples/live/trace-run-83de5da137c0.jsonl`.
  - Each query is logged twice: count the `query_zetaris` events only.
- **Test** `tests/unit/docs/test_impact_numbers.py` recomputes it from the trace and checks the sentence.

## F2: Replay of human-reviewed cases (B10, C2)

Today:
1. `POST /cases/{id}/review` replaces the stored decision with a copy whose `outcome` is the reviewer's and whose `outcome_reasons` is `["HUMAN_REVIEW"]`.
2. Replay re-decides the machine inputs, gets the machine outcome, and reports `match: false`.

Fix:
- `app/store.py` ✎ (additive): keep the **machine** record when a review overwrites it. Use a `machine_decisions` table keyed by `case_id`, written once, the first time a review replaces the record.
  - Cases reviewed before this change have no machine record. Replay reconstructs it by re-deciding, and says so.
- `app/audit/replay.py` ✎: when the stored record's `outcome_reasons == ["HUMAN_REVIEW"]`:
  1. replay the **machine** record exactly as today (policy hash, record hash, facts, outcome);
  2. verify the latest review exists, its `decision` equals the stored outcome, and its role is allowed by the policy for that outcome;
  3. return `match = machine_ok and review_ok`.
- **`ReplayResult` gains** (additive):
  - `human_override: {reviewer, role, decision, rationale, review_id, at} | None`;
  - `machine_outcome: str | None`.
- `python run.py replay` prints, for example: "Machine decision ESCALATE replays identically. Overridden by tprm_lead (lead.reviewer@example.com) to APPROVE_WITH_CONDITIONS: Bridge letter accepted…".
- **Tests:**
  - run the sample memory session;
  - replay CASE-0011 → `match: true`, `machine_outcome: ESCALATE`, `human_override.decision: APPROVE_WITH_CONDITIONS`;
  - tamper with the stored human record's outcome → `match: false`;
  - CASE-0003 (no review) is unchanged.

## F3: PRIOR_WORK (C3), with your wording

`docs/PRIOR_WORK.md` §1 "How". Claude Code proposes the edit; you approve the text, because this is your declaration on the form.

- Remove the reference to the missing `docs/CLAUDE_CODE_USAGE.md`. Point to `docs/CURSOR_USAGE.md`, which already tabulates the tool per pass.
- Make the pass ranges match the README: P0–P14-A in Cursor; P14-B onwards in Claude Code.
- Fix "completly", "All Application" and the double spaces.
- Add one sentence: Release 3's specs and review were drafted by Claude (Anthropic) outside the repo, like Releases 1 and 2.

## F4: Evaluation page and `GET /eval/latest` (C8, B11)

- `app/api/routes_meta.py` ✎: `GET /eval/latest` returns
  `{live: <latest eval/results_live/*/summary.json> | null, offline: <latest eval/results/*/summary.json> | null, live_markdown, offline_markdown}`.
  - 404 only if both are missing.
  - It reads only `eval/results_live` and `eval/results`: summaries, never labels.
- `ui/screens.py` ✎: the Evaluation page calls `client.eval_latest()` first and renders the **live** table first, then the offline one. Remove the hard-coded `EVAL_SUMMARY_PATH`.
- `.dockerignore`: leave `eval/results` excluded. The live results are included, which is what matters in Docker.
- **Tests:** the endpoint returns the 24 Oct live summary (three systems), and the Streamlit page test renders "arbiter" with n = 5.

## F5: Streamlit fallback polish (C7, C9, B12)

- `ui/screens.py`: the run spinner reads "Running the assessment. Sample mode takes a few seconds; a live run takes about 2–4 minutes (measured median 142 s)."
- `ui/provider.py`: `_served()` prefers the event's `model`, then `provider_meta.routed_model`, then `winning_route.model`. Never `provider_model`, which is the routing mode `meterless/auto`.
  - **Test:** with the live trace, the sidebar shows `nvidia/nemotron-3.5-super-vl-120b-a12b`.
- `.streamlit/config.toml` (new):

  ```toml
  [client]
  toolbarMode = "minimal"
  ```

  This hides the Deploy button. If the "Help agents write better apps" popover still appears in your Streamlit version:
  - `scripts/capture_ui.py` clicks "Don't show again" before capturing;
  - re-capture the stills.

## F6: Direct-NVIDIA default model (C11)

`app/config.py` ✎: the default for the direct-NVIDIA deep model becomes `nvidia/nemotron-3.5-super-vl-120b-a12b`, the entitled model. Update `.env.example` to match. **Test:** `/health` in sample mode no longer names `nemotron-3-super-120b-a12b`.

## F7: Flaky first AppTest (B13)

`tests/unit/ui/test_p10.py::test_p10_new_assessment_how_to_use`: pass `default_timeout=15` to `AppTest.from_file` (or `.run(timeout=15)`). Do the same for any other AppTest that runs first in its module.

## F8: Brief headline wording

`app/labels.py` builds `f"{outcome_label} to {_AUDIENCE[outcome]}: {detail}"`, which gives "Request information to the vendor:", "Decline to the business owner:" and, whenever an approval has why-points, "Approve to the approval record:" / "Approve with conditions to the approval record:". Use a phrase per outcome instead:

| Outcome | Headline starts |
|---|---|
| ESCALATE | "Escalate to the TPRM lead:" (unchanged) |
| REQUEST_INFO | "Ask the vendor for more information:" |
| DECLINE | "Decline, and tell the business owner:" |
| APPROVE_WITH_CONDITIONS | "Approve with conditions:" |
| APPROVE | "Approve:" (the no-points form "Approve: <vendor> meets the checks…" is unchanged) |

- Update the tests that assert the old strings, listing each one in the report.
- Regenerate `tests/fixtures/ui/p14a_*` only with the existing recording script, never by hand.
- **Do not** regenerate committed `output_examples/` here; P20 does that.

## Acceptance tests (marker `p19`)

| Id | Test |
|---|---|
| P19-T1 | F1 number recomputed from the trace |
| P19-T2 | F2: CASE-0011 after the sample memory session replays `match: true` with `human_override`; a tampered human record fails; an unreviewed case is unchanged |
| P19-T3 | F4 endpoint, and the Streamlit Evaluation page shows the live table |
| P19-T4 | F5 provider sidebar names the served Nemotron model; the spinner copy says 2–4 minutes |
| P19-T5 | F6 `/health` default model |
| P19-T6 | F8 headlines for all five outcomes on the six sample examples |

## Claude Code prompt

```
/start-pass 19
You are implementing P19 of Arbiter Release 3: fixes F1–F8 from docs/spec/release3/P19_FIXES.md (findings C1–C3, C7, C8, C11 and B10–B13 in R3_00_ASSESSMENT.md).
Read: CLAUDE.md; docs/spec/release3/README.md; docs/spec/release3/R3_00_ASSESSMENT.md §3–§4; docs/spec/release3/P19_FIXES.md; app/audit/replay.py; app/api/routes_review.py; app/store.py; app/api/routes_meta.py; app/labels.py; ui/screens.py; ui/provider.py.
F3 changes my declaration: propose the exact text and wait for my approval before writing it.
Plan first: .cursor/plans/P19.md with each fix, the files and tests P19-T1..T6. Wait for my approval.
Tests first (marker p19) → implement → verify-pass 19 green → PR into main.
Finish with docs/passes/P19_REPORT.md and docs/cursor-usage/P19.md (tool: Claude Code); delete .cursor/ACTIVE_PASS; stop.
```
