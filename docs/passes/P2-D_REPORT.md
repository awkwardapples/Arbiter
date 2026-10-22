# P2-D report: ScoutGuard, contracts, audit chain

## Built

- **ScoutGuard** (`app/guard/`): deterministic pattern layers, ambiguous-band hook to `generator.generate(purpose="guard_classify")`, PII redaction, metadata-only logging.
- **Execution contracts** (`app/actions/contracts.py`, `keys.py`): HMAC-SHA256 over canonical JSON (signature excluded), 7-day TTL, `required_approvals()` from policy, immutable parent + signed child on `add_approval`.
- **Audit chain** (`app/audit/chain.py`): SQLite WAL append-only log with chained SHA-256; genesis `prev_hash` is **empty string** `""` (not zero-hex, so the first link is visibly distinct from a real hash).
- **Eval assets**: byte copies under `vendor/meterless/`; synthetic `data/evals/injection_domain.jsonl` (44 rows); `python run.py guard-eval`.
- **Tests**: P2-T40–P2-T48 (`@pytest.mark.p2d`).

## Guard-eval table (`--no-model`)

| Set | Precision | Recall | F1 | TP | FP | TN | FN |
|---|---:|---:|---:|---:|---:|---:|---:|
| scout | 1.000 | 1.000 | 1.000 | 7 | 0 | 3 | 0 |
| domain | 1.000 | 1.000 | 1.000 | 22 | 0 | 22 | 0 |

Benign look-alikes that **pass** (deterministic): e.g. `dom-023` (“ignore previous versions of the policy once superseded”), `dom-024` (ignore typos in formatting), `dom-038` / `dom-039` (ignore spreadsheet tabs / disregard outdated draft clauses).

## Deviations

- Contract TTL **7 days** (Scout default minutes) — documented in `app/actions/contracts.py` module docstring and here.
- `GuardFlag` has no `evidence_meta` field; detector meta stays in Python logging only (per plan approval).
- Ambiguous-band **live** generator test skipped until P2-B; mocked tests cover model vs offline paths.

## Known gaps

- P2-B `generator.generate` still raises `OfflineProvider` in production; guard uses it only when online (ambiguous band).
- `executor.py` / API contract routes remain P3/P4-B.

## Commands

```bash
python scripts/tasks.py verify-pass --pass 2d
python run.py guard-eval --set all --no-model
```

## Explain it

1. **Blocked segment:** `guard` returns `level=block`; upstream records `GuardFlag`s; policy rule `injection_blocked` forces **ESCALATE** with `UNTRUSTED_CONTENT_TAMPERING`.
2. **Metadata-only logging:** Scout spec / integrity — untrusted text must not enter logs or traces (PII and injection payloads stay out of observability stores).
3. **Re-issue on approval:** Signature covers the full contract; mutating approvals would invalidate integrity — child contract with `parent_id` preserves audit trail.
4. **Tampered audit row:** `verify()` recomputes hashes from genesis `prev_hash=""`; first mismatch returns failing `seq`.
5. **Precision vs recall:** Precision = blocked predictions that were true injections; recall = injections caught. Benign look-alikes drive precision — false blocks on legitimate TPRM wording are costly.
