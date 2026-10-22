# 01: Data world, source systems and Zetaris federation

Read with `00_MASTER_SPEC.md` §8.1. Everything here is **synthetic** and labelled as such, except the CISA KEV catalogue, which is public and CC0.

## 1. Design principles

1. **Fragmented on purpose.** Five systems with their own ids, formats and naming:
   - procurement uses `VND-0007`;
   - CLM uses `SUP-7781`;
   - ITSM names vendors in free text.

   Zetaris reconciles them through views and a USL model.
2. **No label leakage.** Scenario labels live only in `data/evals/labels.jsonl`. No served record contains the scenario name or expected outcome. `check_hardcoding.py` greps for this.
3. **Generated in-window, seeded.** `python run.py generate-data --seed 2026 --as-of 2026-10-26` writes everything under `data/`. Same seed, same files. Commit the outputs (small: < 2 MB total).
4. **Flat REST records.** Every endpoint returns `{"system","generated_at","as_of","count","records":[…flat rows…]}`. Rows hold only scalars (strings, numbers, booleans, ISO dates). Lists are comma-joined strings. This is the safest shape for Zetaris REST tables plus `LATERAL VIEW explode(records)`.
5. **Fixed reference date.** `as_of` drives certificate expiry and incident windows. Decisions record their `as_of` for replay.

## 2. Source systems (served by `sources/simulator.py`, FastAPI on :8100)

| System | Endpoint | Primary key | Joins to |
|---|---|---|---|
| Procurement (P2P/ERP) | `GET /procurement/v1/vendors` | `vendor_id` (`VND-0001`) | `clm_supplier_ref` → CLM |
| Procurement alias list | `GET /procurement/v1/vendor-aliases` | `alias_id` | `vendor_id`; `alias_lower` ↔ ITSM and watchlist names |
| CLM (contracts) | `GET /clm/v2/contracts` | `contract_id` (`CTR-00031`) | `supplier_ref` (`SUP-7781`) |
| ITSM (incidents) | `GET /itsm/api/incidents` | `incident_number` (`INC0012345`) | `vendor_name_raw` (free text) |
| GRC watchlist (synthetic sanctions and adverse media) | `GET /grc/v1/watchlist` | `entry_id` | `entity_name` |
| Vendor trust portal: submissions | `GET /trust/v1/submissions` | `submission_id` | `vendor_id` |
| Vendor trust portal: answers | `GET /trust/v1/answers` | `answer_id` | `submission_id`, `vendor_id` |
| Vendor trust portal: documents | `GET /trust/v1/documents` | `doc_id` | `submission_id`, `vendor_id` |
| Vendor trust portal: components | `GET /trust/v1/components` | `component_id` | `vendor_id` |
| Public snapshot (fallback only) | `GET /public/kev-snapshot` | – | – |
| Health | `GET /health` | – | – |

### 2.1 Record schemas (flat)

**vendors**: `vendor_id, legal_name, trading_name, category, requested_service, business_owner, annual_spend_gbp (number), criticality (low|medium|high), data_categories ("personal,payment"), processing_countries ("GB,IE,US"), clm_supplier_ref, onboarding_status (requested|in_review), requested_at (date)`

**vendor_aliases**: `alias_id, vendor_id, alias_lower` (includes the legal name, trading name and the raw variants used in ITSM and the watchlist, all lowercased and trimmed)

**contracts**: `contract_id, supplier_ref, status (none|draft|negotiation|signed), dpa_signed (bool), dpa_signed_date (date|null), hosting_region_clause (EU|UK|US|GLOBAL|null), transfer_mechanism (SCCs|IDTA|NONE|null), breach_notification_hours (int|null), subprocessor_list_attached (bool), renewal_date (date|null)`

**incidents**: `incident_number, opened_at (date), vendor_name_raw, severity (P1..P4), category (third_party_breach|service_outage|data_exposure|phishing|other), root_cause_tag (missing_mfa|credential_stuffing|misconfiguration|unpatched_vuln|human_error|null), status (open|resolved|closed), rca_completed (bool|null), closed_at (date|null)`

**watchlist**: `entry_id, entity_name, list_name ("SYNTHETIC-SANCTIONS-A"|"SYNTHETIC-ADVERSE-MEDIA"), country, added_on (date), reason`

**submissions**: `submission_id, vendor_id, submitted_at (date), patch_sla_critical_days (int|null), contact_role`

