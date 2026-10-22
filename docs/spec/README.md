# Arbiter specification pack: how to use it

This pack was written **before the build window** (20–21 Oct 2026) by the human and an AI architect (Claude, outside the repo). It contains **no application code**. It is committed unchanged as the repository's first commit *after* the window opens (Thu 22 Oct, after 01:00 BST), and it is declared as a pre-existing component (see `docs/PRIOR_WORK.md`).

## Contents

| Path | What it is | Who reads it |
|---|---|---|
| `AGENTS.md` | Binding operating manual for coding agents: invariants, workflow, standards | Every Cursor agent, every pass |
| `.cursor/rules/*.mdc` | Always-on and file-scoped rules (core, Python, integrity, sponsor contracts, testing) | Cursor, automatically |
| `.cursor/commands/*.md` | `/start-pass`, `/verify-pass`, `/review-pass`, `/explain-pass` | You, in Cursor chat |
| `.cursor/hooks.json`, `.cursor/hooks/*.py` | `stop` hook (auto re-verify loop) and `beforeShellExecution` guard (secrets, port 8889, destructive commands) | Cursor, automatically |
| `docs/spec/00_MASTER_SPEC.md` | Thesis, Track 3 mapping, scoring traceability, architecture, contracts, components, failure model | Everyone |
| `docs/spec/01_DATA_AND_ZETARIS.md` | Synthetic enterprise world, simulator, Zetaris federation (REST → views → USL, DQ), query registry, parity | P1, P3 |
| `docs/spec/02_POLICY.md` | Policy-as-code, tri-state DSL, outcome order, governed precedent exceptions | P2-C, P3, P4 |
| `docs/spec/03_EVALUATION.md` | Labels, splits, baseline, metrics, calibration, honesty rules | P5-B, P6, P7 |
| `docs/spec/04_SUBMISSION_PLAYBOOK.md` | Video script, deck outline, sponsor explanation, metadata.json, form worksheet, post-submission | P6, P7, you |
| `docs/spec/05_RUNBOOK.md` | UK-time schedule, Day-0 checks, review protocol, organiser questions, risks, cut lines | You |
| `docs/spec/06_LAUNCH.md` | **Literal launch sequence**: repo setup, first commit, P0, worktrees, three parallel agents, PR and review gate | You |
| `.gitignore` | Minimal ignore list so the first commit can never include `.env` or `.venv` (P0 extends it) | git |
| `.cursor/worktrees.json` | Links `.env` and `.venv` into Cursor-managed worktrees (optional route) | Cursor |
| `docs/spec/passes/README.md` | Lane graph, ownership table, models, time budgets, prompt template | You and every agent |
| `docs/spec/passes/P0…P7_*.md` | One file per pass: goal, deliverables, interfaces, acceptance tests, verification, Cursor prompt | The agent on that lane |
| `docs/PRIOR_WORK.md` | Pre-existing component declaration (draft) | Submission form, README |
| `docs/DAY0_CHECKS.md` | Template for recording environment checks | You, Wed/Thu |

## The loop, in one picture

```
you: /start-pass 1a  ──► agent (Plan Mode) writes .cursor/plans/P1-A.md ──► you approve
                          │
                          ▼  ACTIVE_PASS = "1a build"
                 agent writes acceptance tests (fail) → commits → implements
                          │
               agent stops ─► stop hook runs verify-pass ─► red? feed failures back (≤5×)
                          │                                 green? remind: report + push
                          ▼
                 docs/passes/P1-A_REPORT.md, docs/cursor-usage/P1-A.md, push branch
                          │
you → Claude: "Review P1-A p1a-data <sha>"  ──► clone, verify, diff vs spec ──► PASS / FIXES / BLOCK
                          │
                       merge to main ──► /explain-pass 1a (15 min study)
```

## Rules for the human

1. **Commit nothing to the project repo before Thu 22 Oct 01:00 BST (00:00 UTC).** Creating the empty public repo on Thursday is fine.
2. First commit: this pack, unchanged, staging only its paths: `git add .gitignore AGENTS.md .cursor docs && git commit -m "docs: import pre-existing design specification (declared)"` (full sequence in `06_LAUNCH.md` §2).
3. Run at most three lanes at once, each in its own worktree and branch (`passes/README.md` §2).
4. Never paste a key into Cursor chat, Claude chat, a screenshot or a terminal you are recording.
5. If the Track 3 challenge statement on HackOS (published at kickoff) adds requirements, send it to me before P0; I will patch the spec.
6. If a hook does not work on your OS (Day-0 test), keep it but use `/verify-pass` manually. If `beforeShellExecution` is unsupported, remove that entry from `hooks.json`.
7. The hooks call `python3` (correct for WSL/Linux/macOS). If you ever run Cursor natively on Windows instead, change the two `command` entries in `.cursor/hooks.json` to `py -3 …`.
8. Reference clones live **beside** the repo, never inside it: `~/zetaris-getting-started` (with its own `.env.local`) and `~/meterless`.
