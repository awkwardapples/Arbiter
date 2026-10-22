# P4-B plan: SQLite case store, approvals, replay, read API, Docker

Approved 2026-10-22. Branch is `p4b-api` from `origin/main`. `output_examples/` is a waiver until P6: absent passes, present with fewer than 3 files fails with the P6 message. Clean-clone is opt-in (`DOCKER=0` or docker missing skips it). The CI job builds the repo Dockerfile. `bundle_json` and the two ownership exceptions (HealthResponse fields, CI docker job) are approved.

## Goal

Replace the JSON case store with SQLite while keeping the public `Store` methods P3 and P4-A already call. Pending contracts can be approved or rejected by role over HTTP: a sufficient role produces a signed child contract and, once every required role is satisfied, the existing executor writes the outbox. Any stored decision replays by re-running the policy engine and checking the policy hash, the record hash and the contract signatures. The read API serves the risk-sorted queue, the case, the trace and audit-chain verification. A sample-mode Docker image, a CI smoke job and a clean-clone script prove a judge can run the six input examples with no env file.

## Branch and phase

`.cursor/ACTIVE_PASS` is `4b plan`. Marker `p4b`. The pass file’s branch is `p4b-api`. This worktree is on `p4b-report`, two commits behind `origin/main` (`e967cd9` P3 T15 evidence, `873e316` docs). See question 1. No code until this plan is approved.

## Schema (`var/arbiter.db`, WAL)

`Store(root="var")` opens `root / "arbiter.db"` (so tests that pass a temp root stay isolated). `PRAGMA journal_mode=WAL`. One connection per `Store` instance; each write commits. A new `Store(same root)` sees committed rows (P4-T15).

| Table | Columns |
|---|---|
| `cases` | `case_id PK`, `run_id`, `vendor_ref`, `legal_name`, `created_at`, `status`, `outcome`, `tier`, `residual_risk`, `decision_json`, `report_json`, `trace_path`, `mode_json`, **`bundle_json`** |
| `contracts` | `contract_id PK`, `case_id`, `parent_id`, `state`, `json` |
| `reviews` | `review_id INTEGER PK`, `case_id`, `json` |
| `human_decisions` | `id INTEGER PK`, `case_id`, `json` |

`bundle_json` is the full `CaseBundle` (canonical JSON). The named columns are the queue projection, filled on every `save` / `put_human_decision`. `get()` round-trips `bundle_json`. P3’s bundle carries `input`, `first_decision`, `contract_ids`, `artifacts`, `limitations` and `log_file`, which the pass’s column list does not have; dropping them would break `get()` for the orchestrator and P4-A. This extra column is the whole deviation. Cut line if time runs out: skip the JSON import below and start from an empty database.

One-shot import, only when `cases` is empty: read `root/cases/*.json` into `cases`, `root/contracts/*.json` into `contracts`, `root/reviews/*.json` into `reviews`. Idempotent. Files are left in place.

`put_human_decision` inserts `human_decisions` and updates the case row (decision, outcome, tier, residual risk, bundle) so `get()` still returns the latest decision, which is what the JSON store does today.

## Store interface (stable)

Unchanged signatures:

```python
class Store:
    def __init__(self, root: Path | str = "var") -> None: ...
    def save(self, bundle: CaseBundle) -> None: ...
    def get(self, case_id: str) -> CaseBundle: ...          # NotFound
    def list(self, order: Literal["risk", "recent"] = "risk") -> list[CaseBundle]: ...
    def put_contract(self, contract: ExecutionContract) -> None: ...
    def contracts_for(self, case_id: str) -> list[ExecutionContract]: ...
    def put_review(self, review: BaseModel | dict[str, Any]) -> None: ...
    def reviews_for(self, case_id: str) -> list[dict[str, Any]]: ...
    def put_human_decision(self, record: DecisionRecord) -> None: ...
```

`list("risk")` keeps the P3 key: outcome severity (DECLINE first), then residual risk descending, then `case_id`. `list("recent")` stays `created_at` descending. The HTTP queue uses a different sort (below); P4-A keeps the method it already has.

Additive, used by the contract route (lookup by id has no case id):

