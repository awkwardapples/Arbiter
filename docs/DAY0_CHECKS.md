# Day-0 environment checks (fill in; never paste secrets here)

Date: ____  Machine: ____ (OS ____, RAM ____ GB, free disk ____ GB)

| # | Check (05_RUNBOOK §3) | Result | Notes |
|---|---|---|---|
| 1 | OS supported by Nightshift (Windows / Mac M1+ / Mac M5+ / DGX) | ☐ | |
| 2 | Python 3.12, Git, gh, Docker Desktop installed | ☐ | versions: |
| 3 | git user.name/email = GitHub account on the form | ☐ | |
| 4 | Zetaris `preflight.sh` passes; Docker 8 GB / 4 CPU | ☐ | |
| 5 | Zetaris `verify.sh` 9/9 | ☐ | |
| 6 | Zetaris UI :3000; REST `SELECT 1` works | ☐ | |
| 7 | Zetaris API key created in GUI and stored in password manager | ☐ | |
| 8 | getting-started `scripts/preflight.py` passes | ☐ | |
| 9 | **Zetaris container → `host.docker.internal:8100` reachable** | ☐ | service name used: |
| 10 | Throwaway REST table to host served JSON works (then removed) | ☐ | if ✗ → plan fallback B (github_raw) |
| 11 | Nightshift installed; NVIDIA key in Providers tab; lanes fast/deep enabled | ☐ | |
| 12 | `GET /v1/models` with token + `meterless-app` → list of ids | ☐ | ids seen: |
| 13 | chat on `meterless/fast` returns `model` = | ☐ | cold latency: |
| 14 | chat on `meterless/deep` returns `model` = | ☐ | cold latency: |
| 15 | Organisers' `smoke_test.py` passes | ☐ | |
| 16 | Cursor access confirmed (HackOS folder / Pro) | ☐ | plan: |
| 17 | Cursor `stop` hook test (followup_message honoured) | ☐ | if ✗ → manual `/verify-pass` |
| 18 | Cursor `beforeShellExecution` hook test (`cat .env` denied) | ☐ | if ✗ → remove entry |
| 19 | Plan Mode, worktrees / parallel agents available | ☐ | |
| 20 | Organiser questions sent (05_RUNBOOK §6) | ☐ | replies: |
