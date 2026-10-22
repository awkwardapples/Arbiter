"""Meterless H-MEM, Python port (facade; port of `reference/src/index.ts`).

Deterministic, dependency-free, in-memory with optional JSON persistence. Passes the
engine's own conformance vectors (`tests/conformance/test_hmem_conformance.py`).
Provenance and licence: `vendor/meterless/NOTICE.md`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.memory.hmem.conflicts import ConflictDetectionService
from app.memory.hmem.dreaming import DreamingService
from app.memory.hmem.embeddings import cosine, embed, jaccard, tokenize
from app.memory.hmem.ledger import TrustLedgerService
from app.memory.hmem.mining import MemoryMiningService, MinerFn, parse_strict_json_array
from app.memory.hmem.retrieval import MemoryRetrievalService
from app.memory.hmem.sleep import SleepCycleService
from app.memory.hmem.store import MemoryStoreService
from app.memory.hmem.types import (
    DAY_MS,
    DEFAULTS,
    FEEDBACK_DELTAS,
    ConflictRecord,
    DreamProposal,
    FeedbackKind,
    LedgerEntry,
    MemoryRecord,
    MiningEventType,
    Provenance,
    QueryResult,
    RetrievedMemory,
    SleepPreview,
    SleepReport,
    clamp01,
    now_ms,
)

__all__ = [
    "DAY_MS",
    "DEFAULTS",
    "FEEDBACK_DELTAS",
    "HMEM",
    "ConflictDetectionService",
    "ConflictRecord",
    "DreamProposal",
    "DreamingService",
    "LedgerEntry",
    "MemoryMiningService",
    "MemoryRecord",
    "MemoryRetrievalService",
    "MemoryStoreService",
    "Provenance",
    "QueryResult",
    "RetrievedMemory",
    "SleepCycleService",
    "SleepPreview",
    "SleepReport",
    "TrustLedgerService",
    "clamp01",
    "cosine",
    "embed",
    "jaccard",
    "now_ms",
    "parse_strict_json_array",
    "tokenize",
]


class HMEM:
    def __init__(
        self,
        clock: Callable[[], int] = now_ms,
        actor: str = "system",
        persist_dir: str | Path | None = None,
        miner_fn: MinerFn | None = None,
        ledger_mirror: str | Path | None = None,
    ) -> None:
        self.clock = clock
        self.ledger = TrustLedgerService(clock, persist_dir, ledger_mirror)
        self.store = MemoryStoreService(clock, self.ledger, actor, persist_dir)
        self.mining = MemoryMiningService(self.store, clock, miner_fn)
        self.retrieval = MemoryRetrievalService(self.store, self.ledger, clock, actor)
        self.conflicts = ConflictDetectionService(self.store, self.ledger, clock, actor)
        self.sleep = SleepCycleService(self.store, self.ledger, clock, actor)
        self.dreaming = DreamingService(self.store, self.ledger, clock, actor)

    def add(self, content: str, *, source: str | None, **fields: Any) -> MemoryRecord:
        return self.store.add(content, source=source, **fields)

    def mine(self, event: MiningEventType, text: str, *, chat_id: str | None = None) -> list[MemoryRecord]:
        return self.mining.mine_interaction(event, text, chat_id=chat_id)

    async def amine(
        self, event: MiningEventType, text: str, *, chat_id: str | None = None
    ) -> list[MemoryRecord]:
        return await self.mining.amine_interaction(event, text, chat_id=chat_id)

    def query(
        self, q: str, top_n: int = DEFAULTS.retrieval_top_n, threshold: float = DEFAULTS.retrieval_threshold,
        chat_id: str | None = None,
    ) -> QueryResult:  # fmt: skip
        return self.retrieval.query(q, top_n=top_n, threshold=threshold, chat_id=chat_id)

    def feedback(self, memory_id: str, kind: FeedbackKind) -> None:
        self.retrieval.feedback(memory_id, kind)
