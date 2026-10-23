# P13: Zetaris Unified Semantic Layer, for real (human-attended)

## 1. Goal

The Zetaris USL `vendor_risk` is compiled, deployed and activated over the onboarded sources, with:

- business descriptions on the model, every table and key columns;
- the five DQ rules registered and run **inside Zetaris**;
- the public CISA KEV feed federated live, not from the repo snapshot.

Arbiter's live mode queries the USL (`ZETARIS_QUERY_LAYER=usl`). The USL model itself (`LOAD USL` JSON) becomes the **semantic catalogue the Planner reasons over**. A new `Q_VENDOR_360` query shows the USL's compact expressive power.

`docs/ZETARIS_USL.md` is the judging artefact: sources identified → onboarded → USL built → reflection, including a measured custom-pipeline-versus-USL comparison.

## 2. Why it scores

The Opening Ceremony made the USL an explicit Zetaris judging requirement, with reflection on:

- how it sped up the build;
- how it helps day to day;
- why it matters to agents (clean data and expressive power in a compact format);
- custom Python pipeline versus USL.

This serves Sponsor Tech, Impact (track consistency: "data") and Innovation (agents planning over the semantic layer).

## 3. Read first

- `docs/spec/release2/R2_00_ASSESSMENT.md` §§3–4 (findings B4, B9)
- `docs/spec/01_DATA_AND_ZETARIS.md` §§5–9
- `docs/passes/P1-B_REPORT.md`
- In `~/zetaris-getting-started`:
  - `AGENTS.md`;
  - `docs/guides/zetaris-lightning-sql-commands.md` §13 (USL) and §14 (DQ);
  - `docs/guides/zetaris-lightning-sql-companion.md` (USL and DQ sections);
  - `open_data/usl/sql/01_sic_usl_create.sql` and `02_sic_edgar_usl_create.sql`. These are the **verified** patterns; copy their shapes exactly.

## 4. Safety (unchanged from P1-B)

- Dry-run and show every statement, then wait for the human's explicit "go" before anything that creates, drops or writes.
- Never print the key. Never call port 8889.
- `COMPILE USL` **without** `DEPLOY` stores nothing (it returns the model JSON), so use it freely to debug.

## 5. Procedure (attended; the agent stops at each ⏸)

1. **Read-only state.**
   - Run `SHOW NAMESPACES OR TABLES IN lightning.metastore` and `SHOW NAMESPACES OR TABLES IN lightning.metastore.arbiter`.
   - Run `LIST DQ USL` (if any) to see what exists. ⏸
2. **Reproduce the failure safely.**
   - Send the current multi-table DDL **without `DEPLOY`**.
   - Record the full error text (HTTP body) in the report.
   - Also paste the same DDL into the Zetaris UI → *Unified Semantic Layer → New USL* (the UI often shows a more specific parser error). ⏸
3. **Bisect without DEPLOY**, one change at a time, recording each result in a table in the report:
   1. a single table `vendor` with **only `varchar` columns** (mirrors the verified example);
   2. add `int`, then `decimal(14,2)`, then `date`, then `boolean` columns;
   3. a second table with `FOREIGN KEY REFERENCES`;
   4. suspect column names (`text`, `status`, `version`, `category`): test each in isolation. If one is rejected, rename **only in the USL** (e.g. `text` → `doc_text`) and alias it back in the `ACTIVATE … AS SELECT` (`text AS doc_text`) and in USL-layer registry SQL (§6). The DuckDB mirror and the views keep the original name;
   5. the full 10-table DDL.
   Use the official runner for ad-hoc statements:

   ```bash
   python3 ~/zetaris-getting-started/scripts/run_sql.py FILE --dry-run
   ```

   It keeps `COMPILE USL` intact. Alternatively, add `python run.py zetaris exec --file FILE [--yes]` (same REST client, prints the statement first).
4. **Fix `zetaris/sql/03_usl.sql`** to the working form (finding B4):
   - `COMPILE USL IF NOT EXISTS vendor_risk DEPLOY NAMESPACE lightning.metastore.arbiter DDL` followed by the working `CREATE TABLE`s (each on a new line, `;`-separated, no trailing `;`).
   - `UPDATE USL lightning.metastore.arbiter.vendor_risk SET DESCRIPTION '…'`, plus one `SET TABLE DESCRIPTION` per table, written in business language for an analyst. Example: *"One row per vendor onboarding request from procurement; tier inputs and the CLM supplier reference."*
   - `ACTIVATE USL TABLE lightning.metastore.arbiter.vendor_risk.<table> AS SELECT … FROM arbiter.<table>_v`. Use **fully qualified names**, wrap NOT NULL key columns in `COALESCE(…, '')`, and add explicit `CAST`s.
   - `REGISTER DQ <rule> TABLE lightning.metastore.arbiter.vendor_risk.<table> AS <expr>`. Use the qualified table, no alias and no window functions; generate it from `zetaris/dq_rules.yaml`.
   - `RUN DQ TABLE lightning.metastore.arbiter.vendor_risk.<table>` for each table with rules.

   Show the dry run. ⏸ Then `python run.py zetaris onboard --only 03 --yes --skip-exists`.
