# P2-A plan: Meterless H-MEM, Python port (conformance 13/13)

## Goal

Replace the P0 stubs in `app/memory/hmem/` with a faithful, dependency-free Python port of the Meterless H-MEM reference engine (`~/meterless/engines/hmem/reference/src`, commit `1742dec56a66e58eef9dda2d2b865823758ca8cd`, 1,147 lines of TS across 10 files). Behaviour is preserved module by module: same ids (`mem-N`), same enrichment, same hybrid ranking formula, same feedback deltas, same ledger entries, same sleep guardrails, same dream approval boundary, same conflict gate. JS-only semantics (FNV-1a `Math.imul`, `toFixed`, default `Array.sort`, JS `\s`/`trim`, ASCII `\b`, ASCII `\d`) live in one place, `jsfmt.py`. `tests/conformance/test_hmem_conformance.py` is a 1:1 port of `conformance/runner.ts` over a byte-identical copy of `vectors.json` and prints `H-MEM conformance: 13/13 PASS`. Additive only: optional `agentId`/`runId`/`taskId` on records, and an optional append-only ledger mirror (`logs/hmem-ledger.jsonl`). P4-A's precedent adapter will sit on top of this facade; nothing here knows about vendors or precedents.

Branch: `p2a-hmem` (already checked out in this worktree).

## Files (all inside P2-A ownership, README §3)

| File | Action | Port of |
|---|---|---|
| `app/memory/hmem/jsfmt.py` | fill stub | – (JS-semantics helpers) |
| `app/memory/hmem/types.py` | fill stub | `types.ts` |
| `app/memory/hmem/embeddings.py` | fill stub | `embeddings.ts` |
| `app/memory/hmem/ledger.py` | fill stub | `trustLedger.ts` (+ optional mirror) |
| `app/memory/hmem/store.py` | fill stub | `memoryStore.ts` |
| `app/memory/hmem/mining.py` | fill stub | `memoryMining.ts` |
| `app/memory/hmem/retrieval.py` | fill stub | `memoryRetrieval.ts` |
| `app/memory/hmem/conflicts.py` | fill stub | `conflictDetection.ts` |
| `app/memory/hmem/sleep.py` | fill stub | `sleepCycle.ts` |
| `app/memory/hmem/dreaming.py` | fill stub | `dreaming.ts` |
| `app/memory/hmem/__init__.py` | fill stub | `index.ts` (`HMEM` facade + re-exports) |
| `vendor/meterless/hmem_vectors.json` | create | byte-identical copy (sha256 `10afb5a0…7029`) |
| `vendor/meterless/LICENSE` | create | Apache-2.0 text copied from `engines/hmem/LICENSE` (sha256 `63e29fc8…a0ef`) |
| `vendor/meterless/NOTICE.md` | create | repo URL, commit sha, copied files + sha256, licence, "ported to Python by Arbiter", camelCase → snake_case mapping table |
| `scripts/dev/hmem_golden.py` | create | Node golden check for `embed()` (50 strings, 1e-12) |
| `scripts/gates/p2a.py` | fill stub | gate (below) |
| `tests/conformance/test_hmem_conformance.py` | create | `runner.ts` |
| `tests/unit/hmem/__init__.py` | create | – |
| `tests/unit/hmem/test_embeddings.py`, `test_jsfmt.py`, `test_persistence.py`, `test_agent_fields.py`, `test_ledger_mirror.py` | create | P2-T2…T6 |
| `docs/passes/P2-A_REPORT.md`, `docs/cursor-usage/P2-A.md` | create at the end | – |

**Ownership flag (one):** `tests/conformance/__init__.py`. `tests/` and `tests/unit/` are packages, so the new `tests/conformance/` directory needs an empty `__init__.py`, which is not literally matched by `tests/conformance/test_hmem_*.py`. P2-D will need the same empty file for `test_scout_*.py`; identical empty adds merge cleanly in git. I propose to create it. No other file outside ownership is touched (no `app/schemas/*`, `app/errors.py`, `app/config.py`, `requirements*.txt` edits; no new dependencies).

## Module mapping and interfaces

Records and ledger entries are **pydantic v2 models** with snake_case attributes and camelCase aliases (`populate_by_name=True`, serialised `by_alias=True, exclude_none=True` so JS `undefined` fields are dropped). They are **mutable and shared by reference** (the runner sets `byKey[k].supersededBy` directly on the object `add()` returned, and the store must see it), so `validate_assignment` stays off.

