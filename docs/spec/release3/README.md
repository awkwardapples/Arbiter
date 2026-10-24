# Release 3: show the agents working, prove it live, fix what a judge would find

Read `R3_00_ASSESSMENT.md` first: it records the state of `main` at `fd1b19e`, the claims that are wrong (C1–C11), the bugs (B10–B13) and the scoring. Release 3 changes **no** decision logic. It adds a console, a few honest trace events, and live evidence.

| Pass | What | Lane id | Branch | Merges into | Tool and model |
|---|---|---|---|---|---|
| **P18-A** | Streaming and read API for the console; three new trace events | `18a` | `p18a-stream-api` | `main` (additive and safe) | Claude Code, Sonnet or Opus |
| **P18-B** | Web console foundation, then the **live run view** (the hero) | `18b` | `p18b-run-view` | `p18-console` | Claude Code, **Opus** |
| **P18-C** | Case page and Cases queue in the web console | `18c` | `p18c-case` | `p18-console` | Claude Code, Opus or Sonnet |
| **P18-D** | Sources and USL, Provider, New assessment, Memory and Review, Audit, Evaluation | `18d` | `p18d-pages` | `p18-console` | Claude Code, Sonnet |
| **P19** | Fixes: C1–C3, C7, C8, C11; B10–B13; the Streamlit fallback | `19` | `p19-fixes` | `main` | Claude Code, Sonnet |
| **P20** | Live re-run after the Nightshift fix; docs, screenshots, demo script (attended) | `20` | `p20-live` | `main` | Claude Code, Opus (attended) |

Shared design for all P18 lanes: `P18_00_DESIGN.md`. Read it before any P18 work.

## 1. Import (one commit, before any Release 3 lane)

The pack is one patch on top of `fd1b19e`. Apply it from Claude Code's terminal, or any terminal, in your repo:

```bash
cd ~/arbiter && git switch main && git pull
git tag -a fallback-streamlit-v1 -m "Submittable state before Release 3 (fd1b19e)" fd1b19e
git push origin fallback-streamlit-v1
git switch -c r3-spec
git apply --index /path/to/release3.patch
python scripts/tasks.py verify          # must be green
git commit -m "docs: Release 3 assessment and pass specs; Claude Code tooling for lanes 18a-20"
gh pr create --fill && gh pr merge --merge --delete-branch
git switch main && git pull
git switch -c p18-console && git push -u origin p18-console     # integration branch for the web lanes
```

The patch adds:

- **This folder** (`docs/spec/release3/`).
- **`CLAUDE.md`**, which Claude Code reads automatically. It imports `AGENTS.md` and adds the Claude Code workflow.
- **`.claude/` tooling:**
  - `/start-pass` and `/verify-pass` commands;
  - a Stop hook that re-runs `verify-pass` while a lane is in `build` (the Cursor stop-hook loop, ported);
  - a Bash guard that reuses `.cursor/hooks/shell_guard.py` (no reading `.env`, no port 8889, no force-push);
  - deny rules so Claude Code cannot read `.env` files.
- **Registration of the new lane ids**: lane ids `18a 18b 18c 18d 19 20` in `PASS_IDS`, the hook's `VALID_IDS` and the pytest markers.
- **Corrected attribution wording (C10):**
  - in `AGENTS.md` and `.cursor/rules/20-integrity.mdc`, Cursor built P0–P14-A and Claude Code builds from P14-B on.

## 2. Schedule (UK time; clocks go back Sun 25 Oct 02:00 BST → 01:00 GMT)

Deadline: **Tue 27 Oct 23:45 GMT**. The plan submits a complete entry on Monday night and keeps Tuesday for polish only.

| When | Window 1 | Window 2 | Window 3 |
|---|---|---|---|
| **Sat 24, 12:00–15:30 BST** | **18a** stream API | **18b part 1**: scaffold, tokens, shell, API client, static serving | **19** fixes |
| **Sat 24, 15:30–23:30 BST** | 18a review → merge to `main`; merge `main` into `p18-console` | **18b part 2**: the live run view (bench graph, activity, inspector, pacing, recordings) | **18c** Case and Cases (starts once 18b part 1 is on `p18-console`) |
| **Sun 25, 09:00–14:00 GMT** | **20** live re-run, as soon as the Nightshift release lands (attended; Nightshift and Zetaris up) | 18b polish | **18d** remaining pages |
| **Sun 25, 18:00 GMT** | **Gate A**: feature-complete on `p18-console` (§3). Capture screenshots. Fix list | | |
| **Mon 26, 10:00 GMT** | **Gate B**: merge `p18-console` → `main`, or not (§3) | 20: docs refresh for whichever console ships | – |
| **Mon 26, 12:00–18:00 GMT** | Record the video (`docs/DEMO_SCRIPT.md` from P20); build the deck (Slides) | | |
| **Mon 26, 20:00 GMT** | **First complete submission** (form, repo, video, deck) | | |
| **Tue 27** | Polish only. Freeze 12:00. **Final submission by 18:00 GMT** | | |

