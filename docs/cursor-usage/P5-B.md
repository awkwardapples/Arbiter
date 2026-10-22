# Cursor usage — P5-B

- **Model:** Grok 4.7 (Cursor agent)
- **Plan:** `.cursor/plans/P5-B.md` (approved: optional calibration fields on `Calibration`, offline DuckDB only, calibration split only, generated `docs/EVALUATION.md`, examples from `orchestrator.run`)
- **Notable loop:** P5-T3 stayed red. The gate search is doing what it should. VND-0023 (S06) approves offline at confidence 1.0 with `ALL_REQUIRED_CONTROLS_MET` because the extractor does not raise `residency.regions`. Left for P3.5. The assertion was not loosened.
- **Verify:** `verify-pass --pass 5b` was not run as a green gate. It is red on P5-T3 by design. P5-T1, T2, T4, T6, T7, T8 pass. P5-T5 skips (no README markers).
