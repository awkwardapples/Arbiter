"""Canonical H-MEM shapes (port of `reference/src/types.ts`).

Python attributes are snake_case; serialised JSON keeps the reference's camelCase keys,
so `state.json` and ledger lines round-trip with files the TypeScript engine wrote.
Models are mutable and shared by reference, like the reference's plain objects.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.memory.hmem.jsfmt import clamp01

__all__ = [
    "DAY_MS",
    "DEFAULTS",
    "FEEDBACK_DELTAS",
    "ConflictRecord",
    "DreamProposal",
    "FeedbackKind",
    "LedgerAction",
    "LedgerEntry",
    "MemoryLayer",
    "MemoryRecord",
    "MemoryType",
    "MiningEventType",
    "Provenance",
    "ProvenanceOrigin",
    "QueryResult",
    "QueryTrace",
    "RetrievedMemory",
    "SleepPreview",
    "SleepReport",
    "clamp01",
    "now_ms",
]

MemoryType = Literal["personal", "factual", "preference", "general"]
MemoryLayer = Literal["short_term", "working", "long_term"]
ProvenanceOrigin = Literal[
    "chat_message", "user_correction", "file_save", "file_open", "file_edit",
    "model_response", "plan_completion", "document", "manual", "dream", "sleep_synthesis",
]  # fmt: skip
LedgerAction = Literal[
    "create", "read", "update", "delete", "feedback", "promote", "demote", "merge",
    "conflict_detected", "conflict_resolved",
    "sleep_consolidate", "sleep_archive", "sleep_synthesize",
    "dream_proposed", "dream_approved", "dream_rejected", "restore",
]  # fmt: skip
MiningEventType = Literal[
    "chat_message", "user_correction", "file_save", "file_open", "file_edit",
    "model_response", "plan_completion",
]  # fmt: skip
DreamProposalType = Literal["insight", "domain", "invariant"]
FeedbackKind = Literal["helpful", "not_helpful", "wrong"]
Resolution = Literal["keep_a", "keep_b", "keep_both", "merge", "delete_both"]


class _Model(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True, validate_by_alias=True)

    def to_json(self) -> dict[str, Any]:
        """The reference's JSON shape: camelCase keys, `undefined` (None) fields dropped."""
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


class Provenance(_Model):
    origin: ProvenanceOrigin
    learned_at: int
    label: str
    refs: list[str] | None = None


class MemoryRecord(_Model):
    id: str
    content: str
    type: MemoryType
    layer: MemoryLayer
    timestamp: int
    last_accessed: int
    access_count: int
    tags: list[str]
    embedding: list[float]
    score: float | None = None
    confidence: float
    source: str
    provenance: Provenance
    chat_id: str | None = None
    mission_id: str | None = None
    goal_run_id: str | None = None
    domain: str
    namespace: str
    entities: list[str]
    related_to: list[str]
    supersedes: str | None = None
    superseded_by: str | None = None
    derived_from: list[str] | None = None
    # Arbiter addition (hackathon H-MEM Agent Engine fields); the engine never reads them.
    agent_id: str | None = None
    run_id: str | None = None
    task_id: str | None = None


class LedgerEntry(_Model):
    memory_id: str
    action: LedgerAction
    actor: str
    timestamp: int
    previous_state: dict[str, Any] | None = None
    new_state: dict[str, Any] | None = None
    details: dict[str, Any] | None = None


class DreamProposal(_Model):
    id: str
    type: DreamProposalType
    content: str
    derived_from: list[str]
    suggested_domain: str | None = None
    status: Literal["proposed", "approved", "rejected"]


class SleepPreview(_Model):
    to_consolidate: list[str]
    to_archive: list[str]
    to_synthesize: list[list[str]]


class SleepReport(_Model):
    backup_id: str
    consolidated: int
    archived: int
    synthesized: int
    action_log: list[str]


class ConflictRecord(_Model):
    id: str
    memory_a: str
    memory_b: str
    reason: str
    confidence: float
    resolved: bool
    resolution: Resolution | None = None


class RetrievedMemory(_Model):
    memory: MemoryRecord
    relevance: float


class QueryTrace(_Model):
    retrieval_reason: str
    strategy: Literal["minimal", "personal", "comprehensive"]
    scores: dict[str, float]


class QueryResult(_Model):
    memories: list[RetrievedMemory]
    context: str
    trace: QueryTrace


FEEDBACK_DELTAS: dict[str, float] = {"helpful": 0.05, "not_helpful": -0.03, "wrong": -0.2}


@dataclass(frozen=True, slots=True)
class _Defaults:
    retrieval_top_n: int = 5
    retrieval_threshold: float = 0.35  # on the final score, after the confidence multiplier
    consolidation_days: int = 7
    archive_min_days: int = 30
    archive_max_access: int = 2
    synthesis_cosine: float = 0.82
    dream_cluster_min_size: int = 2
    dream_relatedness: float = 0.35
    max_dream_proposals_per_type: int = 8
    conflict_auto_resolve_gate: float = 0.7
    entity_cap: int = 10
    related_cap: int = 5
    recency_days: int = 14


DEFAULTS = _Defaults()
DAY_MS = 24 * 60 * 60 * 1000


def now_ms() -> int:
    """`Date.now()`."""
    return time.time_ns() // 1_000_000
