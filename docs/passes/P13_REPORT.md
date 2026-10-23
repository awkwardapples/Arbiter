# P13 report — Zetaris USL `vendor_risk`

## Built

- `zetaris/sql/03_usl.sql` was applied. `COMPILE USL IF NOT EXISTS vendor_risk DEPLOY` returned HTTP 200. Ten `ACTIVATE USL TABLE` statements returned HTTP 200. `SHOW TABLES IN lightning.metastore.arbiter.vendor_risk` returned 10 tables.
- Eleven description updates returned `updated=true`. Five `REGISTER DQ` statements returned HTTP 200. Four `RUN DQ TABLE` statements returned the counts in `docs/ZETARIS_USL.md`. `dq_vendor_spend` has no separate `RUN` line because `RUN DQ` is per table; the vendor run includes it (32 total, 32 valid, 0 invalid). `contract` has two rules, so five registrations become four runs.
- The column `text` is `doc_text` in the USL only. `ACTIVATE` selects `text AS doc_text`. `Q_SUBMISSION_DOCUMENTS` selects `doc_text AS text` on the USL layer.
- `Q_VENDOR_360` is in the registry. Parity compared it on the USL and on DuckDB for all 32 vendors: 1 row each, hashes equal.
- `python run.py zetaris parity` with `ZETARIS_QUERY_LAYER=usl` printed `all_green=True` and rewrote `docs/passes/P1-B_parity.json` (`query_layer` `usl`).
- `docs/ZETARIS_USL.md` records the sources, the bisect, the DQ results, the CISA reachability check, and the measured comparison.
- `app/data/zetaris.py` no longer rewrites a table name that is already behind a dot, and `dq_invalid` accepts a `SHOW DQ` `records` value that is one JSON object. Without that, the USL count SQL and `SHOW DQ ALL INVALID` were corrupted, and the contract key `CTR-30028` was dropped.

`Q_VENDOR_360` inner-joins vendor, contract, and submission because those three are one-to-one in the sample (32, 32, and 32). If a vendor ever lacks a contract or submission, those become left joins too, or the vendor silently drops from the 360. Components stay a left join: only 2 of 32 vendors have one.

Live KEV was not swapped onto `kev_raw`. Both sides of this parity run still read the 84-row snapshot, so a full hash can match. Live feed grows over time; a full row hash can never match across time; superset equality is the correct parity for a live-vs-snapshot comparison. That check is not in `zetaris/parity.py` yet, and it was not needed for this snapshot-to-snapshot run.

## Bisect (`COMPILE USL` without `DEPLOY`)

| Probe | HTTP | Result |
|---|---|---|
| Current 10-table DDL, `text` column, no `DEPLOY` | 400 | `Invalid DDL statement. Please provide a valid CREATE TABLE statement using Spark SQL or ANSI SQL syntax.` |
| `vendor`, varchar only | 200 | Model JSON returned |
| Add `int`, then `decimal(14,2)`, then `date`, then `boolean` | 200 | Each type accepted |
| Second table with `FOREIGN KEY REFERENCES` | 200 | FK recorded on `vendor_id` |
| Column name `text` alone | 400 | Same invalid-DDL message |
| Column names `status`, `version`, `category` alone | 200 | Accepted |
| Full 10-table DDL with `doc_text` instead of `text`, no `DEPLOY` | 200 | 10 tables, name `vendor_risk` |

The deploy of that last form returned HTTP 200, `timeUsed` 645.

## Deviations

- `SHOW USL` is not a command in the Lightning SQL guide. Existence was checked with `SHOW NAMESPACES OR TABLES IN lightning.metastore.arbiter`, which was empty, so `IF NOT EXISTS` stayed on the compile.
- `data/usl/vendor_risk.model.json` is still the JSON from `COMPILE` without `DEPLOY`. `load_model()` fills descriptions from `03_usl.sql`. The live model now has descriptions and `dqAnnotations`; a `LOAD USL` export has not replaced the file.
- `kev_rest_url()` returns `settings.KEV_URL` (`raw.githubusercontent.com`, cisagov `kev-data` `develop`). `CREATE LIGHTNING REST TABLE kev_raw` returned HTTP 400 because `kev_raw` already exists and still points at the repo snapshot. Zetaris can fetch `https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json` (session probe HTTP 200, catalogue count 1754, `catalogVersion` `2026.10.21`). The session table was dropped. The activated USL table still reads the 84-row view.
- `.env` was not opened. The read-only check reported `ZETARIS_QUERY_LAYER=views`. Parity was run with `ZETARIS_QUERY_LAYER=usl` on that process only.
- The three `docs/img/zetaris_usl_*.png` screenshots were not captured. `python run.py zetaris model --export` and `--mermaid` were not added. The mermaid block in `docs/ZETARIS_USL.md` is the foreign keys from the compile JSON.

## Known gaps