```python
# jsfmt.py
JS_WHITESPACE: str                       # exact ECMAScript WhiteSpace + LineTerminator set
JS_WS_CLASS: str                         # regex char class built from it, used instead of \s
def imul32(a: int, b: int) -> int        # (a * b) & 0xFFFFFFFF
def to_fixed(x: float, digits: int) -> float     # Decimal(x).quantize(ROUND_HALF_UP), sign-aware; never round()
def js_trim(s: str) -> str
def js_default_sort_key(s: str) -> bytes # UTF-16 code-unit order (s.encode("utf-16-be"))
def js_array_string(value: object) -> str        # String([k, v]) for the entries().sort() case
def assert_ascii_id(s: str) -> str       # localeCompare on ids → plain compare, guarded

# types.py
MemoryType = Literal["personal", "factual", "preference", "general"]
MemoryLayer = Literal["short_term", "working", "long_term"]
ProvenanceOrigin, LedgerAction (17), MiningEventType (7), DreamProposalType, FeedbackKind = Literal[...]
class Provenance(BaseModel): origin; learned_at (learnedAt); label; refs: list[str] | None
class MemoryRecord(BaseModel): id, content, type, layer, timestamp, last_accessed, access_count, tags,
    embedding, score?, confidence, source, provenance, chat_id?, mission_id?, goal_run_id?,
    domain, namespace, entities, related_to, supersedes?, superseded_by?, derived_from?,
    agent_id?, run_id?, task_id?          # last three additive (P2-T5)
class LedgerEntry(BaseModel): memory_id, action, actor, timestamp, previous_state?, new_state?, details?
class DreamProposal, SleepPreview, SleepReport, ConflictRecord, RetrievedMemory, QueryTrace, QueryResult
FEEDBACK_DELTAS = {"helpful": 0.05, "not_helpful": -0.03, "wrong": -0.2}
DEFAULTS: Final  (frozen dataclass; same 13 constants); DAY_MS; def clamp01(x: float) -> float
def now_ms() -> int

# embeddings.py
DIM = 64
def tokenize(text: str) -> list[str]
def fnv1a(s: str) -> int                 # over UTF-16 code units
def embed(text: str) -> list[float]
def cosine(a: list[float], b: list[float]) -> float
def jaccard(a: Iterable[str], b: Iterable[str]) -> float

# ledger.py
class TrustLedgerService:
    def __init__(self, clock, persist_dir: str | Path | None = None, mirror_path: str | Path | None = None)
    def log(self, memory_id, action, actor, *, previous_state=None, new_state=None, details=None) -> LedgerEntry
    def history(self, memory_id) -> list[LedgerEntry]
    def all(self) -> tuple[LedgerEntry, ...]
    def stats(self) -> dict[str, int]

# store.py
class MemoryStoreService:
    def __init__(self, clock, ledger, actor: str, persist_dir=None)
    def persist(self) -> None
    def add(self, content: str, *, source: str | None, type=None, layer=None, tags=None, confidence=None,
            provenance=None, chat_id=None, mission_id=None, goal_run_id=None, supersedes=None,
            derived_from=None, agent_id=None, run_id=None, task_id=None) -> MemoryRecord
    def get(self, id) -> MemoryRecord | None
    def all(self) -> list[MemoryRecord]
    def update(self, id, **patch) -> MemoryRecord
    def delete(self, id, reason: str) -> None
    def touch(self, id) -> None
    def promote(self, id, layer) -> None
    def restore_all(self, records, seq) -> None
    def snapshot_all(self) -> tuple[list[MemoryRecord], int]
    def classify_domain(self, content, tags, type) -> str
    def extract_entities(self, content) -> list[str]
def snapshot(r: MemoryRecord) -> dict[str, Any]       # camelCase dict, embedding dropped

# mining.py
class MemoryMiningService:
    def __init__(self, store, clock, miner_fn: Callable[[str], str | Awaitable[str]] | None = None)
    def mine_interaction(self, event, text, *, chat_id=None, layer=None) -> list[MemoryRecord]
    async def amine_interaction(...) -> list[MemoryRecord]   # same, awaits an async miner_fn
    def mine_document(self, file_name, text) -> list[MemoryRecord]  (+ amine_document)
    def mine_model_free(self, text) -> list[str]
def parse_strict_json_array(raw: str) -> list[str]

# retrieval.py
class MemoryRetrievalService:
    def score_one(self, memory, query) -> float
    def query(self, query, *, top_n=None, threshold=None, chat_id=None) -> QueryResult
    def format_reinjection(self, items) -> str
    def feedback(self, memory_id, kind: FeedbackKind) -> None

# conflicts.py
class ConflictDetectionService:
    def scan(self) -> list[ConflictRecord]
    def auto_resolve(self, conflict) -> Literal["resolved", "queued"]
    def queue(self) -> list[ConflictRecord]

# sleep.py
class SleepCycleService:
    def preview(self) -> SleepPreview
    def execute(self, preview: SleepPreview | None = None) -> SleepReport
    def restore(self, backup_id: str) -> None

# dreaming.py
class DreamingService:
    def dream(self) -> list[DreamProposal]
    def pending(self) -> list[DreamProposal]
    def approve(self, proposal_id) -> MemoryRecord | None
    def reject(self, proposal_id) -> None

# __init__.py
class HMEM:
    def __init__(self, clock: Callable[[], int] = now_ms, actor: str = "system",
                 persist_dir: str | Path | None = None, miner_fn=None,
                 ledger_mirror: str | Path | None = None)   # ledger_mirror is additive, default off
    store, ledger, mining, retrieval, conflicts, sleep, dreaming, clock
    def add(self, content, *, source, **kw) -> MemoryRecord
    def mine(self, event, text, *, chat_id=None) -> list[MemoryRecord]
    async def amine(...)
    def query(self, q, top_n=5, threshold=0.35, chat_id=None) -> QueryResult
    def feedback(self, memory_id, kind) -> None
```

