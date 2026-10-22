# Verify the active pass

1. Read `.cursor/ACTIVE_PASS` to get `<ID>`.
2. Run `python scripts/tasks.py verify-pass --pass <ID>`.
3. If green: say so, list the acceptance test ids that passed, and continue with the pass workflow (report → CURSOR_USAGE entry → push → delete ACTIVE_PASS → stop).
4. If red: list each failure (test id, file:line, one-line cause), fix them one at a time, and re-run. Never weaken, skip or delete a test. If a test itself looks wrong, set `.cursor/ACTIVE_PASS` to `<ID> blocked` and ask the human, explaining why.

Use this command manually if the automatic stop hook does not work on this machine.