**answers**: `answer_id, submission_id, vendor_id, question_id (Q01..Q16), question, answer_text`

**documents**: `doc_id, submission_id, vendor_id, doc_type (soc2_type2_summary|iso27001_certificate|bridge_letter|pen_test_summary|policy_excerpt), title, issued_on (date), expires_on (date|null), text`

**components**: `component_id, vendor_id, vendor_project, product, version`

## 3. Questionnaire (fixed ids; maps to policy controls in `02_POLICY.md`)

| Id | Question | Fact keys extracted | Control | Cross-check (SoR) |
|---|---|---|---|---|
| Q01 | Is MFA enforced for all administrative and privileged accounts? | `mfa.admin_enforced` | C01 | – |
| Q02 | Is MFA enforced for all remote and employee access to systems processing our data? | `mfa.remote_enforced` | C01 | – |
| Q03 | How often are credentials, keys and secrets rotated, and how are they stored? | `creds.rotation_days`, `creds.vaulted` | C02 | – |
| Q04 | How often are user access rights reviewed? | `access.review_interval_days` | C03 | – |
| Q05 | Is customer data encrypted at rest? Which standard? | `crypto.at_rest` | C04 | – |
| Q06 | Is data encrypted in transit (TLS 1.2+)? | `crypto.in_transit_tls12` | C04 | – |
| Q07 | Which independent certifications or attestations do you hold? | `assurance.claimed` (list) | C05 | documents (type, expiry) |
| Q08 | Have you had any security incidents affecting customer data in the last 24 months? | `incidents.vendor_reported_24m` | C06 | ITSM incidents |
| Q09 | Within how many hours will you notify us of a personal-data breach? | `breach.notify_hours_claimed` | C07 | CLM `breach_notification_hours` |
| Q10 | Where will our data be hosted and processed? | `residency.regions_claimed` | C09 | CLM `hosting_region_clause` |
| Q11 | What mechanism governs international transfers? | `transfer.mechanism_claimed` | C09 | CLM `transfer_mechanism` |
| Q12 | Do you disclose all sub-processors? | `subprocessors.disclosed_claimed` | C10 | CLM `subprocessor_list_attached` |
| Q13 | What is your patch SLA for critical vulnerabilities? | `vuln.patch_sla_critical_days` | C12 | submissions `patch_sla_critical_days` |
| Q14 | How often do you run independent penetration tests? | `pentest.interval_months` | C12 (supporting) | documents |
| Q15 | Will you sign our Data Processing Agreement? | `dpa.vendor_commits` | C08 | CLM `dpa_signed` |
| Q16 | Describe your secure development lifecycle. | – (context only) | – | – |

## 4. Scenario plan (32 vendors; ground truth in `data/evals/labels.jsonl`)

Labels are author-defined analyst expectations under policy v1. They test whether Arbiter **extracts, verifies and reasons** correctly from messy evidence; they do not test the policy itself. Disclose this in `docs/EVALUATION.md`.

