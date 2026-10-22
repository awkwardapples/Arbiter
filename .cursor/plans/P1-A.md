# P1-A plan — synthetic enterprise world, simulator, query registry, DuckDB mirror

## Goal

Deliver a complete **offline data plane** for Arbiter: a seeded generator that materialises 32 synthetic vendors across five fragmented REST-shaped systems plus a filtered CISA KEV snapshot, eval labels/splits/truth facts, and six demo inputs; a FastAPI simulator that serves committed JSON; a validated query registry with 15 ANSI-safe queries; an in-memory DuckDB backend mirroring the USL table/column model; inline submission routing; DQ rules shared with future Zetaris onboarding; and `FallbackBackend` behaviour ready for P1-B. Sample mode (`SAMPLE_MODE=true`) runs real registry SQL against DuckDB with no network. Labels and expected outcomes are derived **only** from `scenarios.yaml`, never from running the decision stack.

## Branch

`p1a-data` (per pass index).

## Ownership check

All paths below are in **P1-A** ownership (`docs/spec/passes/README.md` §3), except:

| Exception | Owner | P1-A action |
|---|---|---|
| `app/data/factory.py`, `app/data/status.py` | P1-A (P1-B may ✎ add Zetaris branch later) | Implement DuckDB-first factory; optional import of `ZetarisBackend` when P1-B lands — no edits to `app/data/zetaris.py` (P1-B stub stays) |
| `run.py` | P0 | **No edit** — wire commands only via owned `app/cli/data.py` |
| `docs/passes/P1-A_REPORT.md`, `docs/cursor-usage/P1-A.md` | This lane (reporting) | Written at end of build phase |

---

## Files to create or edit

### Data generator and committed outputs (`data/**`)

| File | Action |
|---|---|
| `data/README.md` | Create: synthetic disclaimer, sources/licences (KEV CC0), regenerate commands, approximate sizes |
| `data/generator/scenarios.yaml` | Create: 32 vendors `VND-0001`…`VND-0032`, scenario codes S01–S14, tier drivers, answer polarities, documents, contracts, incidents, watchlist, components, expected outcomes/reasons; 4 inline eval payloads; 6 input-example bindings per §A6 |
| `data/generator/phrasebank.yaml` | Create: ≥5 variants per polarity per question (01 §4.1), including negations and false friends |
| `data/generator/generate.py` | Create: CLI entry used by `generate-data`; deterministic `random.Random(seed)`; sorted iteration; `--as-of` on every envelope; KEV match assert (shared rule with registry); writes §A6 artifacts including `input_examples/expected.json` |
| `data/generator/kev_match.py` (or inline in generate) | Create: single KEV match implementation used by generator asserts and documented for SQL parity |
| `data/kev/fetch_kev.py` | Create: download from `KEV_URL`, filter catalogue products + 50 seeded extras; write snapshot + `SOURCE.md` |
| `data/sample/systems/*.json` | Create (9 files): flat envelopes per 01 §1.4 |
| `data/kev/kev_snapshot.json` | Create (via generator; one `--refresh-kev` run committed) |
| `data/evals/labels.jsonl` | Generated |
| `data/evals/splits.json` | Generated (stratified, sha256 fields) |
| `data/evals/truth_facts.jsonl` | Generated (never read by `app/`) |
| `data/evals/inline/*.json` | Create (4 files) |

### Enterprise simulator (`sources/**`)

| File | Action |
|---|---|
| `sources/simulator.py` | Create: FastAPI app, load JSON once, 01 §2 routes + `GET /public/kev-snapshot`, `GET /health`, `SIM_FAULTS` injection |

### Data layer (`app/data/`)

| File | Action |
|---|---|
| `app/data/queries.yaml` | Fill: 15 queries (01 §6), columns/systems/control_ids, `Q_DQ_INVALID` → `handler: dq_invalid` |
| `app/data/registry.py` | Implement: load YAML, param validation, safe literal rendering, `{T.<table>}` resolution, `render(...)`, `run` helper if useful |
| `app/data/duckdb_backend.py` | Implement: one-time in-memory build from sample JSON + KEV (<2 s); `run(query_id, params) -> QueryResult` |
| `app/data/dq.py` | Implement: load `zetaris/dq_rules.yaml`, `invalid_keys(backend, table) -> set[str]` |
| `app/data/inline.py` | Implement: `InlineBackend(submission, main_backend)` per §A5 |
| `app/data/backend.py` | Extend: `FallbackBackend(primary, secondary, tracer)` with pin-on-401 and trace `status=fallback` |
| `app/data/factory.py` | Implement: `get_backend(settings, tracer, submission=None)` — SAMPLE_MODE → DuckDB; else try Zetaris import or DuckDB + trace note; wrap inline |
| `app/data/status.py` | Implement: `check() -> dict` (table counts; delegate Zetaris if module usable) |
| `app/data/__init__.py` | Export public surface if needed (minimal) |