If the Nightshift fix has not shipped by **Sun 25, 16:00 GMT**, P20 runs its "no fix" branch (P20 §3). Do not wait longer than that.

## 3. Gates

**Gate A (Sun 25, 18:00 GMT): feature complete.** On `p18-console`, all of these hold:

1. `python scripts/tasks.py verify` and `verify-pass` for 18b, 18c and 18d are green. `npm run check` in `web/` is green.
2. `python scripts/capture_web.py --smoke` passes against `SAMPLE_MODE=true python run.py serve`:
   - Example 2 runs in the console;
   - the bench fills in;
   - the ruling reads Escalate;
   - the Case page opens;
   - a recorded live run replays.
3. The parity checklist in `P18_00_DESIGN.md` §9 is ticked, or each unticked row is reachable in the Streamlit console and listed.

**Gate B (Mon 26, 10:00 GMT): ship or hold.** Merge `p18-console` into `main` only if all of these hold:

1. Gate A holds.
2. A live run of example 2 (Quillfeather) completed in the web console on your machine against Zetaris and Nightshift. It does not need to be flawless; fallbacks are fine and shown.
3. `docker build` and `docker run -e SAMPLE_MODE=true` serve the console at `http://localhost:8000/` (from the clean-clone script, step 3 plus a GET of `/console/`).
4. You have looked at every page at 1440×900 and at 1280×720 (the video size) and nothing is broken or empty.

If Gate B fails, **do not merge**:

- `main` stays the Streamlit console, plus P18-A, P19 and P20 (all independent).
- The video uses the Streamlit console and the recorded-run evidence.
- The web console can still be mentioned as "in progress on branch `p18-console`". Do not show it in the video.

## 4. Fallback and revert

- **Tag before you start:** `fallback-streamlit-v1` at `fd1b19e` (§1). It is always a submittable state.
- **Nothing is deleted.** `ui/` (Streamlit) is untouched by P18. `python run.py ui` keeps working. P19 fixes its copy and the Evaluation page, so the fallback improves too.
- **The web console is additive:** `web/`, `app/api/routes_stream.py`, `app/api/routes_evidence.py`, `app/api/routes_web.py`, three `include_router` lines.
  - The static mount activates only if `web/dist/index.html` exists. With no `web/`, `main` behaves as today.
- **One merge commit.** `p18-console` reaches `main` as a single merge. To undo after merging: `git revert -m 1 <merge-sha> && git push`. That is one commit and one minute.
- **The judge path does not depend on Node.**
  - `web/dist/` (the built console) is committed, so `docker build` stays Python-only, exactly as the passing clean-clone report.
  - A test fails if `web/dist/` is stale against `web/src/` (P18-B).

## 5. Parallel work in Claude Code (VS Code)

Claude Code has no Cursor "lanes", so use one VS Code window per git worktree, each with its own Claude Code session:

```bash
cd ~/arbiter
git worktree add ../arbiter-18a -b p18a-stream-api main
git worktree add ../arbiter-19  -b p19-fixes      main
git fetch && git worktree add ../arbiter-18b -b p18b-run-view origin/p18-console
# later, once 18b part 1 is merged into p18-console:
git worktree add ../arbiter-18c -b p18c-case  origin/p18-console
git worktree add ../arbiter-18d -b p18d-pages origin/p18-console
```

In each window:

1. Create the venv once: `python -m venv .venv && python scripts/tasks.py setup`.
   - **Windows:** `.venv\Scripts\python`. Run `npm ci` in `web/` once it exists.
