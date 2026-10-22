# Independent review of a pass (run with a DIFFERENT model from the one that built it)

The text after this command is the lane ID. You are a reviewer, not the author. **Do not modify any file.**

1. Read `AGENTS.md`, the lane's section of its pass file, and the spec sections it lists.
2. Inspect the change: `git diff --stat main...HEAD` and `git diff main...HEAD`.
3. Run `python scripts/tasks.py verify-pass --pass <ID>` and `python scripts/tasks.py verify`.
4. Check, and record evidence for each:
   - every acceptance test id in the pass file exists, carries the lane marker, and asserts what the pass file says (not a weaker version);
   - only files in the lane's ownership changed (list any others);
   - the 12 invariants in `AGENTS.md` §3 (cite file:line for any violation);
   - integrity rules (`.cursor/rules/20-integrity.mdc`): hardcoding, fabricated traces, secrets, mocks outside `tests/`;
   - error handling, timeouts and determinism where the lane touches I/O, hashing or time;
   - the pass report is accurate (claims match code).
5. Output:
   - **Verdict**: PASS / PASS WITH FIXES / BLOCK.
   - **Findings table**: severity (blocker/major/minor), file:line, issue, evidence, suggested fix.
   - **Fix prompt**: a single copy-paste prompt the author agent can execute to address all blocker and major findings.
