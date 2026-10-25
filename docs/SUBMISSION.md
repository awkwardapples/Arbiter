# Submission checklist

State on 25 October 2026, at the end of P20. A box is ticked only when the artefact exists in the repo and the path is given. **The video and the deck are not uploaded yet.** `metadata.json` `demo_video` and `slide_deck` stay empty strings until those uploads exist.

## Form text

**Project name.** Arbiter

**Track.** Reasoning Architecture

**One-line description** (identical in the README, `metadata.json`, `docs/SLIDES.md` and here; `tests/unit/docs/test_claims.py` checks it):

> Auditable reasoning for third-party vendor onboarding: agents gather cited evidence, a versioned policy decides, and the next action is a signed contract.

**Sponsor technology** (from `docs/SPONSORS.md`):

> Zetaris is the single SQL access point: five enterprise systems and the CISA KEV catalogue are onboarded as Lightning REST tables and modelled as one Unified Semantic Layer, `vendor_risk`, with DQ rules; every live query carries a request id. Meterless Nightshift runs every model call and returns a compute receipt; Meterless H-MEM holds lead-governed precedents; the Meterless Scout subset guards untrusted vendor text and signs every action as an execution contract. NVIDIA Nemotron 3.5 Super VL and Nemotron 3.5 Lightning, served through Nightshift, do the planning, claim extraction, critique and challenge. Note: a Nightshift app rule coerces both lanes to `auto`; Meterless acknowledged the bug and targeted a fix for its Sunday release, which had not reached this build on 25 October (Nightshift Console v1.2.1).

**Pre-existing components** (from `docs/PRIOR_WORK.md`):

1. Design documentation, no code: `AGENTS.md`, `docs/spec/**`, `.cursor/` rules, commands, `hooks.json` and two hook scripts, and the `docs/DAY0_CHECKS.md` template. Written 20–21 Oct 2026 with Claude (Anthropic) as architect; committed unchanged in `b3c720deca0140efe6ef53fd88e9f18474ca707c`, after the window opened.
2. Problem framing, user research and pitch narrative from the earlier prototype Vendor-Risk-Assessment-Agent (React/Node). No code reused.
3. Market-research slides (problem, users, competitors), refreshed and reused in deck slides 4 and 6.
4. Third-party material under licence: Meterless H-MEM vectors and Scout eval cases (Apache-2.0, `vendor/meterless/`), CISA KEV (CC0 1.0).
5. Data: none prepared before the window; all synthetic data comes from the seeded generator.

`docs/PRIOR_WORK.md` §1 records the tool per pass range (Cursor for P0–P14-A, Claude Code from P14-B) and links the organisers' confirmation that any IDE may be used (22 October 2026).

**Numbers to quote** (README eval block, `eval/results_live/20261025T153035975818Z/summary.json`):

- Arbiter, live: 10/10 on the first 10 test cases, 0 unsafe approvals, 4/4 consistent; 10 of 21 model calls fell back to deterministic logic (6 of 10 cases decided without a successful model call).
- Baseline: not measured. All 10 calls returned HTTP 502 from Nightshift's forced `auto` routing.
- Arbiter, offline: 16/16 on the full test split, 0 unsafe approvals.

## In the repo

- [x] Track "Reasoning Architecture" in the README badge and `metadata.json` `track`
- [x] One-line description identical across README, `metadata.json`, `docs/SLIDES.md` and this file
- [x] README rewritten in the P17 order, with the live eval block (`README.md`)
- [x] Impact case with cited sources and a labelled estimate (`docs/IMPACT.md`)
- [x] Sponsor claims, each tied to a file and a verbatim trace line (`docs/SPONSORS.md`, `metadata.json` `evidence_map`)
- [x] Models are only what ran: Nemotron 3.5 Super VL and Lightning, each with a receipt (`metadata.json` `model_evidence`)
- [x] The deep-lane deviation stated in README, SPONSORS, `metadata.json` and `docs/evidence/nightshift_deviations.md`
- [x] Live examples 2–5 (`output_examples/`, `logs/examples/live/`); examples 1 and 6 failed live twice and keep current sample-mode outputs (`logs/examples/live_failed/`); the sample-mode set (`output_examples/sample_mode/`)
- [x] Live memory session, 6/6 (`docs/evidence/memory_session.md`)
- [x] Clean-clone check, 8/8 with Docker (`docs/passes/clean-clone-2026-10-24.md`); re-run after the P20 merge
- [x] Zetaris USL parity green (`docs/passes/P1-B_parity.json`)
- [x] Demo script (`docs/DEMO_SCRIPT.md`), deck outline (`docs/SLIDES.md`), judge Q&A (`docs/QA_PREP.md`)
- [x] Per-pass tool and model record (`docs/CURSOR_USAGE.md`)
- [x] Web console served by the API at `/console/` (`web/dist/`), screenshots in `docs/img/console_*.png`
- [ ] A measured live baseline: blocked on the Nightshift routing fix, which had not reached this build on 25 October
- [ ] USL ERD screenshot from the Zetaris UI: not committed

## Video

Record from `docs/DEMO_SCRIPT.md`. Target 3:35, hard stop 3:50.

- [ ] Video recorded
- [ ] Track, user and problem stated in the first 20 seconds
- [ ] Live shots are the Quillfeather run (live on the day, or the recording of `run-211916c1544d` with its date), the proof, the memory session and the eval
- [ ] The Nightshift proof shot shows both receipt ids and routed models, and the deviation is said aloud
- [ ] No model named other than Nemotron 3.5 Super VL and Nemotron 3.5 Lightning; no baseline "win"
- [ ] No secrets in any frame (no `.env`, no Nightshift providers tab, no Zetaris API-keys page)
- [ ] Video uploaded (HackOS, plus an unlisted backup)

## Deck

Build from `docs/SLIDES.md` (23 slides) and export a PDF.

- [ ] Deck built
- [ ] Rubric coverage table in `docs/SLIDES.md` honoured; all eight required points present
- [ ] Every statistic carries its source
- [ ] Eval numbers match the README block
- [ ] Monitoring appears only on slide 22, as future work
- [ ] Deck PDF uploaded

## After upload

- [ ] Paste the two URLs into `metadata.json` `demo_video` and `slide_deck` only
- [ ] Replace the README "Demo video" line with the link
- [ ] Create the HackOS submission with the form text above
- [ ] Run `python scripts/clean_clone_check.py` against the public repository URL
- [ ] Tag `submission-final` and push the tag
- [ ] Keep the video and the deck reachable through 6 Nov 2026
