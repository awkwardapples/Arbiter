# Meterless H-MEM: third-party notice

Arbiter's `app/memory/hmem/` is a Python port of the **Meterless H-MEM reference implementation**, ported to Python by Arbiter. The conformance test vectors are copied unchanged.

- Source repository: https://github.com/Meterless/Meterless (`engines/hmem/`)
- Commit: `1742dec56a66e58eef9dda2d2b865823758ca8cd` (2026-10-19)
- Licence: Apache License 2.0. The full text is in [`LICENSE`](LICENSE) (copied from `engines/hmem/LICENSE`).
- Copyright: the Meterless authors. Modifications (the Python port) by the Arbiter team.

## Files copied verbatim

| File here | Upstream path | sha256 |
|---|---|---|
| `hmem_vectors.json` | `engines/hmem/conformance/vectors/vectors.json` | `10afb5a07233466576ba6feb0d88408488909ba2721ee9157fdb932132917029` |
| `LICENSE` | `engines/hmem/LICENSE` | `63e29fc8231b53757a77fbc371071c91d768621efa1e68b1d9ff8d1bb7c4a0ef` |

## Files ported (not copied)

| Arbiter file | Upstream file | Upstream sha256 |
|---|---|---|
| `app/memory/hmem/types.py` | `reference/src/types.ts` | `becb504870a67646a20a421ffe04d8732db63418393423d2186c074b182f54c7` |
| `app/memory/hmem/embeddings.py` | `reference/src/embeddings.ts` | `89433327ee1075a8049bc8518cdf5cabf51ad67802e192266841cdee727b6d10` |
| `app/memory/hmem/store.py` | `reference/src/memoryStore.ts` | `a1eac8de8c0fde0e503e1212f3cb98295a661c2a8bad93ad82e51985885e6fd0` |
| `app/memory/hmem/ledger.py` | `reference/src/trustLedger.ts` | `263253dd3342c488ce773d7e728d77aec983c1833873602b59ce1a6c7999e20e` |
| `app/memory/hmem/mining.py` | `reference/src/memoryMining.ts` | `6072693d654ea1c34a9adbf6ce80101eeb1eeb56273d264f6ceb4859ffde6562` |
| `app/memory/hmem/retrieval.py` | `reference/src/memoryRetrieval.ts` | `4fe120b1b64fe7225b9b28fda59514c114de9e885d22c5bf0aa035788b6d629d` |
| `app/memory/hmem/conflicts.py` | `reference/src/conflictDetection.ts` | `432e8b86ed0b5883d435e5ab4a12160d1f40d194cbdb4c119d3b710cbb0301a3` |
| `app/memory/hmem/sleep.py` | `reference/src/sleepCycle.ts` | `3ce0d4f3233d0ad7c133a2cbaf39b6122467022e0aa378a160a0d463e2264cef` |
| `app/memory/hmem/dreaming.py` | `reference/src/dreaming.ts` | `d12594d667ec068690c6b81e020cd62ade91671316a1ab9b529259304aceb009` |
| `app/memory/hmem/__init__.py` | `reference/src/index.ts` | `9c481889afcdd70086d3bb3470842fa2330215e4d7760d826d103accdf8c1cdf` |
| `tests/conformance/test_hmem_conformance.py` | `conformance/runner.ts` | `d6724860761c4846a0bce3080d25115bcb0ba1d9d0d2e933438f5683a7a9b7c5` |
| `app/memory/hmem/jsfmt.py` | – | (Arbiter-only: JavaScript number, string and sort semantics) |

## Additions made by Arbiter (not upstream)

- Optional `agentId`, `runId` and `taskId` fields on `MemoryRecord` (from the hackathon "Meterless H-MEM Agent Engine" doc). Unused by the engine's logic.
- Optional `ledger_mirror` path on `HMEM(...)` and `TrustLedgerService(...)`: an append-only JSONL copy of every ledger entry.
- Errors are raised as `app.errors.ValidationFailed` / `app.errors.NotFound` instead of a plain `Error`.
- An async `amine` / `amine_interaction` / `amine_document` alongside the synchronous mining methods.

## Name mapping (TypeScript → Python)

Serialised JSON (`state.json`, ledger lines, snapshots) keeps the TypeScript camelCase keys; Python attributes use snake_case.

| TypeScript | Python |
|---|---|
| `MemoryStoreService` / `TrustLedgerService` / `MemoryMiningService` / `MemoryRetrievalService` / `ConflictDetectionService` / `SleepCycleService` / `DreamingService` | same class names |
| `HMEMOptions.persistDir` / `.minerFn` | `persist_dir` / `miner_fn` |
| `lastAccessed`, `accessCount`, `chatId`, `missionId`, `goalRunId`, `relatedTo`, `supersededBy`, `derivedFrom`, `learnedAt` | `last_accessed`, `access_count`, `chat_id`, `mission_id`, `goal_run_id`, `related_to`, `superseded_by`, `derived_from`, `learned_at` |
| `LedgerEntry.memoryId` / `previousState` / `newState` | `memory_id` / `previous_state` / `new_state` |
| `SleepPreview.toConsolidate` / `toArchive` / `toSynthesize` | `to_consolidate` / `to_archive` / `to_synthesize` |
| `SleepReport.backupId` / `actionLog` | `backup_id` / `action_log` |
| `ConflictRecord.memoryA` / `memoryB` | `memory_a` / `memory_b` |
| `DreamProposal.suggestedDomain` | `suggested_domain` |
| `QueryResult.trace.retrievalReason` | `trace.retrieval_reason` (serialised `retrievalReason`) |
| `store.classifyDomain` / `extractEntities` / `restoreAll` / `snapshotAll` | `classify_domain` / `extract_entities` / `restore_all` / `snapshot_all` |
| `mining.mineInteraction` / `mineDocument` / `mineModelFree` | `mine_interaction` / `mine_document` / `mine_model_free` |
| `parseStrictJsonArray` | `parse_strict_json_array` |
| `retrieval.scoreOne` / `formatReinjection` | `score_one` / `format_reinjection` |
| `conflicts.autoResolve` | `auto_resolve` |
| `query(q, { topN, threshold, chatId })` | `query(q, top_n=…, threshold=…, chat_id=…)` |
| `FEEDBACK_DELTAS`, `DEFAULTS`, `DAY_MS`, `clamp01` | same names (`DEFAULTS` fields snake_case, e.g. `retrieval_top_n`) |
