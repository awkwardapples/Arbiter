# P4-B report — SQLite case store, approvals, replay, read API

## Built

Cases, contracts, reviews and human decisions persist in SQLite at `{root}/arbiter.db` (WAL). `Store` keeps the methods P3 and P4-A already call. `get()` round-trips the bundle, including any key P3 saved that `CaseBundle` does not declare (`extra="allow"`, stored in `bundle_json`). A one-shot import reads `var/cases/*.json`, `var/contracts/*.json` and `var/reviews/*.json` when those tables are empty.

Replay loads the stored decision, the policy file for its major version, and the named calibration. It re-runs `decide(record.policy_inputs, …)`, reapplies each stored `escalation_reasons` entry with `force_escalate`, and checks three things: the policy-model hash, the record hash, and every contract signature at `issued_at`.

`GET /cases` is the queue. `POST /contracts/{id}/approve` records a signed child contract. When the role satisfies the policy, the existing executor writes the outbox. `GET /audit/verify` recomputes the hash chain. `python run.py replay` and `python run.py audit-verify` call the same code.

The image is `python:3.12-slim`, dependencies installed at build, non-root, healthcheck via urllib. Compose runs `api`, `ui` and optional `sources`. CI job `docker` runs `docker build -t arbiter .` from the repo Dockerfile (no `docker pull`) and posts the six input examples with `SAMPLE_MODE=true` and no env file.

### Replay sample

Offline run of `input_examples/example_1.json` (case `CASE-0003`, outcome `APPROVE`):

```json
{
  "match": true,
  "diff": [],
  "checks": {
    "policy_hash": true,
    "record_hash": true,
    "contract_signatures": true
  }
}
```

### Approval flow (example 5, DECLINE)

1. The run stores one contract in `pending_approval`. `approvals.DECLINE` in `policy/arbiter_policy.v1.yaml` requires `tprm_lead`.
2. `POST /contracts/{id}/approve` as `tprm_analyst` returns 403. The body names `tprm_lead`. Nothing is written to the outbox.
3. The same call as `tprm_lead` calls `contracts.add_approval`, which signs a child contract, then `executor.execute`. The child is `executed` and `var/outbox/procurement/<contract_id>.json` exists. The audit chain gets `contract_issued` and `action_executed`.
4. The same parent, with the route clock moved past `expires_at`, returns 409 and the message `expired`.

## Deviations

- **`bundle_json` column.** Approved. The pass listed projection columns; the P3 bundle also has `input`, `first_decision`, `contract_ids`, `artifacts`, `limitations` and `log_file`. Those, plus any unknown key, live in `bundle_json`. `get()` returns them.
- **`HealthResponse` additive fields** (`data`, `provider`, `hmem_records`, `audit_chain_length`). Approved. The route's `response_model` would otherwise drop them. Reason: `/health` has to report backend, provider and chain length without a second schema.
- **`.github/workflows/ci.yml` docker job.** Approved. Reason: the sample-mode smoke is the judge path and has to build this repo's Dockerfile.
- **`output_examples/` waiver.** Approved. Absent directory passes with `waiver: output_examples/ absent until P6`. A present directory with fewer than three files fails with `output_examples/ exists but has fewer than 3 files; P6 populates this directory.`
- **`run.py assess` is still the P3 stub** (stated in `docs/passes/P3_REPORT.md`). Clean-clone step 7 runs `orchestrator.run` in a fresh venv and records that waiver. This lane does not own `app/cli/run_case.py`.
- **`git clone --no-local`.** `git clone --local` hardlinks objects and fails on this WSL layout (`/tmp` and the checkout are different mounts).
- **History scan.** The tree scan is `scripts/scan_secrets.py` (allowlist and placeholders). `git log -p` is checked for the high-signal patterns only. The assignment regex matches prose such as `token = re.compile` in docs, so it stays on the tree scan.
- **Trace check.** Every container trace is schema-checked. Collaboration is required for `trace-run-*`. `trace-zetaris-status.jsonl` is the `/health` probe, not an agent run.
- **`Store.get_contract`.** Additive. The approve route has a contract id and no case id. Existing methods are unchanged.
- **Queue sort vs `Store.list("risk")`.** The HTTP queue sorts residual risk descending, then `created_at` ascending. `list("risk")` keeps the P3 key (outcome severity, then residual risk, then case id) so P4-A sees the same method.

## Known gaps

- Local Docker smoke (`P4-T17` container run) is skipped unless `ARBITER_DOCKER_TESTS=1`. The CI `docker` job is the authoritative build. `P4-T18` runs when `docker` is on `PATH` and `DOCKER` is not `0`.
- `run.py assess` still exits as the P3 stub. Judges who follow the playbook's native command hit that stub; `POST /run` and `orchestrator.run` are the working paths.
- H-MEM record count is null until P4-A defines `app.memory.keeper.count`.
- UI service in compose starts the P5-A stub.

## Commands

```
python scripts/tasks.py verify-pass --pass 4b
```

Green. Marker tests: 17 passed, 1 skipped (`P4-T17` container smoke). Regression: 559 passed, 3 skipped, 8 deselected (`not live`). Secret scan and hardcode check passed. `P4-T18` passed on this machine (about 90s): image build, six examples, traces, novel input, secret scan, fresh venv.

Evidence: `docs/passes/clean-clone-2026-10-22.md`.

## Explain it

1. **What replay recomputes, and what fails it.** It recomputes `decide` on the stored `policy_inputs`, then `force_escalate` for each stored escalation reason. It fails if the loaded policy's model hash differs from `policy_sha256`, if the recomputed record hash or the hash of the stored content differs from `record_sha256`, if any contract signature fails at `issued_at`, or if a stored fact value or the outcome differs from the recomputation. A tampered fact is listed as `facts.<key>`.
2. **Why approval creates a child.** A signed contract is immutable. `add_approval` copies it, appends the approval, gives the copy a new id and `parent_id`, and signs that copy. The parent stays as it was issued.
3. **Who can approve a DECLINE.** `tprm_lead`. The rule is `approvals.DECLINE: [tprm_lead]` in `policy/arbiter_policy.v1.yaml`. Rank is `roles` in the same file: a higher rank satisfies a lower requirement, so an analyst does not satisfy a lead. The route returns 403 and names the required role.
4. **How the queue is ordered.** `GET /cases` sorts residual risk descending, then `created_at` ascending, so the riskiest case is first and two equal risks keep the earlier one first. The badge text is the outcome word (`APPROVE`, `DECLINE`, and the others), not a colour.
5. **What `/audit/verify` proves.** It recomputes every row's hash from the previous hash and the canonical event. `ok: true` means the chain is intact from the genesis row. A tampered row returns `ok: false` and `first_bad_seq`, the first sequence whose stored hash or `prev_hash` does not match.
