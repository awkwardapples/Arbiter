# Submission checklist

Nothing here is a recorded video, an uploaded deck, or a HackOS submission. Boxes stay open until that artefact exists. Notes marked **in repo** are true of the tree today. They are not ticks for the video or the form.

`metadata.json` fields `demo_video` and `slide_deck` are empty strings. Leave them empty until the uploads exist, then set only those two values.

## In the repo

- **Track.** `Reasoning Architecture` is the README badge and `metadata.json` `track`. **in repo**
- **One-line description.** The deck and `docs/DEMO_SCRIPT.md` use the README sentence: "Auditable reasoning for third-party vendor onboarding: agents gather cited evidence, a versioned policy decides, and the next action is a signed contract." `metadata.json` `description` is a longer sentence. They are not the same string. Pick one before the form is submitted. This pass does not change `metadata.json`.
- **Eval numbers.** README block between the eval markers is `eval/results/20261022T080517661769Z/summary.json`: offline, n=15, `arbiter_offline` accuracy 15/15, unsafe approvals 0/15, git sha `a7228be2efe2bca9f004f981db12c1e8dd53704f`. That file has no second system. **in repo**
- **Console eval page.** `docs/img/ui_5.png` says results are not published yet. Do not quote it as the eval. **in repo**
- **Screenshots.** `docs/img/ui_1.png` through `docs/img/ui_6.png` exist. Sidebar on those frames: Data: zetaris, LLM: auto. Later frames use CASE-0007. The six committed traces are DuckDB / offline, and example 1 is CASE-0003. **in repo**
- **Agent names.** README "Agents" lists Orchestrator plus Planner, Evidence, Evaluator, PolicyEngine, MemoryKeeper, Challenger, Reporter, ScoutGuard, and ActionExecutor. `metadata.json` `agents` has those names except Orchestrator. The counts differ. Align them on the form, the deck, and the video before submit.
- **Sponsor claims.** `docs/SPONSORS.md` ties each claim to a file and a trace line from the offline examples. Those lines do not show a Zetaris request id or a Nightshift model id. **in repo**
- **Pre-existing declaration.** README "Pre-existing components" points at `docs/PRIOR_WORK.md`: design docs from 20–21 Oct 2026, the Vendor-Risk-Assessment-Agent narrative with no code reused, market-research slide material, Meterless vectors (Apache-2.0), CISA KEV (CC0). Compare that list with the form text in `docs/spec/04_SUBMISSION_PLAYBOOK.md` §7 before submit.
- **URL placeholders.** `demo_video` and `slide_deck` are `""`. **in repo**
- **Video and PDF.** Not in the repo. The script is `docs/DEMO_SCRIPT.md`. The outline is `docs/SLIDES.md`.

## Video

Record from `docs/DEMO_SCRIPT.md`. Target about 3:30, hard stop 3:45. File name from the playbook: `OAH2026-Arbiter-ReasoningArchitecture-Demo.mp4`.

- [ ] Length is between 1:00 and 3:45
- [ ] Track, user, and problem are stated in the first 20 seconds
- [ ] At least two agents interact, including one loop line in a trace (`needs_revision` on `run-3d6b7460d393` if the offline sample is what you show)
- [ ] Zetaris is shown doing work, or the narration says this sample used the DuckDB mirror and names `zetaris/sql/03_usl.sql`
- [ ] Meterless is shown doing work, or the narration says `provider=offline` on this sample and names Nightshift, H-MEM, and Scout as the live engines
- [ ] The final output is on screen, and the close says why it matters
- [ ] No secrets in any frame (no `.env`, no Nightshift Providers tab, no Zetaris API-keys page)
- [ ] Spoken numbers match `eval/results/20261022T080517661769Z/summary.json` (15/15, 0 unsafe approvals, offline). No baseline figure.

## Deck

Build 10 slides from `docs/SLIDES.md` (within 8–12). Export a PDF.

- [ ] All eight required points appear (coverage table in `docs/SLIDES.md`)
- [ ] On-slide text is about 30 words, with the README one-liner on the title slide
- [ ] Eval numbers match the same `summary.json` as the video and the README
- [ ] Screenshots are the six `docs/img/ui_*.png` files, with the honesty notes from slide 9
- [ ] No keys and no real personal data
- [ ] PDF exported

## Consistency across README, deck, video, form, and metadata.json

- [ ] The track is "Reasoning Architecture" everywhere
- [ ] The one-line description is the same string everywhere (README and `metadata.json` differ today; see above)
- [ ] Eval numbers are the same and come from `eval/results/20261022T080517661769Z/summary.json`
- [ ] Agent names and count match (README includes Orchestrator; `metadata.json` does not)
- [ ] Sponsor claims match, and each one used on the form is backed by a file or a trace in `docs/SPONSORS.md`
- [ ] The pre-existing declaration matches the form, the README, and `docs/PRIOR_WORK.md`
- [ ] No secrets in the video, the screenshots, the deck, or the logs

## Still to do by hand

- [ ] Record the video
- [ ] Upload the video (HackOS, plus an unlisted backup) and the deck PDF
- [ ] Paste the two URLs into `metadata.json` `demo_video` and `slide_deck` only
- [ ] Put the video link in the README under the existing "Demo video" line (that line still says it is not published)
- [ ] Create the HackOS submission from the playbook §7 worksheet, after the roster shows only you
- [ ] Run `python scripts/clean_clone_check.py` on the public repo URL
- [ ] Tag `submission-final` and push the tag when the final submission is in
- [ ] Keep the video and the deck reachable through 6 Nov 2026

`docs/QA_PREP.md` is the Tuesday question list from the pass. It is not part of this checklist's documents.
