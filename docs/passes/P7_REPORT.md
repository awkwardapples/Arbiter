# P7 report

## Built

P7 delivered the submission documents. No application code.

- `docs/DEMO_SCRIPT.md` — the existing offline narration, plus the commands that start the demo (`python run.py serve`, then `python run.py ui`) and callouts for `docs/img/ui_1.png` through `docs/img/ui_6.png`.
- `docs/SLIDES.md` — a 10-slide deck outline covering the eight required points.
- `docs/SUBMISSION.md` — the checklist for the video, the deck, consistency, and the uploads still to do.

`docs/cursor-usage/P7.md` records the lane. `metadata.json` was not edited.

## Deviations

The stills in `docs/DEMO_SCRIPT.md` are from CASE-0007, on the live path (sidebar Data: zetaris, LLM: auto). The traces the script reads aloud are the offline sample runs (`provider: offline`, DuckDB), and example 1 is CASE-0003. The stills and the traces are different sessions. They are not a disagreement about one run.

`docs/SLIDES.md` slide 10 takes its eval numbers from the README block: 15/15 offline, 0 unsafe approvals. It does not take them from `docs/img/ui_5.png`, which says evaluation results are not published.

## Known gaps

- The video is not recorded.
- The deck is not assembled. `docs/SLIDES.md` is an outline, not a PDF.
- `metadata.json` `demo_video` and `slide_deck` stay empty until the files are uploaded.

## Not touched

`app/`, `tests/`, `eval/`, `output_examples/`, and `logs/examples/` were not edited. `docs/EVALUATION.md` and `scripts/` were not edited either.

## Commands

`python scripts/tasks.py verify-pass --pass 7` is green: 616 passed, 5 skipped. No tests are marked `p7`. The first run failed because the sandbox could not open the Docker socket. The rerun with the daemon reachable passed.
