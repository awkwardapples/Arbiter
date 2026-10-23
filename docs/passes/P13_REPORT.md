# P13 report — Zetaris USL `vendor_risk`

## Built

- `zetaris/sql/03_usl.sql` is one `COMPILE USL … DEPLOY` statement with 10 `CREATE TABLE`s. Later `ACTIVATE`, `REGISTER DQ`, `RUN DQ`, and `UPDATE USL` statements use `lightning.metastore.arbiter.vendor_risk`. The five `REGISTER DQ` lines match `zetaris/dq_rules.yaml`.
- The column `text` is `doc_text` in the USL only. `ACTIVATE` selects `text AS doc_text`. `Q_SUBMISSION_DOCUMENTS` has a `sql_usl` override that selects `doc_text AS text`, so agents still see `text`. DuckDB and the views keep `text`.
- `kev_rest_url()` returns `settings.KEV_URL` for `simulator` and `github_raw`.
- `Q_VENDOR_360` is in the registry. On DuckDB it returns one row for each of `VND-0001` … `VND-0032`, and its component and KEV counts match `Q_VENDOR_COMPONENTS` and `Q_COMPONENT_KEV`.
- `app/data/usl_model.py` loads `data/usl/vendor_risk.model.json`. The Planner’s model path puts `compact_catalogue()` and the query-to-table map in `app/llm/prompts/plan.md`. The deterministic plan is still the screen set.
- Unit marker `p13` is green. `python scripts/tasks.py verify-pass --pass 13` passed: 9 p13 tests, then 691 passed and 6 skipped in the non-live regression, secret-scan, and hardcode-check.

`Q_VENDOR_360` inner-joins vendor, contract, and submission because those three are one-to-one in the sample (32, 32, and 32). If a vendor ever lacks a contract or submission, those become left joins too, or the vendor silently drops from the 360.

Live KEV parity, when it is run, is a superset check: non-KEV columns must match exactly; the live CVE count and latest KEV date must be greater than or equal to the snapshot. Live feed grows over time; a full row hash can never match across time; superset equality is the correct parity for a live-vs-snapshot comparison. That check is not in `zetaris/parity.py` yet.

## Bisect (`COMPILE USL` without `DEPLOY`)

`ARBITER_SRC`, `ARBITER_PUB`, and container `arbiter` already existed (`arbiter.vendor_v` = 32, `arbiter.kev_vuln_v` = 84). Those creates were skipped. `SHOW NAMESPACES OR TABLES IN lightning.metastore.arbiter` was empty before and after the probes, so nothing was stored.

| Probe | HTTP | Result |
|---|---|---|
| Current 10-table DDL, `text` column, no `DEPLOY` | 400 | `Invalid DDL statement. Please provide a valid CREATE TABLE statement using Spark SQL or ANSI SQL syntax.` |
| `vendor`, varchar only | 200 | Model JSON returned |
| Add `int`, then `decimal(14,2)`, then `date`, then `boolean` | 200 | Each type accepted |
| Second table with `FOREIGN KEY REFERENCES` | 200 | FK recorded on `vendor_id` |
| Column name `text` alone | 400 | Same invalid-DDL message |
| Column names `status`, `version`, `category` alone | 200 | Accepted |
| Full 10-table DDL with `doc_text` instead of `text`, no `DEPLOY` | 200 | 10 tables, name `vendor_risk` |

## Deviations

- The USL was not deployed, activated, or given DQ rules. `COMPILE … DEPLOY` was shown and was waiting for an explicit go. This finish was requested before that go. The instance is still on the views layer.
- `data/usl/vendor_risk.model.json` is the JSON from `COMPILE USL` without `DEPLOY`, key-sorted, not a `LOAD USL` export. That payload has no descriptions. `load_model()` fills table descriptions from the `SET TABLE DESCRIPTION` lines in `03_usl.sql` until a real `LOAD USL` replaces the file.
- `kev_rest_url()` now points at `settings.KEV_URL`, but `kev_raw` was not dropped and step 02 was not re-run. The live view is still the 84-row snapshot.
- `.env` was not opened. `ZETARIS_QUERY_LAYER` was `views` on the read-only check.
- `docs/ZETARIS_USL.md`, the three `docs/img/zetaris_usl_*.png` screenshots, a green `docs/passes/P1-B_parity.json` with `query_layer: usl`, and `scripts/gates/p13.py` were not written. `verify-pass` skips a missing gate, so a green run does not mean the P13 submission gate.

