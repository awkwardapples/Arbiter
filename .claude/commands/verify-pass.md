---
description: Verify the active Arbiter pass and fix failures
---

# Verify the active pass

1. Read `.cursor/ACTIVE_PASS` to get `<ID>`.
2. Run `python scripts/tasks.py verify-pass --pass <ID>` with the project venv's interpreter. For P18 lanes, also run `npm run check` in `web/`.
3. **If green:**
   - say so and list the acceptance test ids that passed;
   - continue the lane: report, usage note, push, PR, delete `.cursor/ACTIVE_PASS`, stop.
4. **If red:**
   - list each failure (test id, file:line, one-line cause);
   - fix them one at a time and re-run.
   - Never weaken, skip or delete a test. If a test itself looks wrong, set `.cursor/ACTIVE_PASS` to `<ID> blocked` and ask the human why.

Use this when the Stop hook does not run on this machine.
