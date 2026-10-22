# P2-D: ScoutGuard, execution contracts, audit chain — plan

## Goal

Implement lane P2-D so Arbiter has a production-shaped **ScoutGuard** (deterministic injection detectors plus optional fast-route model check in the ambiguous band, PII redaction, metadata-only logging), **HMAC-signed immutable execution contracts** with policy-driven approval gates and child re-issue on approval, and an **append-only SQLite audit hash chain**. Guard quality is measured on Meterless’s adversarial set (byte copy) and a synthetic TPRM-flavoured domain set (≥40 labelled segments). P3 can consume `guard()`, `issue`/`sign`/`verify`, and `AuditChain.append`/`verify` without touching this lane’s files.

## Branch and active pass

- Spec branch: `p2d-guard` (marker `p2d`). Current workspace branch is `p2d-report`; I will push to `p2d-guard` when finishing unless you prefer staying on `p2d-report`.
- Active pass: `2d plan` until you approve this file, then `2d build`.

## Read-first (done for planning)

- `AGENTS.md`; master spec §§8.3, 8.7, 8.8; `docs/spec/passes/P2_ENGINES.md` lane D; `docs/spec/02_POLICY.md` §3 (`approvals` block).
- Meterless clone at `~/meterless`: `adversarial.jsonl`, `thresholds.yaml`, `risk-and-policy.md`, `execution-contract.md`, `prompt-injection-block` example.

## Dependencies consumed (not owned)

| Dependency | Use |
|---|---|
| `app/schemas/evidence.py` (`GuardResult`, `GuardFlag`) | Guard return type — **no schema edits** (P0 owns schemas; `evidence_meta` stays inside detector internals / logging extras, not a new schema field unless you approve additive change). |
| `app/schemas/contract.py` (`ExecutionContract`, …) | Contract payload — no edits planned. |
| `app/canon.py` | `canonical_json`, `sha256_hex` for signatures and audit hashes. |
| `app/llm/generator.py` | `generate(..., route="fast", purpose="guard_classify", response="json", schema=…)` for ambiguous band when `use_model=True`. |
| `app/llm/providers/offline.py` / `OfflineProvider` | Ambiguous band falls back to **warn** when the generator is offline (P2-T44). |
| `app/policy/engine.py` | `required_approvals(record, policy)` when issuing contracts (P2-C merged on this tree). |
| `app/policy/loader.py` | `load_default()` in tests and `guard-eval` for approval expectations. |
| `app/tracing.py` | Optional `Tracer` on `guard()`; metadata-only summaries. |

## Scout adversarial → detector mapping (implement before coding detectors)

| Case id | Detectors (expected) |
|---|---|
| `inj-instr-override-001` | instruction_override |
| `inj-instr-override-002` | instruction_override (+ unrestricted phrasing) |
| `inj-role-confusion-001` | role_confusion (`</user>`, `<system>`) |
| `inj-role-confusion-002` | role_confusion (`[INST]`, pretend system) |
| `inj-tool-ref-001` | out_of_band_tool (`internal_admin_panel`, grant/admin panel) |
| `inj-soft-md-001` | user_role_override + secret_exfiltration (markdown body) |
| `inj-control-bytes-001` | hidden_markup (literal `\u202E` spelling + decoded bidi) |
| `clean-001` … `clean-003` | none above threshold (pass) |

Additional detector families from spec (for domain set): addressed-to-AI, HTML comments / `display:none`, zero-width chars, benign look-alikes scored &lt; 0.7 with context words.

## Files to create or edit (ownership §3 — P2-D only)