Errors: missing/blank `source` raises `app.errors.ValidationFailed`; unknown memory, proposal or backup id raises `app.errors.NotFound` (reference throws a plain `Error`; the runner only checks "throws"). No `print` in `app/`; diagnostics via `logging`.

### JS semantics applied (spec §A4 rules 1–9, plus four I found while reading the source)

1. FNV-1a over UTF-16 code units with `imul32`; vectors `""→0x811c9dc5`, `"a"→0xe40c292c`, `"foobar"→0xbf9cf968`.
2. `to_fixed` for `trace.scores` (`toFixed(4)`) and `decisionConfidence` (`toFixed(3)`).
3. `localeCompare` on ids → plain compare after `assert_ascii_id` (ids are always `mem-N`).
4. `[...byDomain.entries()].sort()` sorts by `String([k, v])` = `k + "," + "[object Object],…"`, compared by UTF-16 code units. Sorting by key alone differs when one domain is a prefix of another followed by a char below `,` (e.g. `work` vs `work+x`, both reachable via `project:` tags), so I reproduce the full string key rather than the spec's `str(kv[0])` shorthand. Noted as a refinement, not a deviation.
5. Dict insertion order = `Map` order; `[...new Set(x)]` → `list(dict.fromkeys(x))`.
6. Float arithmetic in the same evaluation order as the TS (so `reduce` sums match bit for bit); integer ms timestamps.
7. Tokeniser: after `.lower()`, `[^a-z0-9\s]` → space then split on `\s+` is equivalent to `re.findall("[a-z0-9]+")` for any `\s` definition, so the tokeniser is exact without depending on the whitespace class. The JS whitespace class is still needed for mining's `split(/(?<=[.!?])\s+|\n+/)`, `.trim()` (`js_trim`) and `parseStrictJsonArray`'s `\s*`.
8. `\b` regexes (entities, `CORRECTION`, `SIGNAL`, opposing pairs) compiled with `re.ASCII`; `/i` flags become `re.I | re.ASCII`, which also blocks Python-only matches like the Kelvin sign `K`→`k`. Opposing pair `/\bavoid[s]?|dislike[s]?\b/i` ported verbatim, precedence quirk included.
9. Numeric extraction `/\d+(\.\d+)?/g` uses ASCII `\d` (`re.ASCII`); `numsA.join()` → `",".join(...)`.
10. Persistence: lossless round-trip, not byte-identical; loads JS-written `state.json` (e.g. `"confidence": 1`). Also loads `<persist_dir>/ledger.jsonl` on start, as the reference does.

## Acceptance tests (marker `p2a`)

