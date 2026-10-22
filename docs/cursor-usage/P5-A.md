# Cursor usage — P5-A

- **Model:** Composer (Cursor agent)
- **Plan:** `.cursor/plans/P5-A.md` (approved by Josh with API-only / no hmem-retrieval API / eval 404 fallback / deferred screenshots)
- **Notable loops:** Streamlit `st.navigation` required file-based `ui/pages/*` after AppTest `switch_page` failures with callable-only pages
- **Verify:** `DOCKER=0 python scripts/tasks.py verify-pass --pass 5a` green (19 p5a tests + full non-live regression)
