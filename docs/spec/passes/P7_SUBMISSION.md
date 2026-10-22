# P7: Submission (human-led, Mon 26 PM to Tue 27)

## 1. Goal

A complete, consistent, honest submission on HackOS:

- the first version by **Mon 26 Oct 20:00 GMT**;
- the final version by **Tue 27 Oct 18:00 GMT**;
- tag `submission-final`.

## 2. Inputs

`04_SUBMISSION_PLAYBOOK.md` (all sections) and the outputs of P6.

## 3. Steps

| # | When | Step | Done when |
|---|---|---|---|
| 1 | Mon 12:00 | Run the live eval (if not done) and `python run.py eval --publish`; regenerate `python run.py examples --live` | README block and `docs/EVALUATION.md` updated by code |
| 2 | Mon 13:00 | Run `python run.py demo-session --live --reset --yes` and note the run ids for cases A, B and C | Run ids in `docs/DEMO_SCRIPT.md` |
| 3 | Mon 14:00–17:00 | **Record the video** (04 §2): shot list, then narration, then edit to ≤ 3:45, then check secrets frame by frame | MP4 named per 04 §2.4; checklist 04 §2.5 ticked |
| 4 | Mon 17:00–19:00 | **Deck** (04 §3): 13 slides covering all 8 points; screenshots from `docs/img`; numbers from `summary.json`; refreshed slides from the old research deck | PDF exported; the coverage table in 04 §3 is ticked |
| 5 | Mon 19:00 | `clean_clone_check.py` on the public repo URL | All PASS |
| 6 | Mon 19:30 | Roster check on HackOS (solo, you as primary contact), then **create the submission** with the 04 §7 worksheet text, video, deck, repo URL, sponsor explanation and pre-existing declaration | Submission v1 exists (timestamp for the tie-break) |
| 7 | Tue AM | Fix issues found; `docs/QA_PREP.md` (§4); final read of README, deck and video for consistency (same track name, same numbers, same claims) | – |
| 8 | Tue 12:00 | **Feature freeze** | – |
| 9 | Tue 16:00 | Final `clean_clone_check.py`; `scan_secrets.py --history`; video and deck links tested in a private window | All PASS |
| 10 | Tue 18:00 | Update the submission on HackOS; `git tag submission-final && git push --tags` | Confirmation screenshot saved locally |
| 11 | After | 04 §8: no pushes to `main`; watch Announcements daily; keep the environment able to re-run the demo; results call 6 Nov 16:00 GMT | – |

## 4. `docs/QA_PREP.md` (generated with me on Tuesday morning)

About 25 likely judge questions, each with a two-sentence answer and the file or trace to show. For example:

- "Where does the LLM end and the policy begin?"
- "Show me a Zetaris request id in a decision."
- "What if the vendor lies consistently across all answers?"
- "What does the Challenger actually change?"
- "How do you know the baseline was fair?"
- "What happens without Nightshift?"
- "Which parts existed before 22 October?"

## 5. Consistency checklist (README × deck × video × form × metadata.json)

- [ ] The track is "Reasoning Architecture" everywhere.
- [ ] The one-line description is identical.
- [ ] Eval numbers are identical and from the same `summary.json` (same git sha).
- [ ] The agent names and count are identical.
- [ ] Sponsor claims are identical and each is backed by a file or trace.
- [ ] The pre-existing declaration is identical in the form, README and `docs/PRIOR_WORK.md`.
- [ ] No secrets appear in any artefact (video frames, screenshots, deck, logs).

## 6. Cursor prompt (small helper tasks only)

```
/start-pass 7
Help me finish submission tasks only; no new features. Read docs/spec/04_SUBMISSION_PLAYBOOK.md and docs/spec/passes/P7_SUBMISSION.md.
Tasks I will give you one at a time: regenerate examples, publish eval, fix doc inconsistencies, generate docs/QA_PREP.md from the code and traces.
Each change: run `python scripts/tasks.py verify` before committing.
```
