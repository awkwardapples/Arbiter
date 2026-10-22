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
| 12 | `GET /v1/models` with token + `meterless-app` → list of ids | ☑ | 2026-10-22, `http://localhost:8088/v1`, HTTP 200, 77 ids, no `meterless-*` response headers. ids seen: 18 routing ids `meterless/{auto,fast,deep,cheap,local,fusion,cluster,text,code,vision,perception,image,video,speech,transcribe,music,embed,judge}`; 8 NVIDIA ids `nvidia/nemotron-3.5-super-vl-120b-a12b`, `nvidia/nemotron-3.5-lightning-30b-a3b`, `nvidia/nemotron-3-ultra-550b-a55b`, `nvidia/nemotron-3-super-120b-a12b`, `nvidia/nemotron-3-nano-30b-a3b`, `nvidia/llama-3.1-nemotron-ultra-253b-v1`, `nvidia/llama-3.3-nemotron-super-49b-v1.5`, `nvidia/nemotron-3-embed-1b`; 51 `local-runtime/*` ids. Captured in `tests/fixtures/meterless_models.json` |
| 13 | chat on `meterless/fast` returns `model` = `nvidia/nemotron-3.5-lightning-30b-a3b` | ☑ | cold latency: 1866 ms (first successful call; `max_tokens=1024`). With `max_tokens=64` the call returned HTTP 502 `provider_error` `nvidia/nemotron-3.5-lightning-30b-a3b_empty_response` (reasoning tokens used the budget). Receipt: `requested_model=meterless/fast`, `provider_model=meterless/auto`, `routed_model=nvidia/nemotron-3.5-lightning-30b-a3b`, `winning_route.provider=nvidia` |
| 14 | chat on `meterless/deep` returns `model` = `nvidia/nemotron-3.5-lightning-30b-a3b` | ☑ | cold latency: 4255 ms (`max_tokens=2048`). Deep routes via `meterless/auto` to the same Lightning 30B lane as fast, not a larger Nemotron. Receipt baseline names `nvidia/nemotron-3-super-120b-a12b` |
| 15 | Organisers' `smoke_test.py` passes | ☐ | |
| 16 | Cursor access confirmed (HackOS folder / Pro) | ☐ | plan: |
| 17 | Cursor `stop` hook test (followup_message honoured) | ☐ | if ✗ → manual `/verify-pass` |
| 18 | Cursor `beforeShellExecution` hook test (`cat .env` denied) | ☐ | if ✗ → remove entry |
| 19 | Plan Mode, worktrees / parallel agents available | ☐ | |
| 20 | Organiser questions sent (05_RUNBOOK §6) | ☐ | replies: |
