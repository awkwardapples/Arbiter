# Cursor usage: P2-A (H-MEM Python port)

- **Date:** 2026-10-22
- **Lane / pass id:** P2-A (`2a`), branch `p2a-hmem`
- **Model used:** Claude Opus (Cursor agent, single session; no subagents)
- **Plan file:** `.cursor/plans/P2-A.md` (approved by the human with the recommended answers: golden check may skip without Node, create `tests/conformance/__init__.py`, opt-in `ledger_mirror`)

## Notable agent loops

1. **Reading the source.** The agent read all 10 reference `.ts` files and `runner.ts` from the local Meterless clone before planning. While reading, it found JS-semantics issues beyond the spec's list: `entries().sort()` compares `String([k, v])`, `/i` and `\d` need `re.ASCII`, JS `.length`/`.slice` count UTF-16 code units, and `$` must become `\Z`. These went into the plan.
2. **Tests first.** The conformance port and the P2-T2…T6 tests were committed red. They failed with `ImportError: cannot import name 'HMEM'`, which was the intended reason.
3. **Implementation.** The engine was written module by module. Conformance was 13/13 on the first run, and all unit tests passed first time.
4. **Coverage.** The agent added `test_services.py` because the acceptance tests barely exercise mining, sleep restore, dream rejection or queued conflicts.

## Stop-hook / verify-pass iterations

- Run 1: lint, tests and gate passed; **secret-scan failed** on `set TOKEN to re.compile(...)` (an assignment-name false positive). The agent renamed it rather than allowlisting.
- Run 2: `verify-pass p2a: ok`.
- Before that, `ruff format` and two SIM lint fixes were applied (`conflicts.py`, `dreaming.py`; both behaviour-preserving).
