# Zetaris federation (P1-B)

Arbiter registers five synthetic REST sources and the public CISA KEV feed in local Zetaris, then queries them through `ZetarisBackend` (see `app/data/zetaris.py`).

## Source mode (fallback B)

This project defaults to **`ZETARIS_SOURCE_MODE=github_raw`**: REST tables read committed JSON from GitHub, not the laptop simulator (Zetaris containers cannot reach `host.docker.internal:8100` reliably).

Set in `.env`:

```bash
ZETARIS_SOURCE_MODE=github_raw
GITHUB_RAW_BASE=https://raw.githubusercontent.com/awkwardapples/Arbiter/main/data/sample/systems
```

Use `simulator` + `SOURCES_PUBLIC_BASE` only when `driver`/`api` containers can curl the simulator.

**KEV:** In `github_raw` mode, step `02_kev.sql` loads the committed `data/kev/kev_snapshot.json` from GitHub (not live CISA), derived from `GITHUB_RAW_BASE`.

## Query layer

- **`usl`** — `lightning.metastore.arbiter.vendor_risk.*` (preferred when compile succeeds)
- **`views`** — `arbiter.*_v` SchemaStore views (acceptable demo fallback if USL fails)

Set `ZETARIS_QUERY_LAYER=views` when USL activation is blocked.

## Commands

```bash
python run.py zetaris status          # SELECT 1 (read-only)
python run.py zetaris onboard --dry-run
python run.py zetaris onboard --only 01 --yes --skip-exists
python run.py zetaris parity
```

Statement batches live in `zetaris/sql/*.sql`, split only on `-- @@stmt` lines.

## Troubleshooting

- **401** — check `ZETARIS_API_KEY` / `ZETARIS_ORG_ID` in `.env` (never log the key).
- **REST empty** — verify `GITHUB_RAW_BASE` URLs return JSON in a browser.
- **USL compile errors** — switch to `ZETARIS_QUERY_LAYER=views` and document in `docs/passes/P1-B_REPORT.md`.