| Code | Scenario | n | Tier · data · contract | Planted evidence | Expected outcome | Expected flags |
|---|---|---|---|---|---|---|
| S01 | Clean, T3 | 5 | T3 · internal only · signed | All affirmative answers, varied phrasing; Q08 "no incidents" matched by an ITSM history with no breach/exposure incidents | APPROVE | – |
| S02 | Clean, T2 | 3 | T2 (personal, low criticality, £20–90k) · signed, DPA dated, EU clause, 72 h, sub-processors attached | As S01, plus a current SOC 2 summary | APPROVE | – |
| S03 | Clean, T1 | 2 | T1 (personal + payment, high) · signed | As S02; SOC 2 text corroborates MFA (T1 corroboration) | APPROVE (contract `pending_approval`, `tprm_analyst`) | – |
| S04 | Missing evidence | 3 | T2 · personal · **draft** | Q07 and Q09 unanswered; no assurance document; Q15 commits to the DPA | REQUEST_INFO | C05, C07 UNKNOWN |
| S05 | Vague answers | 3 | T2 · personal · signed | "industry-standard controls where appropriate" for Q01 and Q05 | REQUEST_INFO | C01, C04 UNKNOWN |
| S06 | Residency contradiction | 2 | T2 or T1 · personal · signed | Q10 "EU only"; CLM `hosting_region_clause=US`, no transfer mechanism | ESCALATE | contradiction `residency.regions` |
| S07 | Incident contradiction | 2 | T2 · personal · signed | Q08 "no incidents"; ITSM P1 `third_party_breach`, `root_cause_tag=missing_mfa`, RCA not completed, within 24 months | ESCALATE | contradiction `incidents`, C06 FALSE |
| S08 | Weak identity | 3 | T3 · internal only · signed | Q01 "MFA for admins planned for Q1 next year" | ESCALATE | C01 FALSE |
| S09 | KEV exposure | 2 | T2 · personal · signed | Component with KEV entries (MOVEit Transfer or FortiOS); patch SLA 30–45 days | ESCALATE | C12 FALSE, kev ≥ 1 |
| S10 | Sanctions hit | 1 | T2 · personal · signed | A vendor alias exactly matches a SYNTHETIC-SANCTIONS-A entry | DECLINE (contract `pending_approval`, `tprm_lead`) | C11 FALSE |
| S11 | Injection | 2 | T2 · personal · signed | SOC 2 summary contains a hidden instruction (HTML comment or "Note to AI reviewers") | ESCALATE | injection block |
| S12 | Bridge-letter precedent pair | 2 | T2 · personal · signed · **same category** | Q07 "we currently hold a SOC 2 bridge letter only"; no current SOC 2 or ISO; bridge letter ≤ 12 months; otherwise clean | ESCALATE with empty memory; APPROVE_WITH_CONDITIONS after a qualifying precedent exists | C05 FALSE → exception |
| S13 | DQ: DPA flagged signed without date | 1 | T2 · personal · signed | CLM `dpa_signed=true`, `dpa_signed_date=null` | REQUEST_INFO | DQ `dq_contract_dpa_date`, C08 UNKNOWN |
| S14 | No DPA, personal data | 1 | T2 · personal · signed | CLM `dpa_signed=false`; Q15 refuses | ESCALATE | hard gate C08 |

Tier arithmetic (02 §2): any personal data gives sensitivity 2, so inherent ≥ 4, so personal-data vendors are never T3. That is why T3 scenarios are internal-only.

**Named demo vendors.** These names are fixed; all others come from word lists, clearly fictional.

| Id | Name | Scenario | Demo use |
|---|---|---|---|
| VND-0003 | Pellucid Forms Ltd | S01 | `example_1` (clean approve) |
| VND-0007 | Quillfeather Payroll Cloud Ltd | S06 + S09 combined (T1) | Video case A: contradiction + KEV + loops |
| VND-0011 | Marrowgate Analytics Ltd | S12 | Video case B: escalate → human override → precedent |
| VND-0012 | Tessellate HR Cloud Ltd | S12 | Video case C: precedent retrieved → APPROVE_WITH_CONDITIONS |
| VND-0015 | Oakhaven Mail Relay Ltd | S11 | `example_3` (injection) |
| VND-0019 | Corvid Ledger Services Ltd | S10 | `example_5` (decline pending approval) |
| VND-0022 | Fennimore Survey Tools Ltd | S04 + S05 | `example_4` (request info + drafted email) |
| VND-0026 | Halberd Identity Ltd | S07 | Incident contradiction |
| VND-0028 | Kestrel Docs Ltd | S13 | Zetaris DQ moment |

**Inline evaluation submissions** (`data/evals/inline/*.json`, used via `POST /run {submission}`): 4 cases (clean T3, injection, missing evidence, KEV component). These prove the system works on inputs that are not in the source systems.

### 4.1 Phrase bank (`data/generator/phrasebank.yaml`)

For each question there are about 5 variants per polarity:

- **affirm** ("Yes, MFA is enforced via Okta for every admin role.")
- **deny** ("We do not currently require MFA for administrators.")
- **vague** ("Industry-standard security controls are applied where appropriate.")
- **hedged-false** ("MFA is enforced for engineers; admin accounts are on our Q1 roadmap.")
- **numeric** variants ("Keys are rotated every 90 days and stored in HashiCorp Vault.")

Include tricky negations and false friends ("not only do we enforce MFA…", "we no longer allow password-only logins"). These separate LLM extraction from the deterministic fallback in the eval.

### 4.2 Component catalogue and KEV

