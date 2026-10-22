# Cursor usage — P1-A

- **Model:** Composer (Cursor agent)
- **Plan:** `.cursor/plans/P1-A.md` (approved via user message echoing plan summary)
- **Hook:** `verify-pass --pass 1a` green after fixing idempotent `generated_at`, DuckDB JSON load, near-match decoy ratio, and lint/format
- **Notable loops:** DuckDB `read_json_auto` required temp files; P1-T1 failed until envelope timestamps were deterministic
