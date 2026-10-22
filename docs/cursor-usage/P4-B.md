# Cursor usage — P4-B

- **Date:** 2026-10-22
- **Lane:** P4-B (`4b`), marker `p4b`
- **Model:** Grok 4.7 (Cursor agent)
- **Plan:** `.cursor/plans/P4-B.md`
- **Branch:** `p4b-api` (fast-forwarded onto `origin/main` at `e967cd9`, PR #9)

## Notable loops

- Acceptance tests were committed failing (`ff1c463`) before the store and routes existed. `GET /cases` was 404, replay was not importable, and `var/arbiter.db` was absent.
- The 403 error test first returned 422 because the executed-contract fixture reused the pending contract id and overwrote it. The fixture got its own id. The route's role check was already correct (example 5's analyst denial passed).
- Clean-clone, three failures then a pass: `git clone --local` cannot hardlink from this checkout onto `/tmp` (cross-device); `/health` writes `trace-zetaris-status.jsonl`, which is not a collaborative case trace; `git log -p` assignment regex matches prose (set token to re.compile) and the P0 fixture file. Fixes stayed in `scripts/clean_clone_check.py`.
- `verify-pass --pass 4b` was green on the first full gate after those script fixes (17 passed / 1 skipped on the marker, 559 passed / 3 skipped on regression). No separate stop-hook bounce.

## Verify

`python scripts/tasks.py verify-pass --pass 4b` green. `P4-T18` ran locally because Docker is on `PATH`. `P4-T17`'s container smoke stayed skipped (`ARBITER_DOCKER_TESTS` unset). The CI job builds with `docker build -t arbiter .`.