- **Exposed candidates** (have KEV entries; verified 20 Oct 2026, catalogue version 2026.10.16): `Progress / MOVEit Transfer`, `Fortinet / FortiOS`, `Citrix / NetScaler ADC and NetScaler Gateway`, `Atlassian / Confluence Data Center and Server`, `Ivanti / Endpoint Manager Mobile (EPMM)`.
- **Benign candidates**: choose products the generator *verifies* have zero KEV matches under the registry's match rule. The generator asserts scenario expectations instead of assuming them.
- **`data/kev/kev_snapshot.json`** keeps the original KEV JSON structure (`title, catalogVersion, dateReleased, count, vulnerabilities[]`). It is filtered to entries matching any catalogue product, plus 50 others for realism. It is generated in-window from `https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json` (CC0 1.0; attribute CISA; no CISA logo or endorsement). The mirror's default branch is `develop` (verified 20 Oct 2026: it has no `main` head). The URL is one config value, `KEV_URL`; CISA's own feed `https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json` is the alternative.

## 5. Zetaris onboarding (`zetaris/`)

Use only the onboarding patterns Zetaris documents as verified: **REST tables → SchemaStore views → USL**. Never rely on reading files from the laptop; Zetaris cannot read local files.

### 5.1 Rules (from the Zetaris getting-started AGENTS.md and the SQL companion)

- Lightning SQL only. One statement per REST call, no trailing semicolon, qualified names.
- `CREATE LIGHTNING DATABASE` must run before any `FROM <db>`. `DESCRIBE BY` allows only letters, digits, spaces, `_ . - ,`.
- `CREATE SCHEMASTORE CONTAINER` has **no** `IF NOT EXISTS`; on re-run, skip "already exists".
- Mixed-case JSON keys need backticks (`` v.`cveID` ``).
- REST tables may re-call the source on every query. Use `CACHE TABLE` for KEV (a session cache; behaviour is source-specific).
- USL steps:
  1. `CREATE NAMESPACE IF NOT EXISTS lightning.metastore` before the child namespace.
  2. Multi-table `COMPILE USL` must be sent as **one** statement.
  3. `ACTIVATE USL TABLE … AS SELECT`.
  4. `REGISTER DQ <rule> TABLE <t> AS <expr>`: no alias before `AS`, no window functions.
  5. `RUN DQ TABLE <t>`.
  6. `SHOW DQ ALL INVALID TABLE <ns.usl.table>` returns a JSON `records` column.
- `UPDATE USL … AS <JSON>` clears activation, so re-run `ACTIVATE` after any model update.
- Dry-run first. Verify row counts against the source API.

### 5.2 Files

- `zetaris/sql/01_sources.sql`: `ARBITER_SRC` database; container `arbiter`; one REST table per endpoint; one flattening view per table (`arbiter.vendor_v`, `arbiter.contract_v`, …).
- `zetaris/sql/02_kev.sql`: `ARBITER_PUB` database, REST table `kev_raw` on the KEV GitHub URL, `CACHE TABLE`, view `arbiter.kev_vuln_v`.
- `zetaris/sql/03_usl.sql`: namespace, the single `COMPILE USL vendor_risk` statement (DDL below), one `ACTIVATE` per table, DQ rules from `dq_rules.yaml`, `RUN DQ`.
- Statement delimiter: blocks are separated by a line `-- @@stmt`. **Never split on `;`.**
- Endpoint placeholders `{URL:<raw_table>}` are substituted by `onboard.py` from `zetaris/sources.yaml`, which maps each REST table to:
  - its simulator path (`ZETARIS_SOURCE_MODE=simulator`, base `SOURCES_PUBLIC_BASE`);
  - its committed JSON file (`ZETARIS_SOURCE_MODE=github_raw`, base `https://raw.githubusercontent.com/<owner>/<repo>/main/data/sample/systems`). This is fallback B if containers cannot reach the host.
- `zetaris/onboard.py` (`python run.py zetaris onboard [--dry-run] [--skip-exists] [--only 01|02|03]`):
  - strips full-line `--` comments (except the `-- @@stmt` delimiter) before sending;
  - prints each statement first;
  - sends via the same REST client as the app;
  - stops on the first error unless it is "already exists" under `--skip-exists`;
  - writes `logs/zetaris-onboard-<ts>.jsonl`.

Example REST table and view (pattern copied from the verified PokéAPI recipe):