- Persistent KEV is the snapshot. Replacing it needs `kev_raw` dropped, then the create above, then the view and `ACTIVATE` for `kev_vuln` run again. The live-feed swap is still outstanding.
- A process whose environment still says `views` does not read the USL.
- The committed model file is not a `LOAD USL` payload.
- `Q_VENDOR_360` is not in the deterministic screen set.
- Parity’s superset check for a live KEV catalogue is not implemented. This green run does not prove that check.

## Commands run

```bash
SHOW NAMESPACES OR TABLES IN lightning.metastore
SHOW NAMESPACES OR TABLES IN lightning.metastore.arbiter
# COMPILE USL IF NOT EXISTS vendor_risk DEPLOY ...     HTTP 200
# 11 UPDATE USL description statements                 HTTP 200 updated=true
# 10 ACTIVATE USL TABLE statements                     HTTP 200 registered
SHOW TABLES IN lightning.metastore.arbiter.vendor_risk # total 10
# 5 REGISTER DQ statements                             HTTP 200
# 4 RUN DQ TABLE statements                            HTTP 200, counts in docs/ZETARIS_USL.md
SHOW LIGHTNING TABLES ARBITER_PUB                      # kev_raw -> kev_snapshot.json
SELECT COUNT(*) AS c FROM arbiter.kev_vuln_v           # 84
# CREATE LIGHTNING REST TABLE kev_raw ... KEV_URL      HTTP 400 already exists
# CREATE REST SESSION TABLE kev_cisa_probe ... cisa.gov HTTP 200, count 1754
# DROP TABLE session.kev_cisa_probe                    HTTP 200
SHOW DQ ALL INVALID TABLE lightning.metastore.arbiter.vendor_risk.contract
# records contract_id CTR-30028

ZETARIS_QUERY_LAYER=usl .venv/bin/python run.py zetaris parity
# stdout: all_green=True
# 656 s; 9/9 table counts; 416/416 query rows; DQ CTR-30028; KEV subset 32/32

wc -l app/data/duckdb_backend.py app/data/dq.py app/data/queries.yaml \
      zetaris/sql/03_usl.sql zetaris/dq_rules.yaml
# 162 + 61 + 300 + 81 + 22
```

One `Q_VENDOR_360` for `VND-0001`: DuckDB 37 ms, USL 5220 ms, same row.

## Explain it

1. The first `COMPILE USL` failed because the column name `text` is rejected. A varchar-only table, `int`, `decimal(14,2)`, `date`, `boolean`, a foreign key, and the names `status`, `version`, and `category` each returned HTTP 200 without `DEPLOY`. A one-column table whose second column was `text` returned the same HTTP 400 as the full DDL. Replacing `text` with `doc_text` made the 10-table statement return HTTP 200. That statement, with `DEPLOY`, is what was stored.
2. `Q_VENDOR_360` joins procurement `vendor`, CLM `contract` on `clm_supplier_ref = supplier_ref`, trust `submission`, a left join to `vendor_component`, and a left join to `kev_vuln` with the same predicate as `Q_COMPONENT_KEV`. `{T.*}` becomes the DuckDB table, `arbiter.<table>_v`, or `lightning.metastore.arbiter.vendor_risk.<table>`. After activation those USL names are queryable. The deterministic planner does not run this id. Parity did, for every `VND-0001` … `VND-0032`.
3. On the model path the Planner sees ten lines, one table each, with the primary key, each foreign key as `fk→table.column`, and the business description, plus a list of query ids and the tables they read. Measured on the committed model: 1219 characters, 304 tokens (`len//4`). A names-only column list of the same model is 1103 characters, 275 tokens. The catalogue is the one that carries descriptions and keys.
4. `wc -l` on 23 Oct 2026: `app/data/duckdb_backend.py` 162, `app/data/dq.py` 61, `app/data/queries.yaml` 300, `zetaris/sql/03_usl.sql` 81, `zetaris/dq_rules.yaml` 22. The USL file is the DDL, descriptions, activation, and DQ statements. The mirror is still what sample mode runs. `Q_VENDOR_360` is the merge; there is no second Python merge beside it.
5. `dq_contract_dpa_date` (`dpa_signed = false OR dpa_signed_date IS NOT NULL`) is the rule for Kestrel Docs Ltd (`VND-0028`). The sample contract is `CTR-30028` (`SUP-7028`): status `signed`, `dpa_signed` true, `dpa_signed_date` null. `RUN DQ` on the contract table reported 1 invalid of 32. `SHOW DQ ALL INVALID` returned `contract_id` `CTR-30028`. Evidence stores a flag `contract_id=CTR-30028`. `derive` then sets `dpa.signed` to UNKNOWN (`app/facts.py`, `DQ_AFFECTS`). The Evaluator asks for `Q_DQ_INVALID` after contract rows exist. The same key is what DuckDB returns, and parity recorded both sides as `["CTR-30028"]`.
