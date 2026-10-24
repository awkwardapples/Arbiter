# Start a pass

The text after this command is the lane ID: Release 1 `0 1a 1b 2a 2b 2c 2d 3 4a 4b 5a 5b 6 7`, Release 2 `13 14a 14b 15 16 17`. Release 3 lanes (`18a 18b 18c 18d 19 20`) are run in Claude Code with `.claude/commands/start-pass.md`.

1. Write the file `.cursor/ACTIVE_PASS` containing exactly one line: `<ID> plan`.
2. Read `AGENTS.md` in full.
3. Find the pass file for `<ID>`: Release 1 ids in `docs/spec/passes/README.md` §2; Release 2 ids (13–17) in `docs/spec/release2/README.md`. Read **only your lane's section** of it, then only the spec sections that lane lists under "Read first". For Release 2, ownership is the table in `docs/spec/release2/README.md`.
4. In Plan Mode, write `.cursor/plans/<LABEL>.md` (LABEL = `P0`, `P1-A`, `P1-B`, `P2-A` … `P7`) containing:
   - goal (one paragraph, your words);
   - every file you will create or edit, each confirmed to be inside your lane's ownership (`docs/spec/passes/README.md` §3) — flag any exception;
   - the interfaces you will implement (signatures);
   - every acceptance test id from the pass file, with a one-line description of how you will test it;
   - risks and questions for the human.
5. Stop. Wait for the human to approve the plan.
6. On approval: change `.cursor/ACTIVE_PASS` to `<ID> build`, then follow `AGENTS.md` §6 steps 3–7 exactly.