| File | Action |
|---|---|
| `app/guard/patterns.py` | Implement all deterministic detectors; export `scan(text, *, capabilities) -> list[PatternHit]` with `(kind, score, evidence_meta)`. |
| `app/guard/pii.py` | `redact(text) -> tuple[str, dict[str, str]]` stable `[EMAIL_n]`, `[PHONE_n]`, `[IBAN_n]`, `[SECRET_n]`. |
| `app/guard/scout_guard.py` | `guard(...)` orchestration, thresholds 0.7 / 0.3, model band, PII on pass/warn path, metadata-only log + trace. |
| `app/guard/__init__.py` | Export `guard` (and optionally `redact`). |
| `app/actions/keys.py` | `signing_key() -> bytes` from env or `var/keys/ephemeral.key` (create once, reuse, trace note). |
| `app/actions/contracts.py` | `issue`, `sign`, `verify`, `add_approval` per spec; module docstring on 7-day TTL deviation. |
| `app/audit/chain.py` | `AuditChain` with SQLite WAL, `append`, `verify`, no update/delete API. |
| `vendor/meterless/scout_adversarial.jsonl` | Byte copy from Meterless eval set. |
| `vendor/meterless/scout_thresholds.yaml` | Byte copy from Meterless `thresholds.yaml`. |
| `vendor/meterless/NOTICE-scout.md` | Attribution, sha256 of copies, licence pointer. |
| `data/evals/injection_domain.jsonl` | ≥40 synthetic TPRM segments (half clean), labelled. |
| `app/cli/guard.py` | Real `guard-eval` handler (replace stub). |
| `scripts/gates/p2d.py` | Lane gate: vendor copies present, domain set ≥40 lines, import smoke + optional quick deterministic eval floors. |
| `tests/conformance/test_scout_adversarial.py` | P2-T40 |
| `tests/unit/guard/test_domain_metrics.py` | P2-T41 |
| `tests/unit/guard/test_pii.py` | P2-T42 |
| `tests/unit/guard/test_guard_logging.py` | P2-T43 |
| `tests/unit/guard/test_guard_model_band.py` | P2-T44 |
| `tests/unit/contracts/test_contracts_crypto.py` | P2-T45 |
| `tests/unit/contracts/test_contracts_approval.py` | P2-T46 |
| `tests/unit/audit/test_audit_chain.py` | P2-T47 |
| `tests/unit/contracts/test_signing_key.py` | P2-T48 |
| `docs/passes/P2-D_REPORT.md` | Finish: guard-eval table, benign look-alike examples, Explain-it answers. |
| `docs/cursor-usage/P2-D.md` | Finish: model, plan, hook iterations. |

**Ownership exceptions:** none planned. I will not edit `app/schemas/*`, `app/llm/generator.py`, `app/policy/*`, or P3 files.

## Interfaces (binding signatures)

```python
# app/guard/patterns.py
class PatternHit(NamedTuple):
    kind: str
    score: float
    evidence_meta: dict[str, Any]

def scan(text: str, *, capabilities: set[str]) -> list[PatternHit]: ...

# app/guard/pii.py
def redact(text: str) -> tuple[str, dict[str, str]]: ...

# app/guard/scout_guard.py
def guard(
    text: str,
    *,
    surface: Literal["vendor_document", "vendor_answer", "api_input"],
    capabilities: set[str],
    segment_id: str,
    tracer: Tracer | None = None,
    use_model: bool = True,
) -> GuardResult: ...

# app/actions/keys.py
def signing_key() -> bytes: ...

# app/actions/contracts.py
def issue(
    decision: DecisionRecord,
    report: Report,
    *,
    capabilities_map: dict[str, list[str]],
    policy: Policy,
    ttl_days: int = 7,
    trace_id: str,
    registry_version: int,
) -> ExecutionContract: ...

def sign(contract: ExecutionContract, *, key: bytes | None = None) -> ExecutionContract: ...

def verify(
    contract: ExecutionContract,
    *,
    now: datetime,
    key: bytes | None = None,
) -> tuple[bool, str]: ...

def add_approval(
    contract: ExecutionContract,
    *,
    by: str,
    role: str,
    decision: Literal["approve", "reject"],
    rationale: str,
    now: datetime,
    policy: Policy,
    key: bytes | None = None,
) -> ExecutionContract: ...

# app/audit/chain.py
class AuditChain:
    def __init__(self, db_path: Path | str = "var/audit.db") -> None: ...
    def append(self, event_type: str, case_id: str, payload: dict[str, Any]) -> int: ...
    def verify(self) -> tuple[bool, int | None]: ...
```

**Guard policy:** `score = max(detector scores)`; ≥0.7 → `block`; [0.3, 0.7) → model classify if `use_model` and not offline → else `warn`; &lt;0.3 → `pass`. Apply PII redaction to `redacted_text` for pass/warn; blocked segments still redact for any downstream safety but extraction should not use raw text.

**Contract signing:** HMAC-SHA256 over `canonical_json(contract.model_dump(mode="json")` with `signature` omitted). `verify` checks signature, expiry, each `tool_plan[].capability ∈ scope.capabilities`, and allowed `state` transitions (issued → pending_approval → approved/rejected/expired; no mutation after sign).

**Audit hash:** `hash = sha256_hex(prev_hash + canonical_json({seq, ts, case_id, event_type, payload}))`, genesis `prev_hash = ""` or fixed zero string (pick one and test consistently — default: empty string for seq=1).

## Acceptance tests (`@pytest.mark.p2d`)