### Zetaris DQ rules (P1-A owns file; SQL onboarding is P1-B)

| File | Action |
|---|---|
| `zetaris/dq_rules.yaml` | Create: 01 §5.4 rules |

### Demo inputs

| File | Action |
|---|---|
| `input_examples/example_{1..6}.json` | Generated / aligned to §A6 |
| `input_examples/expected.json` | Generated from scenarios |

### CLI

| File | Action |
|---|---|
| `app/cli/data.py` | Replace stubs: `generate-data` (seed, as-of, refresh-kev), `sources` (uvicorn simulator) |

### Tests

| File | Action |
|---|---|
| `tests/unit/data/test_generator.py` | P1-T1, P1-T2, P1-T3, P1-T4, P1-T9, P1-T12 |
| `tests/unit/data/test_registry.py` | P1-T5, P1-T6, P1-T11 |
| `tests/unit/data/test_dq.py` | P1-T7 |
| `tests/unit/data/test_simulator.py` | P1-T8 |
| `tests/unit/data/test_inline_and_queries.py` | P1-T10, P1-T14 |
| `tests/unit/data/test_fallback.py` | P1-T13 |
| `tests/contract/test_registry_duckdb.py` | P1-T5 (contract: all queries × all vendors, column order) |
| `tests/conftest.py` | Extend: fixtures for DuckDB backend, sample data paths, tracer (no order dependence) |

### Gate

| File | Action |
|---|---|
| `scripts/gates/p1a.py` | Implement: committed `data/sample` present; total `data/` + `input_examples/` size < 2 MB; optional sanity (labels line count ≥ 32); exit non-zero otherwise |

---

## Interfaces (signatures)

Already in P0 (`app/data/backend.py`):

```python
class QueryResult(BaseModel): ...
class DataBackend(Protocol):
    name: str
    def run(self, query_id: str, params: dict[str, object]) -> QueryResult: ...
```

**`app/data/registry.py`**

```python
class QueryDef(BaseModel): ...  # id, sql | handler, params schema, columns, systems, control_ids

def load_registry(path: Path | None = None) -> dict[str, QueryDef]: ...
def validate_params(query_id: str, params: dict[str, object], registry: dict[str, QueryDef]) -> dict[str, object]: ...
def render(
    query_id: str,
    params: dict[str, object],
    *,
    backend: Literal["duckdb", "zetaris"],
    layer: Literal["usl", "views"] = "usl",
    registry: dict[str, QueryDef] | None = None,
) -> str: ...
def assert_ansi_subset(sql: str) -> None: ...  # P1-T11
```

**`app/data/duckdb_backend.py`**

```python
class DuckDBBackend:
    name: str = "duckdb"
    def __init__(self, *, sample_dir: Path | None = None, kev_path: Path | None = None) -> None: ...
    def run(self, query_id: str, params: dict[str, object]) -> QueryResult: ...
```

**`app/data/dq.py`**

```python
def load_dq_rules(path: Path | None = None) -> list[DqRule]: ...
def invalid_keys(backend: DataBackend, table: str, *, vendor_id: str | None = None) -> set[str]: ...
```

**`app/data/inline.py`**

```python
class InlineBackend:
    name: str = "inline"
    def __init__(self, submission: VendorSubmission, main: DataBackend, registry: ...) -> None: ...
    def run(self, query_id: str, params: dict[str, object]) -> QueryResult: ...
    @staticmethod
    def inline_vendor_ref(submission: VendorSubmission) -> str: ...  # SUB-<sha8>
```

**`app/data/backend.py`**

```python
class FallbackBackend:
    name: str = "fallback"
    def __init__(self, primary: DataBackend, secondary: DataBackend, tracer: Tracer) -> None: ...
    def run(self, query_id: str, params: dict[str, object]) -> QueryResult: ...
```

**`app/data/factory.py`**

```python
def get_backend(
    settings: Settings,
    tracer: Tracer,
    submission: VendorSubmission | None = None,
) -> DataBackend: ...
```

**`app/data/status.py`**

```python
def check(settings: Settings | None = None) -> dict[str, object]: ...
```

**`data/generator/generate.py`**

```python
def generate(*, seed: int, as_of: date, refresh_kev: bool = False) -> None: ...
def kev_matches(vuln: dict, component: dict) -> bool: ...  # shared rule
```

**`sources/simulator.py`**

```python
def create_app(*, systems_dir: Path | None = None) -> FastAPI: ...
def main() -> None: ...  # uvicorn entry for CLI
```

**Registry special handler**

- `Q_DQ_INVALID`: Python handler aggregating DQ invalid rows for a vendor (not raw SQL string in YAML).

---

## Acceptance tests (`@pytest.mark.p1a`)