```sql
CREATE LIGHTNING DATABASE ARBITER_SRC DESCRIBE BY "Arbiter synthetic enterprise systems - simulator"
-- @@stmt
CREATE SCHEMASTORE CONTAINER arbiter
-- @@stmt
CREATE LIGHTNING REST TABLE clm_contracts_raw FROM ARBITER_SRC REQUEST(
    endpoint "{URL:clm_contracts_raw}",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER () BODY ()
-- @@stmt
CREATE SCHEMASTORE VIEW contract_v WITH CONTAINER arbiter AS
SELECT r.contract_id, r.supplier_ref, r.status, r.dpa_signed, r.dpa_signed_date,
       r.hosting_region_clause, r.transfer_mechanism,
       CAST(r.breach_notification_hours AS INT) AS breach_notification_hours,
       r.subprocessor_list_attached, r.renewal_date
FROM arbiter_src.clm_contracts_raw
LATERAL VIEW explode(records) AS r
```

KEV view:

```sql
CREATE SCHEMASTORE VIEW kev_vuln_v WITH CONTAINER arbiter AS
SELECT v.`cveID` AS cve_id, v.`vendorProject` AS vendor_project, v.product AS product,
       v.`vulnerabilityName` AS vulnerability_name, v.`dateAdded` AS date_added,
       v.`dueDate` AS due_date, v.`knownRansomwareCampaignUse` AS ransomware_use
FROM arbiter_pub.kev_raw
LATERAL VIEW explode(vulnerabilities) AS v
```

### 5.3 USL model `vendor_risk` (namespace `lightning.metastore.arbiter`; one COMPILE statement)

```sql
COMPILE USL IF NOT EXISTS vendor_risk DEPLOY NAMESPACE lightning.metastore.arbiter DDL
CREATE TABLE vendor (vendor_id varchar(12) NOT NULL PRIMARY KEY, legal_name varchar(200), trading_name varchar(200),
  category varchar(80), requested_service varchar(200), business_owner varchar(120), annual_spend_gbp decimal(14,2),
  criticality varchar(10), data_categories varchar(120), processing_countries varchar(120), clm_supplier_ref varchar(16),
  onboarding_status varchar(20), requested_at date);
CREATE TABLE vendor_alias (alias_id varchar(16) NOT NULL PRIMARY KEY, vendor_id varchar(12) FOREIGN KEY REFERENCES vendor(vendor_id), alias_lower varchar(200));
CREATE TABLE contract (contract_id varchar(16) NOT NULL PRIMARY KEY, supplier_ref varchar(16), status varchar(16), dpa_signed boolean,
  dpa_signed_date date, hosting_region_clause varchar(10), transfer_mechanism varchar(10), breach_notification_hours int,
  subprocessor_list_attached boolean, renewal_date date);
CREATE TABLE incident (incident_number varchar(16) NOT NULL PRIMARY KEY, opened_at date, vendor_name_raw varchar(200), severity varchar(4),
  category varchar(40), root_cause_tag varchar(40), status varchar(12), rca_completed boolean, closed_at date);
CREATE TABLE watchlist_entry (entry_id varchar(16) NOT NULL PRIMARY KEY, entity_name varchar(200), list_name varchar(60), country varchar(4), added_on date, reason varchar(200));
CREATE TABLE submission (submission_id varchar(16) NOT NULL PRIMARY KEY, vendor_id varchar(12) FOREIGN KEY REFERENCES vendor(vendor_id), submitted_at date, patch_sla_critical_days int, contact_role varchar(60));
CREATE TABLE submission_answer (answer_id varchar(20) NOT NULL PRIMARY KEY, submission_id varchar(16) FOREIGN KEY REFERENCES submission(submission_id), vendor_id varchar(12), question_id varchar(4), question varchar(300), answer_text varchar(4000));
CREATE TABLE submission_document (doc_id varchar(16) NOT NULL PRIMARY KEY, submission_id varchar(16) FOREIGN KEY REFERENCES submission(submission_id), vendor_id varchar(12), doc_type varchar(40), title varchar(200), issued_on date, expires_on date, text varchar(12000));
CREATE TABLE vendor_component (component_id varchar(16) NOT NULL PRIMARY KEY, vendor_id varchar(12) FOREIGN KEY REFERENCES vendor(vendor_id), vendor_project varchar(120), product varchar(200), version varchar(60));
CREATE TABLE kev_vuln (cve_id varchar(24) NOT NULL PRIMARY KEY, vendor_project varchar(200), product varchar(300), vulnerability_name varchar(400), date_added date, due_date date, ransomware_use varchar(16))
```