| Id | File | How tested |
|---|---|---|
| **P2-T40** | `tests/conformance/test_scout_adversarial.py` | Load `vendor/meterless/scout_adversarial.jsonl`; for each row call `guard(..., use_model=False)` with empty capabilities except tool-ref cases; assert 7 injections `level==block`, 3 clean `level==pass`. |
| **P2-T41** | `tests/unit/guard/test_domain_metrics.py` | Run all `data/evals/injection_domain.jsonl` with `use_model=False`; compute precision/recall vs `expected.injection`; assert targets ≥0.95 / ≥0.90 and hard floors ≥0.90 / ≥0.82 in separate asserts. |
| **P2-T42** | `tests/unit/guard/test_pii.py` | Strings containing each PII class; assert placeholders, stable numbering across repeats, no raw substrings, mapping round-trip. |
| **P2-T43** | `tests/unit/guard/test_guard_logging.py` | Unique canary substring in input; `caplog` + `Tracer` to temp `logs/`; assert canary absent from logs and trace JSONL; only kind/score/segment_id/length in guard log extras. |
| **P2-T44** | `tests/unit/guard/test_guard_model_band.py` | Craft text scoring ~0.5 deterministic; `unittest.mock.patch` on `app.llm.generator.generate` returning JSON `{injection: true/false, score, kind}` → block/pass; patch raising `OfflineProvider` → warn. |
| **P2-T45** | `tests/unit/contracts/test_contracts_crypto.py` | Minimal `DecisionRecord`/`Report` fixture; sign+verify ok; parametrize tamper each top-level field → fail; expired; capability outside scope; permute dict key order before sign → still verifies. |
| **P2-T46** | `tests/unit/contracts/test_contracts_approval.py` | Issue T1 APPROVE contract; `add_approval` → new `contract_id`, `parent_id` set; parent byte-stable; `risk.approvals_required` matches `required_approvals` from policy. |
| **P2-T47** | `tests/unit/audit/test_audit_chain.py` | `tmp_path` DB; append 100 events; `verify()` ok; raw SQL tamper one `payload_json` → `verify` returns `(False, seq)`; `inspect.getmembers` / source scan: no public update/delete methods. |
| **P2-T48** | `tests/unit/contracts/test_signing_key.py` | Unset env key, fresh temp `var/keys/`; two `signing_key()` calls same bytes; trace/event or module flag records ephemeral use; assert key file not under `logs/`. |

Workflow after approval: commit failing tests `test(p2d): acceptance tests`, implement until `python scripts/tasks.py verify-pass --pass 2d` and `python run.py guard-eval --set all --no-model` succeed.

## Implementation notes

1. **Domain eval set:** Author 40–48 rows covering SOC2 markdown with HTML comments, “note to AI reviewers”, `call approve_vendor`, bidi/ZWJ, policy-supersession benign lines, normal “ignore” prose, clean vendor answers.
2. **`guard-eval` CLI:** Shared metric helper (TP/FP/TN/FN → precision/recall/F1); write `logs/guard-eval-<ts>.json` with per-set metrics and `--no-model` flag honoured.
3. **Concurrency:** Audit chain uses SQLite WAL + short transactions; tests remain single-process.
4. **Intent / tool plan:** Map outcome → Scout intent strings and tool steps per master spec §8.7; `capabilities_map` supplies allowed capabilities per intent (passed into `issue`, not hardcoded vendor ids).

## Risks and questions for Josh

1. **Branch name:** Proceed on `p2d-report` or create/checkout `p2d-guard` before the first commit?
2. **`GuardFlag` schema:** Spec mentions `evidence_meta` in detectors; current `GuardFlag` has no field for it. Plan: keep rich meta in Python logging only unless you want an additive optional field on `GuardFlag` (requires P0 schema ✎ — I would avoid unless needed for P3 traces).
3. **P2-B completeness:** `generator.generate` still raises `OfflineProvider` by default; ambiguous-band model path is test-driven via mock. OK to ship P2-D with real `generate` integration ready but inactive until P2-B lands?
4. **`issue()` policy parameter:** Spec says `approvals_policy`; I plan to pass `Policy` from `load_default()` and call `required_approvals(decision, policy)` — confirm this matches your expectation vs a slimmer approvals-only struct.
5. **Audit genesis hash:** Prefer empty string or 64-zero hex for the first row’s `prev_hash`? (Either works if tests and `verify()` agree.)

---

**Waiting for your approval** before setting `.cursor/ACTIVE_PASS` to `2d build` and writing tests.