```python
def get_contract(self, contract_id: str) -> ExecutionContract: ...  # NotFound
```

## Replay (`app/audit/replay.py`)

```python
class ReplayChecks(BaseModel):
    policy_hash: bool
    record_hash: bool
    contract_signatures: bool

class ReplayResult(BaseModel):
    match: bool
    diff: list[str]
    checks: ReplayChecks

def replay(
    case_id: str,
    *,
    store: Store | None = None,
    policy_root: Path | None = None,
    now: datetime | None = None,
) -> ReplayResult: ...
```

Steps, matching master spec §8.8:

1. Load the stored `DecisionRecord` from the store (`NotFound` if missing).
2. Major version of `policy_version` (`"1.0.0"` → `1`) selects `policy_root / arbiter_policy.v{major}.yaml`. Load it with `load_policy`. `policy_hash` is `policy_sha256(policy) == record.policy_sha256`. That is the canonical Policy-model hash `decide` already stores, not raw file bytes. A tampered control weight flips it; a comment-only edit would not, and the test will change a weight.
3. Load `policy_root / calibration / {calibration_version}.json` with `load_calibration`.
4. `recomputed = decide(record.policy_inputs, policy, calibration)`, then `force_escalate(recomputed, reason)` for each stored `escalation_reasons` entry, in order.
5. `record_hash` is true only when both hold: `recomputed.record_sha256 == record.record_sha256`, and `sha256_hex(stored.model_dump(exclude={"record_sha256"})) == record.record_sha256`. The second clause is what makes a mutated fact fail even if the stored hash field was left as the original.
6. `diff` lists fact keys whose stored `value` differs from the recomputed fact, plus `outcome` when those differ. Paths look like `facts.<key>`.
7. `contract_signatures` calls `contracts.verify(contract, now=contract.issued_at)` for every contract on the case (HMAC, scope and state at issuance, so a later expiry does not fail replay). False if any returns not ok, or if there are no contracts. `match` is the AND of the three checks and an empty diff.

`now` is accepted for tests; signature checks use `issued_at`, not wall-clock expiry.

## HTTP

Existing handlers in `app/api/main.py` already map `ArbiterError` and `RequestValidationError` to `ErrorResponse` with no traceback. Routes only raise typed errors.

### `routes_cases.py`

| Method | Behaviour |
|---|---|
| `GET /cases` | Queue items: `case_id`, `vendor` (legal name), `outcome` (the badge text: `APPROVE`, `APPROVE_WITH_CONDITIONS`, `REQUEST_INFO`, `ESCALATE`, `DECLINE`), `tier`, `residual_risk`, `status`, `created`. Sort residual risk descending, then `created_at` ascending. |
| `GET /cases/{id}` | Bundle, report, contracts, reviews, `trace_path`. 404 `NotFound`. |
| `GET /cases/{id}/trace` | Parsed JSONL events from `log_file`. Missing file → 404. A non-JSON line → 422 `ParseFailure`. |
| `POST /cases/{id}/replay` | `ReplayResult`. |

### `routes_contracts.py`

`POST /contracts/{id}/approve` body is the existing `ApprovalRequest` (`by`, `role`, `decision: approve|reject`, `rationale` min 30).

Clock seam (tests monkeypatch it; same shape as the orchestrator’s injected clock):

```python
def current_time() -> datetime: ...
```

1. `get_contract`. Missing → 404.
2. `contracts.verify(contract, now=current_time())`. Reason `expired` → 409 `ContractInvalid`. The message contains `expired`.
3. State other than `pending_approval` → 422 `PolicyIneligible`.
4. Role check against `policy.roles` (rank; a higher rank satisfies a lower requirement) and `contract.risk.approvals_required`. If `role` satisfies none of the still-unmet required roles → 403 `Forbidden`. The message lists the required roles (`tprm_lead` for a DECLINE). This happens before `add_approval`, so a wrong role writes nothing.
5. `contracts.add_approval(...)` builds the signed child. `decision=reject` leaves the child `rejected`.
6. If the child is approved, or the executor’s rank check is satisfied, call `executor.execute` with `outbox_dir = store.root / "outbox"`. On `executed`, store the executed child. The outbox file is `var/outbox/procurement/<contract_id>.json` for a decline (`procurement.decline.record`).
7. `put_contract` the child. Audit, via the existing `AuditChain` (no edit to `chain.py`): `contract_issued` for the child; `action_executed` when the outbox write happens. Payload is role, by, parent id, state. No new event-type names.

