# P1-A report — synthetic data plane

## Built

- **Generator:** `data/generator/{scenarios.yaml, phrasebank.yaml, generate.py}` with KEV assert (`kev_match.py`) and `data/kev/fetch_kev.py` (CC0 snapshot + `SOURCE.md`).
- **Committed sample:** nine system JSON envelopes under `data/sample/systems/`, `data/kev/kev_snapshot.json`, eval artifacts (`labels.jsonl`, `splits.json`, `truth_facts.jsonl`, `inline/*`), `input_examples/*` + `expected.json` (~361 KB total).
- **Simulator:** `sources/simulator.py` (FastAPI :8100, `SIM_FAULTS`).
- **Data layer:** `queries.yaml` (15 queries), `registry.py`, `duckdb_backend.py`, `dq.py`, `inline.py`, `factory.py`, `status.py`, `FallbackBackend` in `backend.py`.
- **DQ:** `zetaris/dq_rules.yaml` (shared rules).
- **CLI:** `python run.py generate-data`, `python run.py sources`.
- **Tests:** P1-T1…P1-T14 (`@pytest.mark.p1a`) + contract test; gate `scripts/gates/p1a.py`.

## Deviations

- **`labels.jsonl` tier field:** computed with a simplified rule (T1 only for S03 / S06+S09). Full policy tiering (02 §2) will be applied when P2-C merges; scenario/outcome fields match `scenarios.yaml`.
- **`truth_facts.jsonl`:** minimal stub (category fact only); P3 label oracle may extend planting.
- **Deterministic `generated_at`:** envelope timestamp is `{as_of}T12:00:00Z`, not wall clock, so regen is byte-idempotent (P1-T1).

## Known gaps

- `ZetarisBackend` remains P1-B; live mode uses DuckDB with a trace note until P1-B lands.
- Optional queries `Q_SUBMISSION_ANSWERS` / `Q_SUBMISSION_DOCUMENTS` do not filter optional `question_ids` / `doc_types` yet (no params declared).

## Commands run

```bash
python run.py generate-data --refresh-kev --seed 2026 --as-of 2026-10-26
python run.py generate-data --seed 2026 --as-of 2026-10-26
python scripts/tasks.py verify-pass --pass 1a
```

## Demo vendor query smoke (DuckDB)

| vendor_id | legal_name (profile) | components | KEV rows (Q_COMPONENT_KEV) |
|---|---|---:|---:|
| VND-0003 | Pellucid Forms Ltd | 0 | 0 |
| VND-0007 | Quillfeather Payroll Cloud Ltd | 1 | 15 |
| VND-0019 | Corvid Ledger Services Ltd | 0 | 0 |
| VND-0028 | Kestrel Docs Ltd | 0 | 0 (DQ invalid DPA date) |

## Vendor index (from `labels.jsonl`)

See `data/evals/labels.jsonl` for all 32 vendors: each line lists `case_ref`, `scenario`, `expected_outcome`, and `expected_reasons` derived from `data/generator/scenarios.yaml` only.

## Explain it

1. **ITSM → vendor:** `Q_VENDOR_INCIDENTS` joins `lower(trim(vendor_name_raw))` to `vendor_alias.alias_lower` (e.g. Quillfeather’s legal name uppercased in ITSM matches alias rows).
2. **Flat records:** Zetaris REST + `explode(records)` expects scalar columns; lists are comma-joined strings in JSON.
3. **SQL injection:** Registry validates `vendor_id`/`names`/dates, then renders **literal** SQL (doubled quotes); free text never concatenates unescaped.
4. **Judge inline submission:** `InlineBackend` serves profile/answers/docs/components from the POST body; KEV/watchlist/incidents delegate to DuckDB via `Q_KEV_BY_PRODUCTS`, `Q_WATCHLIST_ALL`, `Q_INCIDENTS_BY_NAME`.
5. **Generator asserts:** After building components, `_assert_scenarios` checks KEV counts and scenario-specific plants before writing labels—wrong evidence fails the generator, not silent eval drift.
