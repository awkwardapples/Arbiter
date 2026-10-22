# P1-B cursor usage

- **Model:** Composer (Cursor agent)
- **Plan:** `.cursor/plans/P1-B.md`
- **Branch:** `p1b-zetaris` (local)
- **Hook:** `verify-pass --pass 1b` green after unit tests + gate (parity exceptions documented until live onboard)

## Notes

- Acceptance tests P1-T20–P1-T24 implemented with respx + captured `tests/fixtures/zetaris_run_response.json` (live SELECT 1 shape).
- Live tests P1-T25–P1-T28 in `tests/live/test_zetaris_parity.py` (require `ARBITER_LIVE_TESTS=1` and onboarded federation).
- Attended onboarding: steps 01–02 green; step 03 USL compile failed once → views layer; parity `all_green=false` (DQ only); `verify-pass --pass 1b` green.