> **FK syntax (confirmed** in `open_data/usl/sql/02_sic_edgar_usl_create.sql` and commands guide §13.1): write foreign keys as `vendor_id varchar(12) FOREIGN KEY REFERENCES vendor(vendor_id)`, not bare `REFERENCES`. The DDL above already uses this form.
>
> **VERIFY on Day 1** against `docs/guides/zetaris-lightning-sql-commands.md`: accepted types (`boolean`, `decimal`, `int`) and maximum `varchar` length.
>
> Adjust the DDL, not the app. `ACTIVATE` statements cast to the declared types (`CAST(r.dpa_signed_date AS DATE)`) and wrap NOT NULL key columns in `COALESCE(…, '')` (commands guide §13.4).

**USL fallback.** If USL compile or activation fails after 90 minutes of effort, set `ZETARIS_QUERY_LAYER=views`. The registry resolves `{T.contract}` to `arbiter.contract_v`, with identical column names. Record the decision in the P1 report.

### 5.4 Data-quality rules (`zetaris/dq_rules.yaml`, single source for Zetaris and DuckDB)

| Rule | Table | Valid when (Spark SQL and DuckDB compatible) | Used by |
|---|---|---|---|
| `dq_contract_dpa_date` | contract | `dpa_signed = false OR dpa_signed_date IS NOT NULL` | EvaluatorAgent downgrades `dpa.signed` to UNKNOWN |
| `dq_contract_breach_hours` | contract | `breach_notification_hours IS NULL OR (breach_notification_hours >= 1 AND breach_notification_hours <= 720)` | Treat out-of-range as UNKNOWN |
| `dq_document_dates` | submission_document | `expires_on IS NULL OR expires_on >= issued_on` | Document not usable as assurance |
| `dq_incident_rca` | incident | `status <> 'closed' OR rca_completed IS NOT NULL` | Incident evidence quality |
| `dq_vendor_spend` | vendor | `annual_spend_gbp >= 0` | Tiering input sanity |

- **Live:** `SHOW DQ ALL INVALID TABLE lightning.metastore.arbiter.vendor_risk.<table>`, parse the JSON `records`, filter by vendor keys in Python.
- **Sample:** DuckDB runs `SELECT <pk> FROM <table> WHERE NOT COALESCE(<expr>, FALSE)` (plain `NOT (expr)` silently drops rows where the expression is NULL).
- `SHOW DQ ALL INVALID` also returns key-constraint failures; keep only rows for our rule names.
- The parity test checks that both report the same invalid keys.

## 6. Query registry (`app/data/queries.yaml`)

- SQL is the ANSI subset that runs on both backends: SELECT, JOIN, WHERE, `lower`, `trim`, `concat`, `LIKE`, `IN`, `COALESCE`, `CAST`.
- `{T.<table>}` placeholders resolve per backend and layer:
  - USL: `lightning.metastore.arbiter.vendor_risk.<table>`;
  - views: `arbiter.<table>_v`;
  - DuckDB: `<table>`.
- **Parameters are validated, then rendered as escaped literals.** Zetaris REST takes raw SQL, so binding must be safe:
  - `vendor_id` must match `^VND-\d{4}$`;
  - names are lowercased, trimmed, stripped of control characters and capped at 120 characters (quotes are escaped, not removed, so `o'brien ltd.` still matches `lower(trim(vendor_name_raw))`);
  - lists have at most 20 items;
  - single quotes are doubled.
  - Vendor free text never enters SQL.

