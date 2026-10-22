# P2-B cursor usage

- **Date:** 2026-10-22
- **Lane:** P2-B LLM layer and Nightshift (`2b`, branch `p2b-nightshift`)
- **Model:** Claude Opus 5.5 (Cursor agent)
- **Plan:** `.cursor/plans/P2-B.md` (approved with defaults and five answers: Nightshift on :8088, stay on `p2b-nightshift`, `llm status` in `app/cli/llm.py`, `rt-local`/missing-NVIDIA-key rules, additive trace fields)
- **Notable loops:**
  - Live discovery came before any provider code: `/v1/models` returned 77 ids.
  - The first live chat on both routes returned HTTP 502 `…_empty_response` at `max_tokens=64`. A single diagnostic call at 1024 succeeded. That led to larger per-purpose token budgets, and to reading the route and receipt from the response body (Nightshift sends no `meterless-*` headers).
  - Acceptance tests were committed failing (`ImportError` on `app.llm.resolve`).
  - After implementation, the only failures were the four tests waiting on fixtures. Fixtures were then captured live through an opt-in test that refuses to write the token.
- **Hook iterations:** `verify-pass --pass 2b` ran three times:
  1. Lint failed: PEP 695 type parameter on `jsonparse.parse`.
  2. The secret scan failed on false positives: the generic `token=` rule matched ordinary keyword arguments. I renamed identifiers; `.secrets-allowlist` is P0-owned and was not touched.
  3. Green: 130 p2b tests, 295 non-live tests, gate, secret-scan, hardcode-check.

  Live P2-T20L passed 2/2.
