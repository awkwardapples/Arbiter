---
description: Start an Arbiter pass (lane) in plan phase
argument-hint: <lane id, e.g. 18a>
---

# Start pass $ARGUMENTS

The lane id is `$ARGUMENTS`. Release 3 ids are `18a 18b 18c 18d 19 20`; Release 1 and 2 ids are listed in `AGENTS.md` and `docs/spec/release2/README.md`.

1. If `.cursor/plans/<LABEL>.md` already exists for this lane and the human approved it earlier, this is a resumed session:
   - write `.cursor/ACTIVE_PASS` as `$ARGUMENTS build`;
   - read the plan and `git log --oneline -20`;
   - say what is done and what is next;
   - continue from step 6.

   (LABEL: `18a` → `P18-A`, `18b` → `P18-B`, `18c` → `P18-C`, `18d` → `P18-D`, `19` → `P19`, `20` → `P20`.)
2. Otherwise, write `.cursor/ACTIVE_PASS` containing exactly one line: `$ARGUMENTS plan`.
3. `AGENTS.md` and `CLAUDE.md` are already in your context. Now read `docs/spec/release3/README.md`, then this lane's pass file:

   | Lane | Pass file |
   |---|---|
   | 18a | `P18A_STREAM_API.md` |
   | 18b | `P18B_RUN_VIEW.md` |
   | 18c | `P18C_CASE_AND_QUEUE.md` |
   | 18d | `P18D_PAGES.md` |
   | 19 | `P19_FIXES.md` |
   | 20 | `P20_LIVE_RERUN.md` |

   Then read only the files that pass lists under "Read first". For P18 lanes, `P18_00_DESIGN.md` is required reading.
4. Write `.cursor/plans/<LABEL>.md` containing:
   - the goal in one paragraph, in your words;
   - every file you will create or edit, each checked against the lane's ownership in `docs/spec/release3/README.md` §6, with any exception flagged;
   - the interfaces or components you will build (signatures, or the component tree);
   - every acceptance test id from the pass file, with one line on how you will test it;
   - risks and questions for the human.
5. **Stop.** Do not write code. Wait for the human to approve the plan.
6. On approval:
   - change `.cursor/ACTIVE_PASS` to `$ARGUMENTS build`;
   - follow `AGENTS.md` §6 steps 3–7: tests first and commit them, implement in small commits, `python scripts/tasks.py verify-pass --pass $ARGUMENTS` green, report and usage note, push, PR, delete `.cursor/ACTIVE_PASS`, stop.
