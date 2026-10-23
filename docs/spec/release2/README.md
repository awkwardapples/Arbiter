# Release 2: from working system to winning submission

## Import (one commit, before any Release 2 lane)

```bash
cd ~/arbiter && git switch main && git pull
git switch -c r2-spec
# Run these in Cursor's terminal so the commit goes through Cursor; the README's AI-usage note (P17) discloses that the patch was drafted by Claude
git apply --index /path/to/release2.patch       # adds docs/spec/release2/ and the tooling changes below
python scripts/tasks.py verify                   # must be green (the Docker test is now opt-in)
git commit -m "docs: Release 2 assessment and pass specs; tooling for lanes 13-17"
gh pr create --fill && gh pr merge --merge --delete-branch
```

The patch also changes tooling:

- extends `PASS_IDS`, the stop hook's `VALID_IDS`, `/start-pass` and the pytest markers for lanes 13–17;
- points `AGENTS.md` at `docs/spec/release2/`;
- fixes findings B5 and B6: the clean-clone test is opt-in with `ARBITER_DOCKER_TESTS=1`, and `scripts/clean_clone_check.py` writes `docs/passes/` only with `--evidence`.

Read `R2_00_ASSESSMENT.md` first. It records why `fbb5cdc` is not submission-ready and which file each finding comes from. Release 2 does **not** change the architecture. It closes five gaps, in order of marks at stake:

| Gap | Rubric lines hit | Pass |
|---|---|---|
| No Zetaris Unified Semantic Layer (explicit Zetaris judging requirement) and no USL reflection | Sponsor Tech, Impact (track consistency), Innovation | **P13** (attended) |
| Decisions shown to the analyst contain contradictions and engineer codes; confidence is wrong on UNKNOWN controls | Technical, Product & UX, Impact | **P14-A** (backend), **P14-B** (console) |
| No committed live evidence: no Nemotron model id, no Nightshift receipt, no Zetaris request id, no baseline comparison, deep lane coerced to Lightning | Sponsor Tech, NVIDIA award, Technical, Demo | **P15** (attended) |
| Memory and "act" story invisible; thin real-world loop | Innovation, Impact | **P16** (stretch: continuous KEV monitoring that re-opens cases using memory) |
| Impact case, README, deck and video script built around caveats | Impact, Demo, all criteria | **P17** |

## Schedule (UK time; clocks go back Sun 25 Oct 02:00)

| When | Slot 1 | Slot 2 | Slot 3 |
|---|---|---|---|
| Fri 23, 13:00 | **P13** USL (you attend: Zetaris) | **P14-A** decision quality and analyst brief | – |
| Fri 23, evening | P13 continues; merge P14-A | – | – |
| Sat 24, 08:00 | P13 finish and merge (if not done) | **P14-B** analyst console | **P16** monitoring (stretch) |
| Sat 24, 14:00 (after P13 and P14-A merged) | **P15** live evidence (you attend: Nightshift and Zetaris) | P14-B continues | P16 continues |
| Sun 25 | P15: live eval (~1 h of Nightshift calls), live examples, memory session, clean-clone PASS | **P17** docs (start once P15 numbers exist) | – |
| Mon 26 | P17 finish; **record video**; build deck (Slides) | **First submission 20:00** | – |
| Tue 27 | Polish only; freeze 12:00; **final submission 18:00 GMT** | | |

Merge order: P14-A → P13 (either order; no shared files) → P14-B → P15 → P16 → P17.

## Lane ids, branches, markers

| Lane | File | Branch | Marker | Suggested model |
|---|---|---|---|---|
| 13 | `P13_ZETARIS_USL.md` | `p13-usl` | `p13` | Claude (attended) |
| 14a | `P14_DECISION_QUALITY_AND_CONSOLE.md` §A | `p14a-decision` | `p14a` | Claude |
| 14b | `P14_DECISION_QUALITY_AND_CONSOLE.md` §B | `p14b-console` | `p14b` | Composer / Grok |
| 15 | `P15_LIVE_EVIDENCE.md` | `p15-live` | `p15` | Claude (attended) |
| 16 | `P16_MONITORING.md` | `p16-monitor` | `p16` | Claude or Grok |
| 17 | `P17_IMPACT_AND_SUBMISSION.md` | `p17-submission` | `p17` | Claude |

Use `/start-pass 13` etc. exactly as before. The import commit of this pack extends `PASS_IDS`, the stop hook's `VALID_IDS` and the pytest markers, so everything works unchanged.