## Known gaps

- No activated `vendor_risk` tables. Live mode still reads `arbiter.*_v`.
- Zetaris DQ is still unregistered. Sample-mode DQ remains `app/data/dq.py`.
- The committed model will not match `LOAD USL` until deploy, description updates, and export.
- `Q_VENDOR_360` is not in the deterministic screen set. P14’s case header and dossier were the intended callers. The LLM planner may select the id; nothing in this pass calls it from the orchestrator.
- Parity’s KEV columns for `Q_VENDOR_360` are not implemented. The rule is the superset check above.

## Commands run

```bash
# read-only, port 8888
SHOW LIGHTNING DATABASES
SHOW NAMESPACES OR TABLES IN lightning.metastore
SELECT COUNT(*) AS c FROM arbiter.vendor_v          # 32
SELECT COUNT(*) AS c FROM arbiter.kev_vuln_v        # 84
# COMPILE USL without DEPLOY, then the bisect probes, then the 10-table doc_text form
SHOW NAMESPACES OR TABLES IN lightning.metastore.arbiter   # empty

wc -l app/data/duckdb_backend.py app/data/dq.py app/data/queries.yaml \
      zetaris/sql/03_usl.sql zetaris/dq_rules.yaml
# 162 + 61 + 300 + 81 + 22

python -c "from app.data.usl_model import load_model, compact_catalogue, catalogue_tokens; ..."
# compact catalogue 1219 chars, 304 tokens (len//4); column-list dump of the same model 1891 chars, 472 tokens

python scripts/tasks.py verify-pass --pass 13
# p13: 9 passed; regression: 691 passed, 6 skipped; secret-scan ok; hardcode-check ok
```

## Explain it

1. The first `COMPILE USL` failed because the column name `text` is rejected. A varchar-only table, `int`, `decimal(14,2)`, `date`, `boolean`, a foreign key, and the names `status`, `version`, and `category` each returned HTTP 200 without `DEPLOY`. A one-column table whose second column was `text` returned the same HTTP 400 as the full DDL. Replacing `text` with `doc_text` made the 10-table statement return HTTP 200. `SHOW NAMESPACES OR TABLES IN lightning.metastore.arbiter` stayed empty, so the debug compiles stored nothing.
2. `Q_VENDOR_360` joins procurement `vendor`, CLM `contract` on `clm_supplier_ref = supplier_ref`, trust `submission`, a left join to `vendor_component`, and a left join to `kev_vuln` with the same predicate as `Q_COMPONENT_KEV`. `{T.*}` becomes the DuckDB table, `arbiter.<table>_v`, or `lightning.metastore.arbiter.vendor_risk.<table>` depending on backend and layer. The USL names are not queryable until activation. The deterministic planner does not run this id. An agent reaches it only if a later plan selects `Q_VENDOR_360` or a caller such as the P14 dossier runs it.
3. On the model path the Planner sees ten lines, one table each, with the primary key, each foreign key as `fk→table.column`, and the business description, plus a list of query ids and the tables they read. Measured on the committed model: 304 tokens against 472 tokens for the same tables written as bare column lists (`len//4`). The foreign keys say which system corroborates which table. The deterministic planner does not see this text.
4. `wc -l` on 23 Oct 2026: `app/data/duckdb_backend.py` 162, `app/data/dq.py` 61, `app/data/queries.yaml` 300, `zetaris/sql/03_usl.sql` 81, `zetaris/dq_rules.yaml` 22. Those are the files that normalise, join, and DQ-check the same data. The USL file is the DDL, descriptions, activation, and DQ statements together. This does not remove the DuckDB mirror or the registry. The mirror is still what sample mode runs, and the USL is not activated, so those lines are not yet replaced in live mode. `Q_VENDOR_360` is the merge; there is no second Python merge beside it.
5. `dq_contract_dpa_date` (`dpa_signed = false OR dpa_signed_date IS NOT NULL`) is the rule for Kestrel Docs Ltd (`VND-0028`). The sample contract is `CTR-30028` (`SUP-7028`): status `signed`, `dpa_signed` true, `dpa_signed_date` null. When `Q_DQ_INVALID` returns that contract, Evidence stores a flag `contract_id=CTR-30028`. `derive` then sets `dpa.signed` to UNKNOWN (`app/facts.py`, `DQ_AFFECTS`). The Evaluator asks for `Q_DQ_INVALID` after contract rows exist. Zetaris has not run the rule; the sample path is DuckDB.