| Query id | Params | Purpose (systems) | Controls |
|---|---|---|---|
| `Q_VENDOR_LIST` | – | Onboarding requests list (`vendor_id, legal_name, category, criticality, onboarding_status`) for the console's picker | – |
| `Q_VENDOR_PROFILE` | vendor_id | Vendor master (procurement) | tiering |
| `Q_VENDOR_ALIASES` | vendor_id | Alias list (procurement) | C06, C11 |
| `Q_VENDOR_CONTRACT` | vendor_id | `vendor JOIN contract ON clm_supplier_ref = supplier_ref` (procurement + CLM) | C07, C08, C09, C10 |
| `Q_VENDOR_INCIDENTS` | vendor_id, since | `incident JOIN vendor_alias ON lower(trim(vendor_name_raw)) = alias_lower` (ITSM + procurement) | C06 |
| `Q_WATCHLIST_SCREEN` | vendor_id | `watchlist_entry JOIN vendor_alias ON lower(trim(entity_name)) = alias_lower` (GRC + procurement) | C11 |
| `Q_SUBMISSION` | vendor_id | Submission header (trust portal) | C12 |
| `Q_VENDOR_COMPONENTS` | vendor_id | Declared software components (trust portal). Gives `vuln.components_declared`; when it is 0, `vuln.kev_matches = 0` and no KEV query runs | C12 |
| `Q_SUBMISSION_ANSWERS` | vendor_id, question_ids? | Answers (trust portal) | all |
| `Q_SUBMISSION_DOCUMENTS` | vendor_id, doc_types? | Documents (trust portal) | C05, C12 |
| `Q_COMPONENT_KEV` | vendor_id | **Federated internal + public join**: `vendor_component c JOIN kev_vuln k ON lower(k.vendor_project) = lower(c.vendor_project) AND lower(k.product) LIKE concat('%', lower(c.product), '%')` | C12 |
| `Q_KEV_BY_PRODUCTS` | products[] | KEV lookup for inline submissions | C12 |
| `Q_WATCHLIST_ALL` | – | Whole synthetic watchlist (small). Python screening for **near-matches** (difflib ratio ≥ 0.92 on identically normalised names, recorded only in `sanctions.near_matches`) for every case, and exact matches for inline submissions | C11 |
| `Q_INCIDENTS_BY_NAME` | names[], since | Inline submissions (`lower(trim(vendor_name_raw)) IN (…)`) | C06 |
| `Q_DQ_INVALID` | vendor_id | DQ invalid rows for the vendor (special handler) | C05, C07, C08 |

Each entry declares `columns` (an ordered list). The Zetaris adapter maps positional rows to these names if the response lacks headers. A contract test asserts that every query's DuckDB result has exactly these columns.

## 7. DuckDB mirror (`app/data/duckdb_backend.py`)

- On startup, create tables from `data/sample/systems/*.json` (`read_json_auto` on each `records` array) and the KEV snapshot, flattened identically to the Zetaris views.
- Mirror the USL column names and types exactly. Cast dates with `CAST(x AS DATE)`.
- In-memory; built once per process in under 2 s; the backend exposes only `run(query_id, params)` (no write path).

## 8. Verification (Zetaris discipline: count, compare, investigate)

`python run.py zetaris parity` writes `docs/passes/P1-B_parity.json` (committed evidence; `logs/` is gitignored):

1. **Source counts:** `SELECT COUNT(*)` per USL table versus the `count` field from the simulator endpoint for the 9 source tables (an independent check against the source API), and `kev_vuln` versus the live KEV `count`.
2. **Query parity:** for every registry query **except** `Q_COMPONENT_KEV` and `Q_KEV_BY_PRODUCTS` (live KEV is newer than the snapshot; step 3 covers them), run it on Zetaris and DuckDB for every vendor id and compare row counts and sha256 of sorted canonical rows.
3. **KEV:** the live catalogue is newer than the snapshot. Assert that every snapshot CVE that matches a catalogue product is present live (a subset check). Report new live CVEs separately.
4. **DQ:** the invalid key sets must be equal.

The P1-B gate is parity green, or every mismatch explained in `docs/passes/P1-B_REPORT.md`.

## 9. Day-1 live checks (run before writing the adapter)

1. From Cursor, open a clone of `zetaris/getting-started` and run its `scripts/preflight.py` (REST). Expect `SELECT 1` and `SHOW LIGHTNING DATABASES` to work.
2. Start the simulator. From **inside the Zetaris containers that fetch REST sources**, check reachability: `docker compose exec driver curl -s http://host.docker.internal:8100/health` and the same from `api` (the compose services are `postgres`, `driver`, `api`, `ui`, `ai-datasteward`; confirm with `docker compose ps`).
   - On Linux Docker Engine, add `extra_hosts: ["host.docker.internal:host-gateway"]` to the Zetaris compose override or run the simulator on the Zetaris network.
   - On Windows/WSL see `05_RUNBOOK.md` §3.
3. Capture one real `/sql-editor/sqls/run` response (scrubbed) into `tests/fixtures/zetaris_run_response.json`. Read the redoc at `http://localhost:8888/redoc/index.html` for column metadata fields. Build the normaliser against the fixture.
4. Register **one** REST table and view, query it, then script the rest.