Example 5 is DECLINE, so the issued contract is `pending_approval` and requires `tprm_lead` (`policy/arbiter_policy.v1.yaml` `approvals.DECLINE`, also master spec §8.7). `tprm_analyst` is 403. `tprm_lead` executes.

### `routes_meta.py`

`GET /health` keeps `HealthResponse` and adds optional fields (schema exception below):

- `data`: `app.data.status.check()` (DuckDB counts; Zetaris probe only if that module’s `status` exists)
- `provider`: `app.llm.status.check()`. With the token unset this returns offline immediately and does not scan ports, so P0’s `/health` test stays fast.
- `hmem_records`: `app.memory.keeper.count()` when that callable exists, else `null`. The keeper module is still P4-A’s stub; this route does not edit it.
- `audit_chain_length`: `SELECT COUNT(*)` on `var/audit.db` when the file exists, else 0. Health does not create the database.

`GET /vendors`: `DuckDBBackend.run("Q_VENDOR_LIST", {})` in sample mode, `get_backend` otherwise. Response is the registry rows (`vendor_id`, `legal_name`, `category`, `criticality`, `onboarding_status`).

`GET /audit/verify`: `AuditChain.verify()` → `{ok: bool, first_bad_seq: int | null}`.

## CLI (`app/cli/audit.py`)

`replay CASE` prints the `ReplayResult` JSON and exits 0 on `match`, 1 otherwise. `audit-verify` prints `{ok, first_bad_seq}` and exits 0 on ok, 1 otherwise. Both replace the P4-B stubs. `run.py` already dispatches them; it is not edited.

## Docker and CI

`Dockerfile` (new):

- `python:3.12-slim`
- `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`, `PORT=8000`
- copy `requirements.txt`, `pip install --no-cache-dir -r requirements.txt`, then `COPY . .` (`.dockerignore` already keeps `run.py`, `app/`, `ui/`, `eval/`, `policy/`, `zetaris/`, `data/sample`, `data/kev`, `input_examples`, `vendor/` and drops `.env*`)
- non-root user owning `/app/logs` and `/app/var`
- `EXPOSE 8000 8501`
- `HEALTHCHECK` the Python urllib one-liner against `http://127.0.0.1:8000/health`
- `CMD ["python", "run.py", "serve"]`
- no secrets, no runtime downloads

`docker-compose.yml` (new):

- `api`: build `.`, port 8000, `SAMPLE_MODE=true`
- `ui`: same image, `python run.py ui`, port 8501, `ARBITER_API_URL=http://api:8000`
- `sources`: same image, `python run.py sources`, port 8100, profile `zetaris`
- comment: live Nightshift stays on the host, because it binds `127.0.0.1`

`.github/workflows/ci.yml` (✎ P4-B): add a `docker` job. Build, `docker run -d -p 8000:8000 -e SAMPLE_MODE=true` with no env file, wait for `/health`, POST each `input_examples/example_*.json` to `/run`, assert `output.decision` against `input_examples/expected.json`, upload `logs/` as an artifact. The job does not run on pytest; P4-T17 is the local twin.

## Clean clone (`scripts/clean_clone_check.py`)

```python
def main(argv: list[str] | None = None) -> int: ...
```

`python scripts/clean_clone_check.py <repo-url>` and `python scripts/clean_clone_check.py --local .` (local path is cloned with `git clone --local` into a temp dir, not checked in place).

Steps from `04_SUBMISSION_PLAYBOOK.md` §6:

