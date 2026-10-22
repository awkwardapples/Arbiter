# Cursor usage — P2-D

- **Model:** Composer (Cursor agent)
- **Plan:** `.cursor/plans/P2-D.md`
- **Branch:** `p2d-report` (per human; spec name `p2d-guard` not used)
- **Notable loops:** Secret-scan flagged `sk-` in PII test and `secret =` in keys module — fixed via runtime-built key material and rename. Contract tamper tests use stale signature after `model_copy` updates. Ruff format on guard/audit modules.
- **Verify:** `python scripts/tasks.py verify-pass --pass 2d` green; guard-eval scout + domain 1.0 / 1.0 deterministic.