| Id | How we test |
|---|---|
| **P1-T1** | Run `generate` twice same seed/as-of; sha256 each output file under `data/sample`, `data/evals`, `input_examples/expected.json`; differ on seed for non-fixed vendor names |
| **P1-T2** | Parse all `data/sample/systems/*.json`; assert envelope keys; every record value scalar; `count == len(records)` |
| **P1-T3** | Grep/scan served JSON records (and simulator responses) for `S0[0-9]+`, uppercase outcome tokens, `expected`, `label` |
| **P1-T4** | Load `scenarios.yaml`; for each vendor assert planted evidence (KEV counts S09 vs non-S09, S06 region mismatch, S10 watchlist alias, S13 DPA date null, etc.) using shared KEV matcher |
| **P1-T5** | Contract: `DuckDBBackend` + registry — every query × every `VND-####`; assert `result.columns == declared columns` in order; non-empty where scenarios expect rows |
| **P1-T6** | `validate_params` / `render` rejects SQL injection vendor id, 21-item list, bad dates; name with `'` renders doubled quotes; rendered SQL has no unescaped single quotes in literals |
| **P1-T7** | `invalid_keys` on contract table includes VND-0028 primary key; clean vendors no false positives for `dq_contract_dpa_date` |
| **P1-T8** | FastAPI `TestClient` on `create_app()`; each route matches file JSON; `/health` counts; env `SIM_FAULTS=itsm:500x2` → two 500s then success |
| **P1-T9** | Parse `splits.json`; stratification rule; recompute sha256 of sorted case lists matches file |
| **P1-T10** | Each `input_examples/example_*.json` validates as `RunRequest`; `expected.json` has all six; `InlineBackend.inline_vendor_ref` for example_6 submission shape |
| **P1-T11** | Static scan of all registry SQL strings against allowed ANSI subset (01 §6); fail on backend-specific functions |
| **P1-T12** | Parse `kev_snapshot.json`; required top-level and entry keys; `count == len(vulnerabilities)` |
| **P1-T13** | Fake primary raising `UpstreamTimeout` once → secondary used, `fallback_from` set, one trace event `status=fallback`; `Unauthorized` pins secondary for subsequent calls |
| **P1-T14** | `Q_VENDOR_COMPONENTS` full set for a vendor with components; empty vendor 0 rows; `Q_WATCHLIST_ALL` full list; Python screen: S10 exact match + planted near-match (ratio ≥ 0.92), no false exact on clean vendors |

Tests first → commit `test(p1a): acceptance tests` → implement until green.

---

## Implementation order (build phase, after approval)

1. **Generator core**: `scenarios.yaml` + `phrasebank.yaml` + `kev_match` + `generate.py` (offline path without network).
2. **One KEV refresh** (human/network): commit snapshot + `SOURCE.md`.
3. **Registry + DuckDB**: `queries.yaml`, `registry.py`, `duckdb_backend.py`, `dq.py`.
4. **Inline + factory + status + fallback**.
5. **Simulator** + CLI wiring.
6. **Tests** (already written) green; **gate** `p1a.py`.
7. **Report** + cursor usage doc.

---

## Risks and questions for Josh

1. **KEV snapshot commit** — First build needs one `python run.py generate-data --refresh-kev ...` with network to pin a real catalogue version. OK to run that during build and commit the result (with `SOURCE.md` attribution)?
2. **VND-0007 (S06+S09, T1)** — Combined scenario is the hardest authoring case (contradiction + KEV + T1 corroboration). Confirm we keep the spec’s fixed demo mapping for `example_2.json` → ESCALATE even if tier arithmetic alone would suggest a different narrative emphasis.
3. **Data size budget (< 2 MB)** — KEV subset + 32 vendors may approach the cap. Plan is aggressive filtering (catalogue products + 50 extras only) and concise document text. Flag in report if we trim phrase variety instead.
4. **Near-match watchlist decoy (S10 screening)** — §A10 lists near-match as a cut line; tests P1-T14 require it. **Recommendation:** keep it (low code cost, demo value). Confirm or cut?
5. **`FallbackBackend` primary** — P1-T13 needs a real primary backend; use a tiny fake `DataBackend` in tests, and in factory use DuckDB-as-primary in sample mode until P1-B provides Zetaris. No objection?
6. **Regression scope** — `verify-pass` runs all non-live tests after P1-A markers. Any known flaky environment constraints (DuckDB on WSL) to watch for?

---

## Verification (target)

```bash
python run.py generate-data --refresh-kev --seed 2026 --as-of 2026-10-26   # once, network
python run.py generate-data --seed 2026 --as-of 2026-10-26                 # offline, idempotent
python scripts/tasks.py verify-pass --pass 1a
```

---

## Status

**Plan phase complete.** `.cursor/ACTIVE_PASS` is `1a plan`. Awaiting human approval before setting `1a build` and coding.