1. Require `run.py`, `README.md`, `.env.example`, `input_examples/` (≥ 3). `output_examples/` (≥ 3) is required when that directory exists. See question 2 for the pre-P6 waiver.
2. `docker build -t arbiter-check .`
3. `docker run -d -p 8000:8000 -e SAMPLE_MODE=true` with no env file. Wait for `/health`. POST every input example. Assert status, `RunResponse` shape, distinct outputs, outcomes vs `expected.json`.
4. Copy container `logs/`, run `scripts/check_trace.py` on each trace, check stdout for readable lines.
5. Seeded-by-time novel inline `CaseInput`, POST `/run`, assert a valid five-way outcome.
6. `scripts/scan_secrets.py` on the tree; `git log -p` scanned for the same secret patterns; `git ls-files` must not list `.env`, `*.pem`, `*.key`.
7. Fresh venv, `pip install -r requirements.txt`, `SAMPLE_MODE=true python run.py assess --input input_examples/example_1.json`.
8. Write `logs/clean-clone-report.md` (pass/fail per step) and copy it to `docs/passes/clean-clone-<YYYY-MM-DD>.md`.

`scripts/gates/p4b.py` (this lane’s stub to fill) only checks that the Dockerfile, compose file, replay function and the three route modules import, and that the workflow contains a `docker` job. It does not build an image. Heavy checks stay in T17 and T18.

## Files

Ownership from `docs/spec/passes/README.md` §3.

| File | Action |
|---|---|
| `app/store.py` | SQLite implementation, same methods, import |
| `app/audit/replay.py` | `replay` |
| `app/api/routes_cases.py` | queue, case, trace, replay |
| `app/api/routes_contracts.py` | approve / reject |
| `app/api/routes_meta.py` | health extension, `/vendors`, `/audit/verify` |
| `app/cli/audit.py` | `replay`, `audit-verify` |
| `Dockerfile` | image |
| `docker-compose.yml` | api, ui, sources |
| `scripts/clean_clone_check.py` | steps 1–8 |
| `scripts/gates/p4b.py` | fill this lane’s gate stub |
| `docs/passes/clean-clone-<date>.md` | written by the script when T18 runs |
| `tests/unit/replay/test_replay.py` | P4-T10, P4-T11 |
| `tests/unit/api/test_cases.py` | P4-T14, trace |
| `tests/unit/api/test_contracts.py` | P4-T13 |
| `tests/unit/api/test_meta.py` | P4-T12, health, vendors |
| `tests/unit/api/test_errors.py` | P4-T16 |
| `tests/unit/store/test_store.py` | P4-T15, migration |
| `tests/unit/docker/test_smoke.py` | P4-T17 |
| `tests/unit/docker/test_clean_clone.py` | P4-T18 |
| `docs/passes/P4-B_REPORT.md` | finish (everyone’s own report) |
| `docs/cursor-usage/P4-B.md` | finish |

**Flagged exceptions**

1. `app/schemas/api.py` ✎ additive only. Extend `HealthResponse` with optional `data: dict | None = None`, `provider: dict | None = None`, `hmem_records: int | None = None`, `audit_chain_length: int = 0`. P0’s health test only asserts `mode` is present and that the body contains no `nvapi-` string. Queue and replay bodies stay as pydantic models inside the route modules so the schema edit stays this small. Noted in the pass report.
2. `.github/workflows/ci.yml` ✎ P4-B. Docker job only; the existing `test` job stays.

Not touched: `app/api/main.py`, `app/audit/chain.py`, `app/actions/*`, `app/orchestrator.py`, `app/memory/keeper.py`, `run.py`, `app/policy/*`.

## Acceptance tests (marker `p4b`)

Written first, committed as `test(p4b): acceptance tests`, confirmed failing for a missing implementation rather than an import typo.