5. **Live KEV.**
   - Change `zetaris/onboard.py::kev_rest_url` so Zetaris always reads `settings.KEV_URL` (CISA's catalogue via `cisagov/kev-data@develop`), never the repo snapshot. The snapshot stays the DuckDB mirror's source.
   - Re-create `kev_raw` (drop it in the Zetaris UI, which only the human can do), then re-run `--only 02`. ⏸
6. **Switch live mode to the USL.** Set `ZETARIS_QUERY_LAYER=usl` in `.env`. `app/data/registry.py` already renders `{T.<t>}` as `lightning.metastore.arbiter.vendor_risk.<t>`. If any column was renamed in step 3.4, add a per-query `sql_usl:` override in `queries.yaml` that aliases it back, so agents see identical columns on every backend.
7. **Parity.** Run `python run.py zetaris parity`.
   - Expect counts 10/10 (`kev_vuln` against the live count), all registry queries equal, KEV subset, and **DQ invalid-key sets equal (5/5)**.
   - Commit `docs/passes/P1-B_parity.json` with `all_green: true`.
8. **Semantic catalogue for agents** (the "expressive power in a compact format" point).
   - `python run.py zetaris model --export` runs `LOAD USL vendor_risk NAMESPACE lightning.metastore.arbiter` and writes `data/usl/vendor_risk.model.json` (scrubbed of instance ids and timestamps; deterministic key order; committed).
   - `app/data/usl_model.py`:
     - `load_model() -> UslModel` (tables, ordered columns with types, PK, FKs, descriptions; from the committed JSON in every mode, so sample mode sees the same model);
     - `compact_catalogue(model) -> str`: one line per table, `table(pk, fk→table.col, …): description`, plus key columns. This must stay ≤ 1,200 tokens (assert in a test).
   - `PlannerAgent` (LLM path only) gets the compact catalogue in its prompt, in place of raw column lists, plus the registry query ids mapped to the tables they read. The deterministic planner is unchanged.
   - Trace event `PlannerAgent/usl_catalogue` with `usl_model_sha256` and token estimate.
9. **Vendor 360 query.**
   - Add `Q_VENDOR_360` to `queries.yaml`: one statement joining `vendor ⋈ contract (clm_supplier_ref = supplier_ref) ⋈ submission ⋈ vendor_component ⟕ kev_vuln`. It returns one row per vendor (contract status, DPA, hosting, breach hours, patch SLA, count of components, count of distinct KEV CVEs, latest KEV date).
   - It must run on DuckDB and Zetaris with identical columns.
   - The case header (P14-B) and the dossier (P14-A) use it.
10. **Screenshots** (no keys visible), saved to `docs/img/zetaris_usl_erd.png`, `zetaris_usl_dq.png`, `zetaris_usl_query.png`:
    - the USL ERD canvas with relationships;
    - DQ results;
    - `Q_VENDOR_360` running in the SQL editor.
11. **Write `docs/ZETARIS_USL.md`** (§6).

## 6. `docs/ZETARIS_USL.md` (judging artefact; every number measured, with the command that produced it)

1. **Identify the data sources.** A table of the six sources:
   - system, owner role, what it holds, entity, key, how it identifies vendors (`VND-…`, `SUP-…`, free text), licence (synthetic or CC0);
   - why each matters to a control.
2. **Onboard.**
   - Lightning REST tables, then SchemaStore views (flattening `records` with `LATERAL VIEW explode`), then the live KEV feed.
   - Statement counts. Parity proof (counts and hashes against the source APIs).
3. **Build the USL.**
   - A mermaid ERD **generated from `vendor_risk.model.json`** (`python run.py zetaris model --mermaid`): 10 tables, PKs, FKs.
   - Descriptions. The five DQ rules and their live results.
   - The bisect table from §5 step 3, as an honest account of the DDL fixes.
4. **Reflection: how the USL sped us up.** Measured, with commands shown:
   - **Custom Python pipeline:**
     - lines of code Arbiter needs *without* the USL to normalise, join and DQ-check the same data (`app/data/duckdb_backend.py` + `app/data/dq.py` + DuckDB flattening + alias joins in the registry);
     - the number of places a schema change touches.
   - **USL:**
     - DDL lines plus DQ lines;
     - one model reused by every query, the DuckDB mirror and the Planner prompt.
   - **The `Q_VENDOR_360` statement** against the equivalent Python merge code (lines and number of source calls).
   - **Time to add a new source** (worked example: a hypothetical SOC 2 report register). USL path: REST table → view → add table to DDL → `ACTIVATE`. Pipeline path: the files and steps to change.
5. **Day to day.**
   - For the TPRM analyst: one governed definition of "vendor"; DQ problems visible *before* a decision (S13: a DPA flagged signed with no date).
   - For the data owner: descriptions double as documentation.
   - For audit: the decision cites a Zetaris request id against a governed model.
6. **Why it matters to agents.**
   - Typed, keyed, clean tables mean fewer extraction errors.
   - The compact catalogue (N tokens) replaces raw dumps (M tokens, measured).
   - FKs tell the Planner which systems corroborate which claims.
   - DQ flags become evidence gaps instead of silent bad data.
7. **Limits.** Honest: synthetic sources; the same Zetaris instance; anything that still runs on views.

## 7. Acceptance tests (marker `p13`)

| Id | Test |
|---|---|
| P13-T1 | Static: every `ACTIVATE`, `REGISTER DQ`, `RUN DQ` and `UPDATE USL` statement in `03_usl.sql` uses the fully qualified `lightning.metastore.arbiter.vendor_risk.<table>` name. `COMPILE` is one statement with ≥ 10 `CREATE TABLE`s, each starting on a new line |
| P13-T2 | `REGISTER DQ` statements are generated from `zetaris/dq_rules.yaml` (no drift: same rule names and expressions) |
| P13-T3 | `kev_rest_url()` returns `settings.KEV_URL` in every source mode |
| P13-T4 | `load_model()` parses the committed JSON: 10 tables, PKs present, FK targets exist, every table has a description |
| P13-T5 | `compact_catalogue()` is deterministic, lists every table and FK, and is ≤ 1,200 tokens (len/4 heuristic) |
| P13-T6 | The LLM planner prompt contains the compact catalogue. The deterministic plan is unchanged (regression on the e2e examples) |
| P13-T7 | `Q_VENDOR_360` runs on DuckDB for all 32 vendors with the declared columns; KEV counts match `Q_COMPONENT_KEV` |
| P13-T8 `live` | USL tables are activated (`SHOW NAMESPACES OR TABLES` shows 10 activated); counts parity |
| P13-T9 `live` | DQ parity 5/5; `SHOW DQ ALL INVALID TABLE …contract` contains VND-0028's contract |
| P13-T10 `live` | `Q_VENDOR_360` parity between Zetaris (USL) and DuckDB |

The gate `scripts/gates/p13.py` requires `docs/passes/P1-B_parity.json` `all_green == true` with `query_layer == "usl"`, and `docs/ZETARIS_USL.md` sections 1–7 present.

## 8. Cut lines

If the full model still fails after **2 hours** of bisecting:

- deploy the largest subset that compiles (at minimum `vendor`, `contract`, `submission`, `vendor_component`, `kev_vuln`);
- point those tables' queries at the USL, leave the rest on views (per-table layer map in `registry.py`);
- write the remainder up honestly in §6.7.

**Never submit without a deployed, activated USL.**

## 9. Cursor prompt

```
/start-pass 13
You are implementing P13 of Arbiter Release 2: build the Zetaris Unified Semantic Layer for real. This lane is human-attended.
Read: AGENTS.md; docs/spec/release2/README.md; docs/spec/release2/R2_00_ASSESSMENT.md §§3–4; docs/spec/release2/P13_ZETARIS_USL.md; docs/spec/01_DATA_AND_ZETARIS.md §§5–9; docs/passes/P1-B_REPORT.md; and in ~/zetaris-getting-started: AGENTS.md, docs/guides/zetaris-lightning-sql-commands.md §§13–14, docs/guides/zetaris-lightning-sql-companion.md, open_data/usl/sql/01_sic_usl_create.sql and 02_sic_edgar_usl_create.sql.
Follow §5 step by step and stop at every ⏸. Use COMPILE USL without DEPLOY to debug. Never print the key; never call port 8889.
Plan Mode: .cursor/plans/P13.md with the bisect plan, files, and tests P13-T1..P13-T10. Wait for approval.
Tests first (marker p13) → commit → implement → attended procedure.
Finish with docs/passes/P13_REPORT.md (bisect table, final DDL diff, parity) + docs/cursor-usage/P13.md; push p13-usl; delete .cursor/ACTIVE_PASS; stop.
```

## 10. Explain it

1. What exactly was wrong with the first `COMPILE USL`, and how did you prove it?
2. Trace `Q_VENDOR_360` from REST source to USL table to the agent.
3. What does the Planner see from the USL, and why is that better than raw schemas?
4. How many lines of custom pipeline does the USL replace, and where is that measured?
5. Which DQ rule catches Kestrel Docs (VND-0028), and what does the agent do with it?