## File ownership (Release 2)

| Lane | Owns (creates or edits) |
|---|---|
| 13 | `zetaris/**`, `app/data/zetaris.py`, `app/data/registry.py` ✎ (USL layer resolution only), `app/data/queries.yaml` ✎ (add `Q_VENDOR_360`; USL-layer SQL overrides), `app/data/usl_model.py` (new), `data/usl/**` (new), `app/agents/planner.py` ✎ (semantic catalogue in the prompt only), `app/llm/prompts/plan.md` ✎, `app/cli/zetaris.py`, `docs/ZETARIS_USL.md` (new), `docs/img/zetaris_*`, `docs/passes/P1-B_parity.json`, `tests/unit/zetaris/**`, `tests/unit/usl/**`, `tests/live/test_zetaris_*` |
| 14a | `app/policy/engine.py` ✎ (reasons only), `app/policy/counterfactuals.py` ✎, `app/confidence.py`, `app/agents/reporter.py`, `app/llm/prompts/report.md`, `app/schemas/report.py` ✎ (additive), `app/schemas/api.py` ✎ (additive `workload`), `app/orchestrator.py` ✎ (workload counters only), `app/labels.py` (new), `app/dossier.py` (new), `app/api/routes_cases.py` ✎ (dossier route), `app/cli/dossier.py` (new), `policy/calibration/**` (re-calibration if needed), `tests/unit/{policy,reporter,dossier,labels}/**`, `tests/e2e/**` ✎ |
| 14b | `ui/**`, `scripts/capture_ui.py` (new), `docs/img/ui_*`, `tests/unit/ui/**` |
| 15 | `app/llm/providers/meterless.py` ✎ (provider meta only), `app/cli/llm.py` ✎ (`proof`), `app/cli/examples.py` ✎, `output_examples/**`, `logs/examples/**`, `eval/**` ✎ (labels and harness fixes), `data/evals/labels.jsonl` + `splits.json` (regenerated by the generator fix in `data/generator/**` ✎), `docs/evidence/**` (new), `docs/EVALUATION.md`, `docs/passes/clean-clone-*.md`, `tests/unit/docker/**`, `tests/unit/llm/**`, `tests/unit/eval/**` |
| 16 | `app/monitor.py`, `app/cli/monitor.py`, `app/api/routes_monitor.py` (all new), `app/api/main.py` ✎ (one include line), `app/facts.py` ✎ (KEV `date_added ≤ as_of` only), `app/schemas/api.py` ✎ (additive `RunOptions.as_of`, `trigger`; coordinate with 14a, which merges first), `data/monitor/**`, `tests/unit/monitor/**` |
| 17 | `README.md`, `metadata.json`, `docs/{IMPACT,SPONSORS,ARCHITECTURE,DEMO_SCRIPT,SLIDES,SUBMISSION,QA_PREP,CURSOR_USAGE}.md`, `tests/unit/docs/**` |

Everyone: `docs/passes/<LABEL>_REPORT.md`, `docs/cursor-usage/<LABEL>.md` and their own gate `scripts/gates/p<ID>.py` (optional; `verify-pass` skips a missing gate).

## Definition of submission-ready (P17 gate; all must hold)

1. The USL `vendor_risk` is activated in Zetaris. `docs/passes/P1-B_parity.json` is `all_green: true`, including DQ. `docs/ZETARIS_USL.md` exists with measured comparisons.
2. `output_examples/` and `logs/examples/live/` come from **live** runs:
   - every example trace passes `check_trace --require-live --require-collaboration`;
   - traces show Nemotron model ids and Nightshift receipt ids.
3. `docs/evidence/nightshift_proof.json` shows `meterless/fast` → Nemotron 3.5 Lightning and `meterless/deep` → Nemotron 3 Super (or the deviation is stated plainly).
4. The live eval in the README compares **arbiter (live) vs single-LLM baseline (live) vs arbiter_offline** on test + inline, with consistency.
5. No analyst-facing surface shows reason codes, fact ids or query ids without a plain-English label. No outcome lists `ALL_REQUIRED_CONTROLS_MET` unless it decided the outcome.
6. A committed clean-clone report passes all 8 steps, with Docker.
7. Every capability in `metadata.json` and `docs/SPONSORS.md` maps to an existing file and, for live claims, a committed trace line (`tests/unit/docs/test_claims.py`).
