# P0: Bootstrap (skeleton, contracts, tooling, guard-rails)

## 1. Goal

By the end of P0 the repository has:

- every shared file and a stub for every module in master spec §9;
- the binding pydantic contracts;
- configuration, tracing and canonical hashing;
- a FastAPI app with `/health`;
- a cross-platform task runner;
- the three integrity scripts (secrets, traces, hardcoding);
- CI.

After P0, parallel lanes only **fill** files they own.

## 2. Why it scores

- **Technical (20):** typed contracts, CI and reliability scaffolding.
- **Integrity:** secrets and hardcode checks from the first commit, which reduces disqualification risk.
- **Sponsor Tech (Cursor):** the rules, plans and hooks are visibly in use from the start.

## 3. Read first

- `AGENTS.md`
- Master spec §§5.2, 7, 8.9, 9, 10, 11, 14
- `docs/spec/passes/README.md` §3 (ownership)

## 4. Depends on

The spec-pack import commit only.

## 5. Deliverables

| File | Responsibility |
|---|---|
| `pyproject.toml` | Project metadata. Ruff config (line length 110, rules `E,F,I,B,UP,SIM`, `extend-exclude = [".cursor"]`: the pre-existing hook scripts are editor tooling, not project code). Pytest config: `testpaths=["tests"]`; markers `p0 p1a p1b p2a p2b p2c p2d p3 p4a p4b p5a p5b p6 p7 live slow`; `-m "not live"` by default via `addopts` |
| `requirements.txt` | **Every runtime dependency for the whole project, pinned to exact versions resolved today:** `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `httpx`, `tenacity`, `duckdb`, `pyyaml`, `streamlit`, `python-dotenv`. No others without asking |
| `requirements-dev.txt` | `pytest`, `pytest-cov`, `ruff`, `respx`, `hypothesis`, pinned |
| `run.py` | Dispatcher. Commands and owning modules are master spec §8.11 (the table is authoritative). `argparse` with subcommands collected from `app/cli/*.py`, where each module exposes `register(subparsers)`. With no arguments it runs `serve`. Starts uvicorn on `0.0.0.0:$PORT` |
| `app/cli/__init__.py`, `app/cli/meta.py` | `serve`, `ui`, `preflight`. `preflight` calls `app.llm.status.check()` and `app.data.status.check()` if importable, otherwise prints "not yet implemented". It prints a table with no secrets |
| `app/cli/{data,zetaris,llm,guard,run_case,review,audit,eval,examples}.py` | Stubs: each has `register()` adding exactly the subcommands master spec §8.11 assigns to it, which print `not implemented yet (lane X)` and exit 3. **CLI modules only parse arguments and delegate** to `app/…`, `eval/`, `scripts/` or `data/generator/`; they hold no decision logic |
| `app/config.py` | `Settings(BaseSettings)` with every variable in master spec §10 except the last block (console, simulator and test variables, which `ui/`, `sources/` and `tests/` read themselves). Secrets are `SecretStr \| None`, **default `None`**; a value matching the placeholder allowlist (`your-…`, `generate-…`, `<…>`, `***`, `changeme`, `example`, `placeholder`) or an empty string is treated as unset (master spec §10). `redacted_dict()`. Organiser aliases (`MODEL_BASE_URL`, `MODEL_API_KEY`, `NEMOTRON_MODEL`) are read-only fallbacks for the NVIDIA provider. `mode()` returns `{"data": "zetaris"\|"duckdb", "llm": "<resolved or 'auto'>"}`. `mask_secrets(text) -> str` replaces any configured secret value, and any pattern from `scan_secrets`, with `***` |
| `app/errors.py` | `ArbiterError(type, message, recoverable)` and subclasses: `ConfigError`, `UpstreamTimeout`, `UpstreamError`, `Unauthorized`, `OfflineProvider`, `ParseFailure`, `GuardBlocked`, `PolicyError`, `PolicyIneligible`, `ContractInvalid`, `BudgetExceeded`, `NotFound`, `ValidationFailed`. HTTP mapping: `ValidationFailed` 400, `Unauthorized` 401, role refusal 403, `NotFound` 404, expired or illegal contract state 409, `PolicyIneligible` 422, `NotImplemented` 501, anything else 500 |
| `app/canon.py` | `canonical_json(obj) -> str` (sorted keys, compact separators, datetimes as ISO-8601 UTC `Z`, pydantic models via `model_dump(mode="json")`). `sha256_hex(obj) -> str` |
| `app/tracing.py` | `Tracer(run_id, *, mode, log_dir="logs")` with `.event(agent_name, action, *, input_summary, output_summary, status="success", target_agent=None, confidence=None, retry_count=0, parent_span_id=None, **extras) -> TraceEvent` and `.span(...)` (context manager setting the parent span). Writes one JSON line per event to `logs/trace-<run_id>.jsonl`, plus a readable stdout line (`[INFO] run_id=… Agent → Target: output_summary (status)`) via `logging`. All text goes through `mask_secrets`. `.close()` flushes. Thread-safe |
| `app/schemas/{common,case,evidence,decision,report,contract,trace,api,facts}.py` | Every model in master spec §7 with **verbatim field names** (including `PolicyInputs`, `PrecedentCandidate`, `PrecedentRef`, `DQFlag`, `Draft` defined there), plus: `TierProfile {data_categories, criticality, annual_spend_gbp, contract_status}`, `GuardFlag {kind, score, level, segment_id}`, `GuardResult`, `CitedSentence {text, citations[]}`, `ContractRisk`, `ToolStep`, `ContractScope`, `Answer`, `Document`, `Component`, `RunRequest` (accepts a bare `CaseInput` **or** `{input: CaseInput, options: {sample_mode?: bool}}`, the organisers' shape), `RunResponse`, `ErrorResponse`, `ReviewRequest`, `ApprovalRequest`, `PolicyInputs`. `ControlResult` includes `conditional: bool = False` and `condition_text: str \| None` (02 §1). `facts.py` holds the `FACT_KEYS: frozenset[str]` listed in §6 |
| `app/llm/generator.py` | **Interface stub** with the final signature (master spec §8.2) that always raises `OfflineProvider`, plus `GenerationResult`. P2-B replaces the body |
| `app/data/backend.py` | **Interface stub**: `DataBackend` Protocol, `QueryResult`. P1-A fills it |
| `app/api/main.py` | FastAPI app. Includes routers from `routes_run`, `routes_cases`, `routes_contracts`, `routes_review` and `routes_meta` (P0 creates each as an empty `APIRouter`, except `routes_meta`, which has `GET /health`). Exception handlers map `ArbiterError` to `ErrorResponse` with the right HTTP code, `RequestValidationError` to 400 `ValidationFailed`, and anything else to 500 `InternalError` with no stack trace in the body. `POST /run` returns 501 `NotImplemented` until P3 |
| `app/api/routes_*.py` | Stubs as above |
| Other module stubs | Empty modules with a docstring naming the owning lane, for every path in master spec §9 under `app/`, `ui/`, `eval/` and `sources/`. This lets imports resolve and keeps ownership visible |
| `scripts/tasks.py` | Subcommands: `setup` (pip install both requirement files into the *current* interpreter; the README and AGENTS.md tell the human to create and activate `.venv` first, and the stop hook prefers `.venv`'s interpreter), `lint` (`ruff check .` + `ruff format --check .`), `test` (`pytest -m "not live"`), `verify-pass --pass ID [--quiet]`, `verify`, `e2e-sample`, `secret-scan [--history]`, `trace-check [paths]`, `hardcode-check`. `verify-pass` runs lint, then `pytest -m "p<ID> and not live"`, then the full non-live suite (regression), then `scripts/gates/p<ID>.py` if present, then secret-scan and hardcode-check. Exit code 0 only if all pass. A lane marker that collects no tests (pytest exit 5, e.g. pass 7) counts as a pass for that step. `--quiet` prints only failures (the stop hook uses it). Pure Python, no shell-isms, works on Windows |
| `scripts/scan_secrets.py` | Regexes: `sk-[A-Za-z0-9_-]{20,}`, `nvapi-[A-Za-z0-9_-]{20,}`, `AKIA[0-9A-Z]{16}`, `ghp_[A-Za-z0-9]{36}`, `xox[baprs]-[A-Za-z0-9-]{10,}`, `-----BEGIN [A-Z ]*PRIVATE KEY-----`, JWT `eyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{10,}`, and the assignment form `(?i)(api[_-]?key\|token\|secret\|password)\s*[=:]\s*['"]?([^\s'"#]{12,})`, flagged unless the value matches the placeholder allowlist (`your-`, `generate-`, `<…>`, `***`, `changeme`, `example`, `placeholder`). Skips `.git`, `.venv`, `var`, `node_modules`. Respects `.secrets-allowlist` (path globs for *fake-key fixtures*). `--history` scans `git log -p`. Never prints a full match; shows file:line and the first 4 characters only |
| `scripts/check_trace.py` | Validates each line against `TraceEvent`. Flags: `--require-collaboration` (≥ 2 distinct agents and ≥ 1 event with status in {needs_revision, retrying, fallback, escalated} or action `request_replan`) and `--require-live` (≥ 1 event with `backend=zetaris` and ≥ 1 with `provider=meterless`). Rejects any secret pattern |
| `scripts/check_hardcoding.py` | Static scan of `app/` (**excluding `app/cli/`**, which only delegates to `eval/` and `app/cli/examples.py`'s writer), `sources/` and `ui/`. Fails on the strings `output_examples`, `expected.json`, `data/evals`, `labels.jsonl`, `splits.json`, `truth_facts`. Fails on the regex `VND-\d{4}` or `CASE-\d+` in `app/agents`, `app/policy`, `app/orchestrator.py`, `app/facts.py`, `app/extract` and `app/memory`. Fails on scenario-code literals `"S\d\d"` anywhere in `app/` |
| `.github/workflows/ci.yml` | ubuntu-latest, Python 3.12, cache pip. Steps: `tasks.py setup`, `lint`, `test`, `secret-scan`, `hardcode-check` (P6 adds Docker) |
| `.env.example` | Master spec §10, verbatim (comments on their own lines only) |
| `.gitignore` | **Extend** the minimal file shipped in the spec pack (never remove its lines). Full list: `.env`, `.env.*`, `!.env.example`, `.venv` (no slash, so a worktree's `.venv` symlink is ignored), `*.pem`, `*.key`, `secrets/`, `credentials/`, `.venv/`, `__pycache__/`, `var/`, `logs/*`, `!logs/.gitkeep`, `!logs/examples/`, `.cursor/ACTIVE_PASS`, `.pytest_cache/`, `.ruff_cache/`, `eval/results/*/cases.jsonl` (large) |
| `.dockerignore` | `.git`, `.venv`, `var`, `logs/*`, `.env*`, `!.env.example`, `.cursor`, `tests/live`, `eval/results` |
| `Makefile` | Optional aliases that call `scripts/tasks.py` |
| `.secrets-allowlist` | Initially empty, with a comment |
| `logs/.gitkeep`, `logs/examples/.gitkeep`, `var/.gitkeep` (ignored) | Directories |
| `README.md` | Stub: name, track, one-line description, "Status: in development during the build window", links to `docs/spec/`. **No capability claims yet** |
| `docs/cursor-usage/README.md` | Template for the per-lane usage files (date, lane, model, plan file, notable agent loops, hook iterations). P6 compiles all lane files into `docs/CURSOR_USAGE.md` |
| `docs/PRIOR_WORK.md` | Fill in the import-commit sha (`git log --format=%H -1 -- docs/spec`) |

## 6. Interfaces (binding)

```python
# app/schemas/facts.py
FACT_KEYS = frozenset({
  "vendor.data_categories", "contract.status",
  "mfa.admin_enforced", "mfa.remote_enforced", "creds.vaulted", "creds.rotation_days",
  "access.review_interval_days", "crypto.at_rest", "crypto.in_transit_tls12",
  "assurance.claimed", "assurance.soc2_type2_current", "assurance.iso27001_current", "assurance.bridge_letter_current",
  "incidents.vendor_reported_24m", "incidents.itsm_vendor_related_24m", "incidents.material_unremediated_24m",
  "breach.notify_hours", "breach.notify_hours_claimed", "breach.notify_hours_contract",
  "dpa.signed", "dpa.vendor_commits",
  "residency.regions", "residency.regions_claimed", "residency.regions_contract",
  "transfer.mechanism", "transfer.mechanism_claimed",
  "subprocessors.disclosed", "subprocessors.disclosed_claimed",
  "sanctions.watchlist_matches", "sanctions.near_matches",
  "vuln.components_declared", "vuln.kev_matches", "vuln.patch_sla_critical_days", "pentest.interval_months",
})

# app/llm/generator.py (stub; P2-B implements)
class GenerationResult(BaseModel):
    text: str; parsed: BaseModel | None; provider: str; route: str; model: str | None
    latency_ms: int; tokens_in: int | None; tokens_out: int | None; repaired: bool = False
def generate(prompt: str, *, system: str | None = None, route: Literal["fast","deep"] = "fast",
             response: Literal["text","json"] = "text", schema: type[BaseModel] | None = None,
             timeout_s: float | None = None, purpose: str, tracer: Tracer | None = None,
             agent_name: str = "unknown") -> GenerationResult: ...

# app/data/backend.py (stub; P1-A implements)
class QueryResult(BaseModel):
    query_id: str; rows: list[dict]; columns: list[str]; backend: Literal["zetaris","duckdb","inline"]
    request_id: str | None; latency_ms: int; fallback_from: str | None = None
class DataBackend(Protocol):
    name: str
    def run(self, query_id: str, params: dict) -> QueryResult: ...
```

## 7. Acceptance tests (marker `p0`)

| Id | Test |
|---|---|
| P0-T1 | `Settings()` loads with an empty environment. **Non-secret** defaults equal `.env.example` values; every secret is `None` both with an empty environment and with `.env.example` loaded as-is (placeholders count as unset). With fake real-looking secrets set, `repr(settings)`, `str(settings)` and `redacted_dict()` contain none of them |
| P0-T2 | Organiser aliases fill the NVIDIA fallback fields only when the native vars are absent |
| P0-T3 | The master spec §7 run-response example validates as `RunResponse`. `CaseInput` rejects none or both of `vendor_id`/`submission`. `RunRequest` accepts both the bare and the wrapped shape. `TraceEvent` requires the organisers' fields |
| P0-T4 | `canonical_json` is key-order invariant, stable for datetimes (UTC `Z`) and nested models. `sha256_hex` is stable across runs (golden value) |
| P0-T5 | `Tracer` writes valid JSONL (every line parses as `TraceEvent`), emits a readable stdout line, and masks a planted fake key in the summaries |
| P0-T6 | `GET /health` returns 200 with a `mode` block and no secrets. (b) `POST /run` returns 501 `ErrorResponse` (**this clause is superseded by P3-T11; P3 deletes clause (b) and says so in its report**). Malformed JSON returns 400 `ValidationFailed`. An unhandled exception returns 500 with no traceback text |
| P0-T7 | `scan_secrets` flags every planted pattern in a temp tree. It ignores placeholders and allowlisted fixture paths. Output never contains a full secret |
| P0-T8 | `check_hardcoding` flags a planted `output_examples` read and a `VND-0007` literal in a temp `app/agents/x.py` |
| P0-T9 | `check_trace` accepts a valid two-agent trace with a `needs_revision` event, and rejects a trace missing `status` or containing a fake key |
| P0-T10 | `python run.py --help` lists **at least** every command in master spec §8.11 (`serve ui preflight generate-data sources zetaris llm guard-eval assess review demo-session replay audit-verify eval calibrate examples`). An unknown command exits 2 |
| P0-T11 | Every `Settings` field appears in `.env.example`; `.env.example` passes `scan_secrets`; **no line has an inline comment** (no line matches `=\S.*\s#`), so `docker run --env-file` gets clean values |
| P0-T12 | `FACT_KEYS` entries are unique, lowercase and dotted, and include every key named in `01_DATA_AND_ZETARIS.md` §3 and `02_POLICY.md` §4 (test holds a literal copy) |
| P0-T13 | Importing every stub module succeeds (`pkgutil.walk_packages` over `app`) |

## 8. Verification

```
python scripts/tasks.py setup
python scripts/tasks.py verify-pass --pass 0
python run.py --help
python run.py serve   # then: curl http://localhost:8000/health
```

The gate script `scripts/gates/p0.py` asserts that the CI workflow file exists and lists the five steps.

## 9. Definition of done

- [ ] All P0 tests are green locally and in CI on the branch.
- [ ] `.cursor/` from the spec pack is unchanged and the hook fires once (note the result in the report).
- [ ] No dependency outside the pinned list.
- [ ] Report and `docs/cursor-usage/P0.md` written.

## 10. Cut lines

The `Makefile` and `hypothesis` (use plain parametrised loops instead).

## 11. Cursor prompt

```
/start-pass 0
You are implementing pass P0 (bootstrap) of Arbiter.
Read: AGENTS.md; docs/spec/00_MASTER_SPEC.md §§5.2, 7, 8.9, 9, 10, 11, 14; docs/spec/passes/README.md; docs/spec/passes/P0_BOOTSTRAP.md.
Plan Mode first: write .cursor/plans/P0.md listing every file in §5, the interfaces in §6 and tests P0-T1..P0-T13. Wait for approval.
Then: tests first (marker p0) → commit → implement until `python scripts/tasks.py verify-pass --pass 0` is green.
Pin exact dependency versions from a fresh `pip install` today; add nothing beyond §5.
Do not implement any lane's logic: stubs only, with the owning lane named in each docstring.
Finish with docs/passes/P0_REPORT.md and docs/cursor-usage/P0.md; push branch p0-bootstrap; delete .cursor/ACTIVE_PASS; stop.
```

## 12. Explain it

1. Why do later lanes only fill files that P0 created?
2. What does `verify-pass` run, in which order, and why the full suite as well?
3. How does a secret get masked in a trace line?
4. What makes a hash "canonical" here, and why does replay depend on it?
5. What happens when the API hits an exception it did not expect?
