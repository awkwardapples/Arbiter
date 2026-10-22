# P1-B report — Zetaris live federation

## Configuration recorded

| Setting | Value |
|---|---|
| **Source mode** | `github_raw` (fallback B) |
| **GITHUB_RAW_BASE** | `https://raw.githubusercontent.com/awkwardapples/Arbiter/main/data/sample/systems/` |
| **Query layer** | **`views`** (USL compile failed; no retry) |
| **KEV REST (Zetaris)** | Committed `data/kev/kev_snapshot.json` via GitHub raw when `ZETARIS_SOURCE_MODE=github_raw` (`onboard.kev_rest_url()`). Runtime `KEV_URL` in `.env` may still target CISA develop for generator refresh only. |

## Onboarding progress

| Step | Status | Notes |
|---|---|---|
| 01 REST + views | **Done** | Nine GitHub raw REST tables + nine `arbiter.*_v` views. Counts: vendor 32, vendor_alias 64, contract 32, incident 2, watchlist 2, submission 32, answers 504, documents 9, components 2 |
| 02 KEV | **Done** | `arbiter_pub.kev_raw` = 1 envelope (`catalogVersion=2026.10.21`, `count=84`); `arbiter.kev_vuln_v` = 84 |
| 03 USL + DQ | **Failed (one attempt)** | `COMPILE USL vendor_risk` rejected: HTTP 400 — invalid DDL / Spark SQL syntax. **No retry.** ACTIVATE / REGISTER DQ / RUN DQ not executed. Federation continues on **views** only; sample-mode DQ remains on DuckDB (`app/data/dq.py`). |

Screenshots (deck): `docs/img/zetaris_1.png` (views), `docs/img/zetaris_2.png` (KEV). Capture `zetaris_3.png` (USL/DQ attempt or views-only note) and `zetaris_4.png` (parity UI if available) without API keys in frame.

## Parity (`python run.py zetaris parity`)

Written to `docs/passes/P1-B_parity.json`. Summary (`query_layer=views`, post steps 01–02):

| Check | Result |
|---|---|
| **Source table counts** (9 views vs sample `count`) | **9 / 9 OK** |
| **Query parity** (all registry queries except KEV federated pair × all vendors) | **384 / 384 OK** (row counts + canonical hashes match DuckDB) |
| **KEV subset** (snapshot catalogue CVEs present in `kev_vuln_v`) | **32 / 32 OK** |
| **DQ parity** (Zetaris `SHOW DQ` vs DuckDB) | **0 / 5 OK** — `UpstreamError` on all rules (USL/DQ never registered) |

**`all_green`: false** — expected with views-only path and no Zetaris DQ.

## Parity exceptions

| Mismatch | Cause | Mitigation |
|---|---|---|
| DQ parity (all rules) | Step 03 USL/DQ did not run; `SHOW DQ ALL INVALID TABLE lightning.metastore.arbiter.vendor_risk.*` unavailable | Documented; **DuckDB DQ** is authoritative in sample mode and for `Q_DQ_INVALID` until USL succeeds on a future Zetaris build |
| USL tables absent | `COMPILE USL` rejected by Zetaris (multi-table DDL in one statement) | **`ZETARIS_QUERY_LAYER=views`**; registry resolves `{T.*}` to `arbiter.*_v` |

Query and count parity are green on the views path; live mode uses Zetaris for federation reads with DuckDB fallback per `FallbackBackend`.

## Verification commands

```bash
python run.py zetaris status
python run.py zetaris parity
python scripts/tasks.py verify-pass --pass 1b
ARBITER_LIVE_TESTS=1 pytest -m "p1b and live"   # optional; needs onboarded instance
```

**`verify-pass --pass 1b`:** green (lint, p1b unit tests, regression, gate with this report § Parity exceptions).

## Built (lane deliverables)

- `app/data/zetaris.py`, `app/cli/zetaris.py`
- `zetaris/{sources.yaml,sql/,onboard.py,parity.py,README.md}`
- Tests P1-T20–T24 (unit), P1-T25–T28 (live marker)
- `tests/fixtures/zetaris_run_response.json`
- `docs/passes/P1-B_parity.json`

## Deviations

- USL not activated (Zetaris DDL rejection); demo uses **views** layer only.
- KEV REST uses **committed snapshot** URL under `github_raw`, not live CISA feed.

## Known gaps

- Zetaris-side DQ rules not registered until USL compile succeeds on a compatible Zetaris version.
- Live marker tests (`ARBITER_LIVE_TESTS=1`) require human-run against this onboarded instance.

## Explain it (short)

1. **Residency fact:** procurement JSON → GitHub raw REST → `vendor_v` → registry `Q_VENDOR_PROFILE` → Zetaris REST SQL → provenance `backend=zetaris`, `query_id`, `zetaris_request_id` in trace output summary.
2. **Federated KEV:** `vendor_component` (trust) joined to `kev_vuln_v` (public snapshot) in SQL — internal + public in one query.
3. **Timeout / 401:** retries then DuckDB per query; 401 pins DuckDB for the run.
4. **Parity:** proves views match DuckDB mirror; DQ exception is USL absence, not data drift.
5. **Fallback B:** `github_raw` lets Zetaris containers read the same committed JSON judges use in sample mode.