| Id | How |
|---|---|
| P4-T10 | Offline (`SAMPLE_MODE`, `LLM_PROVIDER=offline`, temp cwd) run all six `input_examples/example_*.json` through `orchestrator.run`, then `replay`. Each result is `match=true` with all three checks true. |
| P4-T11 | On a stored record, change one fact `value` and save without recomputing the hash. `match` is false and `diff` contains `facts.<that key>`. Copy the policy YAML, change one control weight, call `replay(..., policy_root=copy)`. `checks.policy_hash` is false. |
| P4-T12 | `GET /audit/verify` returns `ok: true` on an intact chain (append one row with `AuditChain`, then GET). `UPDATE` that row’s `hash` in sqlite. The next GET returns `ok: false` and `first_bad_seq` equal to that row. |
| P4-T13 | Run example 5. The stored contract is `pending_approval`. POST approve as `tprm_analyst` → 403 and the body names `tprm_lead`; no outbox file. POST approve as `tprm_lead` with a ≥ 30 character rationale → executed child and a file under `var/outbox/procurement/`. A second contract whose `expires_at` is before `current_time` (monkeypatched) → 409 and the body contains `expired`. |
| P4-T14 | Save three bundles with residual risks 10, 90, 90 and known `created_at`. `GET /cases` returns 90 (earlier created), 90 (later created), 10. Every item’s `outcome` is one of the five outcome words. |
| P4-T15 | `save` / `put_contract` / `put_review`, drop the `Store`, open another on the same root, `get` / `list` / `contracts_for` / `reviews_for` match. Through `TestClient`, `GET /cases/{id}` is identical after a new `Store` opens the same file. |
| P4-T16 | Parametrised: 404 `GET /cases/missing`; 400 approve with a 10-character rationale (`RequestValidationError` → `ValidationFailed`); 403 analyst on the decline contract; 409 expired contract; 422 approve a contract already `executed` (`PolicyIneligible`). Each body validates as `ErrorResponse` and the text has no `Traceback`. |
| P4-T17 | Skipped unless `ARBITER_DOCKER_TESTS=1`. Build the image, run it with `SAMPLE_MODE=true` and no env file, `GET /health` is 200, all six examples match `expected.json` outcomes. |
| P4-T18 | `clean_clone_check.py --local .` exits 0 and the report marks steps 1–8 pass (step 1 subject to question 2). Needs Docker and a network install into a fresh venv. |

## Verification (after build)

```
python run.py replay CASE-0001
python run.py audit-verify
python scripts/tasks.py verify-pass --pass 4b
```

`verify-pass` is lint, `pytest -m "p4b and not live"`, full non-live regression, `scripts/gates/p4b.py`, secret scan, hardcode check. T17 stays skipped in that run. T18 runs.

## Risks

- Replay equality depends on `decide` + `force_escalate` reproducing `record_sha256` for the six offline examples, including any challenger escalation. If a stored record was hashed by a path those two functions do not repeat, T10 fails and I will stop rather than special-case an example id.
- T18 is a Docker build plus a venv install. It will dominate `verify-pass` runtime.
- `app.llm.status.check()` must stay offline-fast when the Meterless token is unset, or P0’s health test slows down.
- `ui/app.py` is still a P5-A stub. Compose starts it; the UI booting is not a P4-B acceptance check.
- Approvals call `contracts.add_approval` and `executor.execute` as they exist. Role rank is enforced in the route (403). Exact-role vs rank inside `add_approval` is left alone; for DECLINE the required role is exactly `tprm_lead`, so the child reaches `approved` and the executor writes the outbox.

## Questions

1. **Branch.** This worktree is `p4b-report`, behind `origin/main` by the P3 T15 merge and its docs note. The pass file says push `p4b-api`.
   - A. Fast-forward to `origin/main`, do the work here, push to `p4b-api`. Recommended: the T15 commits are docs plus evidence, and the pass names the branch.
   - B. Stay on `p4b-report` and push that branch.
   - C. Fast-forward, but keep the name `p4b-report`.

2. **Clean-clone step 1 and `output_examples/`.** The playbook requires at least three files there. The directory does not exist yet; P6 owns it, and output examples may only be produced by `python run.py examples`. Writing them by hand would break the integrity rule.
   - A. Step 1 requires `output_examples/` (≥ 3) only once that directory exists, and the report records a labelled waiver until P6. Recommended.
   - B. Fail step 1 until three example outputs exist. T18 cannot pass in this lane.
   - C. Stop and wait until you generate the examples.

3. **Docker on this machine.** T17 (opt-in) and T18 (part of `verify-pass`) need a working Docker daemon, and T18 also needs pip.
   - A. Docker is available; run T18 inside `verify-pass`. Recommended if `docker info` works in this WSL distro.
   - B. Docker is not available here; keep T17 and T18 skipped unless `ARBITER_DOCKER_TESTS=1`, and let the GitHub `docker` job be the proof. T18 would not run locally.