2. In Claude Code, type `/start-pass 18a` (or the window's lane id). The command reads `CLAUDE.md` → `AGENTS.md` → this README → the pass file, writes `.cursor/ACTIVE_PASS` and produces a plan.
3. Approve the plan.
4. The Stop hook re-runs `verify-pass` until green, or until it gives up after 6 loops and hands back to you.

**If the hooks do not run.**
- Type `/hooks` in Claude Code to see what is registered for this project; project hooks run only after you trust the folder.
- The hook commands call `python`. On Windows, if that is not on the PATH Claude Code's shell sees, change `python` to `py -3` in `.claude/settings.json`. The hook scripts find `.venv` themselves.
- Without hooks, end each build session with `/verify-pass`.

Review each PR before merging:

- Paste `Review <lane> <PR url>` back to me and I will review it as before.
- Or run Claude Code's `/review` in a fresh session.
- **Merge, never rebase.**

**Usage limits.**
- Spend Opus on 18b (the hardest lane) and on P20 (attended judgement calls).
- Sonnet is enough for 18a, 18c, 18d and 19.
- If a session hits its limit mid-lane, the plan file plus `git log` let a fresh session continue: `/start-pass <id>` detects an existing plan and resumes in `build`.

## 6. File ownership (Release 3)

| Lane | Owns (creates or edits) |
|---|---|
| 18a | **New:** `app/api/routes_stream.py`, `app/api/routes_evidence.py`, `app/api/routes_web.py`, `app/api/agent_roster.py`, `app/runhub.py`. **Edits:** `app/api/main.py` ✎ (three includes plus dev CORS); `app/llm/generator.py` ✎ (`model_request` event only); `app/agents/evaluator.py` ✎ (`contradiction_found` event only); `app/orchestrator.py` ✎ (`PolicyEngine decide` event only); `docs/trace_schema.json` (regenerated if the schema test needs it); `.dockerignore` ✎. **Tests:** `tests/unit/api/test_p18a_*.py`, plus existing trace-sequence tests updated with justification |
| 18b | `web/**` except the page folders 18c and 18d own; `scripts/capture_web.py` (new); `scripts/tasks.py` ✎ (`web-build`, `web-check`); `scripts/check_hardcoding.py` ✎ (scan `web/src`); `scripts/gates/p18b.py`; `tests/unit/web/**` |
| 18c | `web/src/pages/case/**`, `web/src/pages/cases/**`, `web/src/features/case/**`; `scripts/gates/p18c.py` |
| 18d | `web/src/pages/{sources,provider,new,memory,review,audit,evaluation}/**`, `web/src/features/{usl,intake,memory,audit,evaluation}/**`; `scripts/gates/p18d.py` |
| 19 | `app/audit/replay.py`, `app/api/routes_review.py` ✎ (store the machine record), `app/store.py` ✎ (additive), `app/api/routes_meta.py` ✎ (`GET /eval/latest`), `app/labels.py` ✎ (headline wording), `app/config.py` ✎ (NVIDIA default model only), `ui/**` (Streamlit fallback only), `.streamlit/config.toml` (new), `docs/IMPACT.md` ✎ (C1 only), `docs/PRIOR_WORK.md` ✎ (C3, your wording), `tests/unit/{audit,api,ui,labels}/**` |
| 20 | `output_examples/**`, `logs/examples/**`, `eval/**` (results only), `docs/evidence/**`, `docs/EVALUATION.md`, `README.md`, `metadata.json`, `docs/{SPONSORS,IMPACT,DEMO_SCRIPT,SLIDES,SUBMISSION,QA_PREP,ARCHITECTURE}.md`, `docs/img/**`, `tests/unit/docs/**` (only if a claims test needs a new evidence path) |

Everyone also owns:

- `docs/passes/<LABEL>_REPORT.md` and `docs/cursor-usage/<LABEL>.md`. Keep the folder name; record the tool as Claude Code.
- `.cursor/plans/<LABEL>.md`.
- Their own `scripts/gates/p<ID>.py`.

**Labels:** `18a` → `P18-A`, `18b` → `P18-B`, `18c` → `P18-C`, `18d` → `P18-D`, `19` → `P19`, `20` → `P20`.

**Shared web files.**
- 18b creates the app shell, router, design tokens, API client and the `web/src/ui/` component kit.
- 18c and 18d may **add** new files under `web/src/ui/`. They may not edit 18b's files.
- If 18c or 18d needs a change to a shared file, they set the phase to `blocked` and ask. The router already has a placeholder route for every page, so 18c and 18d replace their own page files only.

## 7. Definition of done for Release 3

1. Gate B decided, and `main` holds the shipped console.
2. P19 merged: C1–C3, C7, C8 and C11 fixed; B10–B13 fixed; tests green.
3. P20 merged:
   - live examples committed (all six if the Nightshift fix shipped; otherwise at least example 2);
   - the root of `output_examples/` contains no file made before P14-A;
   - the README, SPONSORS, IMPACT, metadata and the demo script match the committed evidence (the P17 claims tests stay green);
   - screenshots show the shipped console.
4. The video (3:30–3:50) and the deck are linked in `metadata.json` and the README.
5. `python scripts/clean_clone_check.py https://github.com/awkwardapples/Arbiter --evidence` passes on your machine after the last merge, and the report is committed.