| Id | File | How |
|---|---|---|
| **P2-T1** | `tests/conformance/test_hmem_conformance.py` | Load `vendor/meterless/hmem_vectors.json`; one pytest param per vector with `ids=` the vector id (`rv-001` …), grouped by section exactly as `runner.ts`, same assertions and messages, `approx` eps 1e-9. Plus a count assertion that the sections are 2/5/2/1/1/1/1 = 13. `teardown_module` prints the runner's scorecard and `H-MEM conformance: 13/13 PASS` (visible with `-s`). |
| **P2-T2** | `tests/unit/hmem/test_embeddings.py` | FNV-1a known vectors; `embed` is unit length or all-zero (empty / single-char input); same input → identical vector; `tokenize` edge cases (punctuation, non-ASCII, `\ufeff`, `\x1c`). Golden: if `node` is on PATH and the Meterless clone is found (`METERLESS_DIR`, default `~/meterless`), run `scripts/dev/hmem_golden.py` (writes a temp `.ts` importing the reference `embed`, runs `npx tsx`) over 50 fixed strings and compare to 1e-12; otherwise `pytest.skip` with the reason. |
| **P2-T3** | `tests/unit/hmem/test_jsfmt.py` | `to_fixed(1.005, 2) == 1.0` (JS `"1.00"`), `to_fixed(2.5, 0) == 3`, `to_fixed(-2.5, 0) == -3`, `to_fixed(0.0005, 3) == 0.001`, plus `1.45→1.4`/`1.55→1.6` at 1 dp (exact-binary cases) and `-0.0` handling; `js_trim` vs a JS-whitespace table; `js_default_sort_key` ordering incl. the `work`/`work+x` case. |
| **P2-T4** | `tests/unit/hmem/test_persistence.py` | `tmp_path` persist dir with a fixed clock: add several records (incl. one with `supersedes`/`derived_from`), query, feedback each kind; reload `HMEM(persist_dir=…)`; assert `store.all()` dumps equal by id, `seq` continues (`mem-N+1`), same query results and scores, ledger history equal. Also load a hand-written JS-style `state.json` (ints for floats, missing optional fields) and re-persist losslessly. |
| **P2-T5** | `tests/unit/hmem/test_agent_fields.py` | `add(..., agent_id, run_id, task_id)` → attributes set; JSON uses `agentId/runId/taskId`; survives persist/reload; appears in the ledger `newState` snapshot. Re-run every conformance vector with agent fields injected on each `add` and assert the identical pass/fail set and identical query order/scores. |
| **P2-T6** | `tests/unit/hmem/test_ledger_mirror.py` | `HMEM(ledger_mirror=tmp/"hmem-ledger.jsonl")`: N ledger entries → N JSONL lines, each parses back as `LedgerEntry` and equals the in-memory entry; a second instance on the same mirror appends (line count = first + second, first lines byte-identical); mirror off by default (conformance writes nothing to `logs/`). |

All test modules carry `pytestmark = pytest.mark.p2a`.

## Gate (`scripts/gates/p2a.py`)

Returns non-zero unless: `vendor/meterless/{hmem_vectors.json,LICENSE,NOTICE.md}` exist; the vectors' sha256 matches the value recorded in `NOTICE.md`; `NOTICE.md` names the source repo, commit sha and Apache-2.0; and running the 13 vectors through the same case functions as the conformance test yields 13/13.

## Build sequence (after approval)

1. `.cursor/ACTIVE_PASS` → `2a build`.
2. Copy vendor files + NOTICE; write all P2-A tests → commit `test(p2a): acceptance tests`; confirm they fail on the stubs (ImportError/AttributeError, not collection errors from typos).
3. `feat(p2a): …` commits in dependency order: jsfmt+types+embeddings → ledger+store → retrieval → mining → conflicts+sleep+dreaming → facade+mirror → gate + golden script.
4. `python scripts/tasks.py verify-pass --pass 2a` green; `pytest tests/conformance/test_hmem_conformance.py -q -s` for the scorecard.
5. Report + cursor-usage; push `p2a-hmem`; delete `.cursor/ACTIVE_PASS`; stop.

## Risks and questions for you

1. **Node is not installed inside WSL** (only a Windows `npx` on `/mnt/c`, and `node` itself isn't found). The P2-T2 golden comparison against the TS reference will therefore **skip** here. Options: (a) leave it skipping and rely on the FNV-1a vectors + determinism tests (my recommendation for now; it's optional per the spec); (b) you install Node in WSL (`nvm install --lts`), and I run the golden check once and paste its output in the report. Either way the conformance suite itself is pure Python and doesn't need Node.
2. **`tests/conformance/__init__.py`**: OK to create it (see ownership flag)?
3. **`ledger_mirror` constructor argument**: the spec lists the facade signature without it; I'm adding it as an optional keyword (default off) so tests and conformance never write into `logs/`. P4-A would pass `ledger_mirror="logs/hmem-ledger.jsonl"` and `persist_dir="var/hmem"`. OK?
4. **`Math.exp` vs glibc `exp`** may differ in the last ulp for the recency term. Conformance asserts order and 1e-9 only, so this can't flip a vector, but it's why I won't claim bit-identical scores against the TS reference.
5. **Async miner**: sync `mine()` plus async `amine()`. If `miner_fn` returns a coroutine, `mine()` raises a clear error telling the caller to use `amine()` rather than spinning up a hidden event loop. OK?

---

**Waiting for approval.** Reply "approved" (with answers to 1–3 if you disagree with my recommendations) and I'll switch to build.
