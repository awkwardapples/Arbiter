# P1: Data world (A) and Zetaris federation (B)

---

# Lane P1-A: synthetic enterprise world, simulator, query registry, DuckDB mirror

## A1. Goal

A seeded generator produces five fragmented synthetic systems, the KEV snapshot, labels, splits, inline submissions and `input_examples/`. A FastAPI simulator serves them as REST. A query registry with safe parameter rendering runs every query on a DuckDB mirror whose tables and columns equal the USL model. Everything works offline.

## A2. Why it scores

- **Impact:** a realistic TPRM evidence landscape.
- **Technical:** one data path, two interchangeable backends, contract tests.
- **Sponsor Tech:** the shape is designed for Zetaris.
- **Integrity:** sample mode runs real logic on cached data, and nothing leaks labels.

## A3. Read first

- Master spec §§7 (Provenance, CaseInput) and 8.1
- `01_DATA_AND_ZETARIS.md` §§1–4, 5.4, 6, 7
- `02_POLICY.md` §§2–4 (tiering, controls, derived facts: needed to author tiers, `truth_facts` and labels)
- `03_EVALUATION.md` §1 (label and split formats)

## A4. Depends on

P0.

## A5. Deliverables

| File | Responsibility |
|---|---|
| `data/generator/scenarios.yaml` | The 32 vendors (ids `VND-0001`…`VND-0032`). Named demo vendors are fixed as in 01 §4; others get word-list names that are clearly fictional. Per vendor: scenario codes, tier drivers, answer polarity per question (`affirm`, `deny`, `vague`, `hedged_false`, `numeric:<value>`, `missing`), documents, contract settings, incidents, watchlist hits, components, expected outcome and reasons (→ labels). Also the 4 inline submissions (01 §4) and the 6 input examples (§A6) |
| `data/generator/phrasebank.yaml` | 01 §4.1. At least 5 variants per polarity per question, including negations and false friends |
| `data/generator/generate.py` | `python run.py generate-data --seed 2026 --as-of 2026-10-26`. The `--as-of` date is written into every envelope and is the default for `ARBITER_AS_OF`. Deterministic (`random.Random(seed)`; sorted iteration). Writes §A6 outputs. **Asserts scenario expectations** using the same KEV match rule as the registry (see note below) and fails loudly on mismatch |
| `data/kev/fetch_kev.py` | `python run.py generate-data --refresh-kev` downloads the live catalogue from `KEV_URL` (default `https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json`; the mirror's default branch is `develop`). It keeps the top-level structure and filters to entries matching any catalogue product plus 50 others (seeded). Writes `data/kev/kev_snapshot.json` and `data/kev/SOURCE.md` (URL, catalogVersion, dateReleased, retrieval time, CC0 notice, "no CISA endorsement") |
| `data/README.md` | Synthetic label; every source and its licence; how to regenerate; size |
| `sources/simulator.py` | FastAPI on `0.0.0.0:8100` (`python run.py sources`). Serves 01 §2 endpoints from `data/sample/systems/*.json` (loaded once) and `GET /health` (`{status, as_of, counts}`). Optional fault injection for demos: `SIM_FAULTS="itsm:500x2"` makes the next two ITSM calls return 500 |
| `app/data/backend.py` | Fill the P0 protocol. `FallbackBackend(primary, secondary, tracer)`: on `UpstreamTimeout`/`UpstreamError` it runs the secondary for that query; on `Unauthorized` it **pins the secondary for the rest of the run**. Either way it sets `fallback_from` and emits trace status `fallback` |
| `app/data/registry.py` | Load `queries.yaml`. `render(query_id, params, *, backend, layer) -> str`. Validate params (`vendor_id ^VND-\d{4}$`; names normalised to `[a-z0-9 .&-]{1,120}`; lists ≤ 20; dates ISO). Render literals with doubled single quotes; dates as `CAST('YYYY-MM-DD' AS DATE)`; resolve `{T.<table>}`. No string formatting of untrusted values anywhere else |
| `app/data/queries.yaml` | The 15 queries in 01 §6, each with `id, description, sql \| handler, params, columns, systems, control_ids`. `Q_DQ_INVALID` uses `handler: dq_invalid` |
| `app/data/duckdb_backend.py` | In-memory DuckDB. Builds the 10 USL-named tables (`vendor, vendor_alias, contract, incident, watchlist_entry, submission, submission_answer, submission_document, vendor_component, kev_vuln`) from the sample JSON with exact column names and types, once per process, in < 2 s. Exposes only `run()` |
| `app/data/inline.py` | `InlineBackend(submission)`: answers `Q_VENDOR_PROFILE`, `Q_SUBMISSION`, `Q_SUBMISSION_ANSWERS`, `Q_SUBMISSION_DOCUMENTS` and components from the request body (`backend="inline"`, vendor ref `SUB-<sha8 of canonical submission>`, contract status `none`). Other queries route to the main backend via `Q_KEV_BY_PRODUCTS`, `Q_WATCHLIST_ALL` and `Q_INCIDENTS_BY_NAME` |
| `app/data/dq.py` | Load `zetaris/dq_rules.yaml`. `invalid_keys(backend, table) -> set[str]`. DuckDB: `SELECT <pk> FROM <t> WHERE NOT COALESCE(<expr>, FALSE)` |
| `app/data/factory.py` | `get_backend(settings, tracer, submission=None)`. SAMPLE_MODE gives DuckDB; otherwise `FallbackBackend(ZetarisBackend, DuckDB)` if `app.data.zetaris` is implemented, else DuckDB with a trace note. Inline cases are wrapped with `InlineBackend` |
| `app/data/status.py` | `check() -> dict` (DuckDB table counts; Zetaris status delegated if present) |
| `zetaris/dq_rules.yaml` | 01 §5.4 |
| `input_examples/example_{1..6}.json`, `input_examples/expected.json` | See §A6 |
| `app/cli/data.py` | `generate-data`, `sources` |

**Scenario-authoring rules the generator must respect:**

1. **T1 corroboration.** Clean T1 vendors (S03, and VND-0007's other controls) get a SOC 2 Type II summary whose text corroborates MFA for privileged and remote access. P3's Challenger requires a non-answer source for C01 at T1 (02 §3, `t1_corroboration`).
2. **Plain phrasing for input examples.** The vendors used in `input_examples/` use affirm, deny, vague and numeric phrasings that a deterministic extractor can read. False friends and tricky negations appear only in eval vendors (S05, S08 and some S01/S02), where they separate LLM extraction from the fallback.
3. **The S12 precedent pair** (VND-0011, VND-0012) shares a category and is T2. Both have a current bridge letter, no SOC 2 or ISO, and everything else clean, so the only failing required control is C05.
4. **Verifiable claims.** Every vendor answer the policy cross-checks (Q08, Q09, Q10, Q11, Q12, Q13, Q15) has a matching system-of-record row, so the Evaluator's verify loop always has something to query.

**KEV match rule** (one implementation, used by the generator assert *and* mirrored in SQL):

```
lower(k.vendor_project) == lower(c.vendor_project) and lower(c.product) in lower(k.product)
```

## A6. Outputs (committed; total < 2 MB)

- `data/sample/systems/{procurement_vendors,procurement_vendor_aliases,clm_contracts,itsm_incidents,grc_watchlist,trust_submissions,trust_answers,trust_documents,trust_components}.json`. Each uses the flat envelope from 01 §1.4.
- `data/kev/kev_snapshot.json`
- `data/evals/labels.jsonl` (03 §1.1) and `data/evals/splits.json` (03 §1.2, with sha256 fields)
- `data/evals/truth_facts.jsonl`: per vendor, the ground-truth value and state of every fact key the scenario plants (what a perfect reader would derive). It is used by P3-T16 (label oracle) and the `fact_accuracy` metric. **Never read by `app/`**
- `data/evals/inline/{inline_clean_t3,inline_injection,inline_missing,inline_kev}.json`
- `input_examples/`:

| File | Content | Expected |
|---|---|---|
| `example_1.json` | `{"vendor_id": "VND-0003"}` | APPROVE |
| `example_2.json` | `{"vendor_id": "VND-0007"}` | ESCALATE (contradiction + KEV) |
| `example_3.json` | `{"vendor_id": "VND-0015"}` | ESCALATE (injection) |
| `example_4.json` | `{"vendor_id": "VND-0022"}` | REQUEST_INFO |
| `example_5.json` | `{"vendor_id": "VND-0019"}` | DECLINE (contract pending `tprm_lead`) |
| `example_6.json` | Inline submission, T3, internal data only, clean | APPROVE |

  `expected.json` maps each file to `{outcome, reasons}` for the e2e test. It is written by the generator from the scenario spec.

## A7. Acceptance tests (marker `p1a`)

| Id | Test |
|---|---|
| P1-T1 | Running the generator twice with the same seed gives byte-identical files (sha256 per file). A different seed changes the non-fixed names |
| P1-T2 | Every system file has the flat envelope; every row value is a scalar; `count == len(records)` |
| P1-T3 | **No label leakage:** no served record contains a scenario code (`S01`…`S14`), an outcome word in upper case, or the strings `expected`/`label` |
| P1-T4 | **Scenario assertions:** for every vendor, the planted evidence matches `scenarios.yaml`. S09 vendors have ≥ 1 KEV match under the match rule; vendors without S09 have 0; S06 contract region ≠ claimed region; S10 alias is on the watchlist; S13 `dpa_signed=true` with a null date |
| P1-T5 | **Contract test:** every registry query runs on DuckDB for every vendor with exactly the declared `columns`, in order |
| P1-T6 | Parameter validation rejects `VND-0001' OR '1'='1`, a 21-item list and non-ISO dates. Names with quotes are rendered safely; the rendered SQL never contains an unescaped quote |
| P1-T7 | DQ: DuckDB flags `dq_contract_dpa_date` for VND-0028's contract and no false positives on clean vendors |
| P1-T8 | Simulator (FastAPI TestClient): each endpoint returns the file contents; `/health` counts match; `SIM_FAULTS` returns 500 exactly N times |
| P1-T9 | `splits.json` is stratified (every scenario with n ≥ 2 appears in both splits); the recorded sha256 values match |
| P1-T10 | Every `input_examples/*.json` validates as `RunRequest`; `expected.json` covers all six; `example_6` produces `SUB-` vendor refs through `InlineBackend` |
| P1-T11 | **ANSI subset:** registry SQL uses only allowed functions and keywords (01 §6); there are no backend-specific functions |
| P1-T12 | The KEV snapshot keeps the top-level keys `title, catalogVersion, dateReleased, count, vulnerabilities` and the entry keys of the live schema; `count == len(vulnerabilities)` |
| P1-T13 | `FallbackBackend` uses the secondary on `UpstreamTimeout` for that query only; on `Unauthorized` it pins the secondary for later queries too. It sets `fallback_from` and emits one trace event with status `fallback` per fallback |
| P1-T14 | `Q_VENDOR_COMPONENTS` returns every declared component; a vendor with none returns 0 rows. `Q_WATCHLIST_ALL` returns the whole watchlist; the Python name screen finds S10's exact match and a planted near-match, with no false exact matches on clean vendors |

## A8. Verification

```
python run.py generate-data --refresh-kev --seed 2026 --as-of 2026-10-26   # once (network)
python run.py generate-data --seed 2026 --as-of 2026-10-26                 # offline, idempotent
python run.py sources &  curl http://localhost:8100/health
python scripts/tasks.py verify-pass --pass 1a
```

## A9. Definition of done

- [ ] Data committed and under 2 MB.
- [ ] All tests green.
- [ ] Every registry query returns plausible rows for the 9 named vendors (paste a summary table into the report).
- [ ] The report lists every vendor with scenario, tier and expected outcome (copied from labels).

## A10. Cut lines

`SIM_FAULTS`; the near-match watchlist decoy.

## A11. Cursor prompt

```
/start-pass 1a
You are implementing lane P1-A of Arbiter (synthetic world, simulator, registry, DuckDB mirror).
Read: AGENTS.md; docs/spec/00_MASTER_SPEC.md §§7, 8.1; docs/spec/01_DATA_AND_ZETARIS.md §§1–4, 5.4, 6, 7; docs/spec/02_POLICY.md §§2–4; docs/spec/03_EVALUATION.md §1; docs/spec/passes/README.md §3; docs/spec/passes/P1_DATA_ZETARIS.md lane A only.
Plan Mode: write .cursor/plans/P1-A.md (files within lane ownership, interfaces, tests P1-T1..P1-T14). Wait for approval.
Then tests first (marker p1a) → commit → implement until `python scripts/tasks.py verify-pass --pass 1a` is green.
The generator must derive labels from scenarios.yaml only, never from running Arbiter. Data is synthetic; say so in data/README.md.
Finish with docs/passes/P1-A_REPORT.md + docs/cursor-usage/<LABEL>.md; push p1a-data; delete .cursor/ACTIVE_PASS; stop.
```

## A12. Explain it

1. How does Arbiter know an ITSM incident with free-text "QUILLFEATHER PAYROLL CLOUD LTD." belongs to VND-0007?
2. Why are records flat, with comma-joined lists?
3. How is vendor input prevented from becoming SQL?
4. What would a judge's own inline submission touch in the data layer?
5. How do the generator's assertions protect the eval from silently wrong labels?

---

# Lane P1-B: Zetaris live federation (human-attended)

## B1. Goal

Zetaris federates the simulator's five systems and the public KEV feed:

- REST tables;
- SchemaStore views;
- the USL model `arbiter.vendor_risk` with DQ rules.

`ZetarisBackend` runs every registry query through the Zetaris REST SQL API. A parity report proves Zetaris and DuckDB return identical results.

## B2. Why it scores

Zetaris is **required**, so it must be load-bearing. Federation of public and private data, USL and DQ is the strongest Data-layer story. Request ids appear in every fact's provenance.

## B3. Read first

- Master spec §§8.1, 12
- `01_DATA_AND_ZETARIS.md` §§5, 6, 8, 9
- The Zetaris getting-started repo: `AGENTS.md`, `docs/guides/zetaris-lightning-sql-commands.md`, `docs/guides/zetaris-lightning-sql-companion.md`, `open_data/rest_apis/sql/non_rate_limited/02_pokeapi_create.sql`, `open_data/usl/sql/01_sic_usl_create.sql`

## B4. Depends on

P0 and P1-A. The human must have Zetaris running (`verify.sh` 9/9) and the API key in `.env`.

## B5. Safety rules for the agent (from the Zetaris AGENTS.md, binding)

- Never create, request, print or log the Zetaris API key. It is read from `.env` by `app/config.py` only.
- Start read-only (`SELECT 1`, `SHOW LIGHTNING DATABASES`, `SHOW DATASOURCES`, `SHOW NAMESPACES OR TABLES IN lightning.metastore`).
- **Dry-run every create script and show the statement list. Wait for an explicit "go" before executing anything that creates, drops or writes.**
- One statement per call, no trailing semicolon. Never split `COMPILE USL`.
- Never call port 8889. Do not hand-write DROP statements; teardown is via the Zetaris UI or `onboard.py teardown` with confirmation.

## B6. Deliverables

| File | Responsibility |
|---|---|
| `app/data/zetaris.py` | `ZetarisBackend(settings, registry, tracer)`. `run()` renders for `layer = settings.ZETARIS_QUERY_LAYER`, then sends `POST {ZETARIS_REST_URL}/sql-editor/sqls/run` with headers `Authorization: Bearer <key>`, `X-Org-ID`, `X-Request-ID: uuid4`, `Content-Type: application/json` and body `{"queryId": uuid4, "sql": sql, "source": "SqlEditor", "limit": 1000}`. The timeout is `ZETARIS_TIMEOUT_SECONDS`. Tenacity: 3 attempts on timeout or 5xx with backoff of 1 s and 3 s, each traced as `retrying`. A 401/403 raises `Unauthorized` with no retry (`FallbackBackend` then pins DuckDB for the run) and marks the backend degraded for 60 s. Normalise `data` to dicts (list of dicts; `{columns, rows}`; or positional rows mapped to registry `columns`), coercing booleans, ints and dates. Emit one trace event per query: `agent_name` (the caller), `action="query_zetaris"`, `query_id`, `rows`, `backend="zetaris"`, `zetaris_request_id`, `latency_ms`. `dq_invalid(table)` runs `SHOW DQ ALL INVALID TABLE …` and parses the `records` JSON. `status()` runs `SELECT 1` |
| `zetaris/sources.yaml` | REST table → `{simulator_path, raw_file}` |
| `zetaris/sql/01_sources.sql` | `ARBITER_SRC` database, container `arbiter`, 9 REST tables `*_raw` using `{URL:<table>}`, and 9 flattening views `arbiter.<name>_v` with columns equal to the USL tables and explicit casts |
| `zetaris/sql/02_kev.sql` | `ARBITER_PUB`, `kev_raw` on the KEV GitHub URL, `CACHE TABLE arbiter_pub.kev_raw`, view `arbiter.kev_vuln_v` (01 §5.2) |
| `zetaris/sql/03_usl.sql` | `CREATE NAMESPACE IF NOT EXISTS lightning.metastore`, then `… lightning.metastore.arbiter`; the single `COMPILE USL` (01 §5.3, verified against the commands guide); 10 `ACTIVATE USL TABLE … AS SELECT … FROM arbiter.<t>_v`; `REGISTER DQ` for each rule in `dq_rules.yaml` (generated, not hand-copied); `RUN DQ TABLE …` |
| `zetaris/onboard.py` | `python run.py zetaris onboard [--dry-run] [--skip-exists] [--only 01\|02\|03]`. Splits on `-- @@stmt` only; substitutes placeholders; prints each statement; requires `--yes` for a real run; stops on the first error (unless "already exists" under `--skip-exists`); logs to `logs/zetaris-onboard-<ts>.jsonl` with no secrets |
| `zetaris/parity.py` | `python run.py zetaris parity`, per 01 §8: counts versus the simulator `count`; per-query row counts and sha256 of sorted canonical rows for every vendor; KEV subset; DQ key sets. Writes `docs/passes/P1-B_parity.json` (committed evidence) and prints a summary. `kev_vuln` counts are compared with the live KEV `count`, and the KEV queries are excluded from row parity (01 §8) |
| `zetaris/README.md` | What is registered, how to onboard, fallback B, the views fallback, troubleshooting |
| `app/cli/zetaris.py` | `zetaris onboard \| parity \| status` |
| `tests/fixtures/zetaris_run_response.json` | **A real** captured response to `SELECT 1 AS one, 'a' AS s` and to one registry query, with the key and any org data scrubbed |

## B7. Attended procedure (do it in this order; the agent stops at each ⏸)

1. Run the preflight: `python run.py zetaris status` gives `SELECT 1` → 1. ⏸
2. Start the simulator. Prove reachability from the Zetaris `driver` and `api` containers (01 §9.2). ⏸ *If this fails after 30 minutes, set `ZETARIS_SOURCE_MODE=github_raw`, push `data/sample/systems` to `main`, and continue.*
3. Capture the fixture. Build and unit-test the normaliser.
4. Run `onboard --only 01 --dry-run` and show the statements. ⏸ Then run `--yes`. Verify counts.
5. Run `--only 02` the same way (KEV).
6. Run `--only 03` the same way (USL). *If `COMPILE`/`ACTIVATE` fails after 90 minutes, set `ZETARIS_QUERY_LAYER=views` and record it.*
7. Run `parity`. Fix mismatches or explain them in the report.
8. Run `python run.py assess --input input_examples/example_2.json` in live data mode once P3 exists (this step moves to P3's live check if P3 is not merged yet).

## B8. Acceptance tests (marker `p1b`; `live` ones also need `ARBITER_LIVE_TESTS=1`)

| Id | Test |
|---|---|
| P1-T20 | respx: request URL, method, headers present (and `X-Request-ID` is a UUID4), body keys and types, and no trailing semicolon in `sql` |
| P1-T21 | The normaliser on the **captured fixture** yields the expected dicts; positional rows map to registry columns; types are coerced |
| P1-T22 | Two 5xx responses then a 200 succeed with 2 `retrying` events. Three 5xx responses raise; `FallbackBackend` returns DuckDB rows with `fallback`. A 401 makes no retry and raises `Unauthorized` |
| P1-T23 | `onboard.py` splits only on `-- @@stmt`; a multi-table `COMPILE USL` stays one statement; placeholders substitute for both source modes; a real run without `--yes` refuses; dry-run output has no secrets |
| P1-T24 | Logs and traces never contain the Authorization header or key (caplog plus trace file scan) |
| P1-T25 `live` | USL (or views) counts equal the simulator `count` for the 9 source tables, and `kev_vuln` equals the live KEV `count` |
| P1-T26 `live` | Query parity: every registry query except `Q_COMPONENT_KEV` and `Q_KEV_BY_PRODUCTS`, × every vendor, gives equal row counts and hashes on Zetaris and DuckDB |
| P1-T27 `live` | DQ parity: invalid key sets are equal |
| P1-T28 `live` | KEV: every snapshot CVE matching a catalogue product is present live |

## B9. Verification

```
python run.py zetaris status
python run.py zetaris onboard --dry-run
python run.py zetaris parity
python scripts/tasks.py verify-pass --pass 1b
ARBITER_LIVE_TESTS=1 pytest -m "p1b and live"
```

The gate `scripts/gates/p1b.py` passes if `docs/passes/P1-B_parity.json` has `all_green: true`, **or** `docs/passes/P1-B_REPORT.md` has a "Parity exceptions" section that lists every mismatch with a cause.

## B10. Definition of done

- [ ] Live parity is green (or explained).
- [ ] The fixture is captured.
- [ ] The query layer is recorded (`usl` or `views`) and the source mode recorded (`simulator` or `github_raw`).
- [ ] Zetaris UI screenshots are saved to `docs/img/zetaris_*.png` for the deck (no keys visible).

## B11. Cut lines (in order)

1. DQ rules in Zetaris (keep DuckDB DQ and say so).
2. USL (keep views).
3. `CACHE TABLE`.

Never cut the REST tables, the views, the KEV join or `ZetarisBackend`.

## B12. Cursor prompt

```
/start-pass 1b
You are implementing lane P1-B of Arbiter (Zetaris live federation). This lane is human-attended.
Read: AGENTS.md; docs/spec/00_MASTER_SPEC.md §§8.1, 12; docs/spec/01_DATA_AND_ZETARIS.md §§5, 6, 8, 9; docs/spec/passes/P1_DATA_ZETARIS.md lane B; and in the Zetaris clone at ~/zetaris-getting-started: AGENTS.md and docs/guides/zetaris-lightning-sql-commands.md + -companion.md.
Obey §B5 safety rules exactly: read-only first; dry-run and show statements; wait for my explicit "go" before any create; never print or log the API key; never call port 8889.
Plan Mode: write .cursor/plans/P1-B.md with the attended procedure §B7 and tests P1-T20..P1-T28. Wait for approval.
Tests first (marker p1b) → commit → implement → follow §B7 step by step, stopping at every ⏸.
Finish with docs/passes/P1-B_REPORT.md (include query layer, source mode, parity summary or exceptions) + docs/cursor-usage/<LABEL>.md; push p1b-zetaris; delete .cursor/ACTIVE_PASS; stop.
```

## B13. Explain it

1. Trace one fact, "residency = US", from the simulator, through Zetaris (table → view → USL), to the decision's provenance.
2. Why is the KEV join a *federated* query, and why does that matter for the story?
3. What happens if Zetaris times out mid-run? And on a 401?
4. What does parity prove, and what would a mismatch mean?
5. What is fallback B, and why is it honest?
