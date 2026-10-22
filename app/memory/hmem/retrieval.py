"""Hybrid retrieval and reinjection (port of `reference/src/memoryRetrieval.ts`).

    raw   = 0.35*semantic + 0.20*keyword + 0.10*tag + 0.10*domain
          + 0.15*entity   + 0.05*layer   + 0.05*recency - 0.20*superseded
    score = clamp01(raw) * confidence          <- confidence multiplies AFTER the sum

keyword = Jaccard of the top-8 query tokens vs memory tokens. Layer weights: long_term 1.0,
working 0.8, short_term 0.6. Recency: exponential decay on lastAccessed, 14-day constant.
Superseded records are penalised, never deleted or filtered. The threshold (0.35) applies to
the FINAL score; top N = 5.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from app.errors import NotFound, ValidationFailed
from app.memory.hmem.embeddings import cosine, embed, jaccard, tokenize
from app.memory.hmem.jsfmt import assert_ascii_id, clamp01, js_sort_entries, to_fixed
from app.memory.hmem.ledger import TrustLedgerService
from app.memory.hmem.store import MemoryStoreService, snapshot
from app.memory.hmem.types import (
    DAY_MS,
    DEFAULTS,
    FEEDBACK_DELTAS,
    FeedbackKind,
    MemoryRecord,
    QueryResult,
    QueryTrace,
    RetrievedMemory,
)

LAYER_WEIGHT: dict[str, float] = {"long_term": 1.0, "working": 0.8, "short_term": 0.6}
_LAYER_MARKER = {"long_term": "LT", "working": "WK", "short_term": "ST"}


class MemoryRetrievalService:
    def __init__(
        self,
        store: MemoryStoreService,
        ledger: TrustLedgerService,
        clock: Callable[[], int],
        actor: str,
    ) -> None:
        self._store = store
        self._ledger = ledger
        self._clock = clock
        self._actor = actor

    def score_one(self, memory: MemoryRecord, query: str) -> float:
        return self._score(
            memory,
            embed(query),
            tokenize(query)[:8],
            self._store.extract_entities(query),
            self._store.classify_domain(query, [], "general"),
        )

    def _score(
        self,
        m: MemoryRecord,
        query_embedding: list[float],
        query_tokens: list[str],
        query_entities: list[str],
        query_domain: str,
    ) -> float:
        semantic = clamp01(cosine(query_embedding, m.embedding))
        keyword = jaccard(query_tokens, tokenize(m.content))
        tag = jaccard(query_tokens, [t.lower() for t in m.tags])
        domain = 1 if m.domain == query_domain else 0
        entity = jaccard(query_entities, m.entities)
        layer = LAYER_WEIGHT[m.layer]
        age_days = (self._clock() - m.last_accessed) / DAY_MS
        recency = math.exp(-age_days / DEFAULTS.recency_days)
        superseded = 1 if m.superseded_by else 0
        raw = (
            0.35 * semantic + 0.2 * keyword + 0.1 * tag + 0.1 * domain
            + 0.15 * entity + 0.05 * layer + 0.05 * recency - 0.2 * superseded
        )  # fmt: skip
        return clamp01(raw) * m.confidence

    def query(
        self,
        query: str,
        *,
        top_n: int | None = None,
        threshold: float | None = None,
        chat_id: str | None = None,
    ) -> QueryResult:
        query_embedding = embed(query)
        query_tokens = tokenize(query)[:8]
        query_entities = self._store.extract_entities(query)
        query_domain = self._store.classify_domain(query, [], "general")
        threshold = threshold if threshold is not None else DEFAULTS.retrieval_threshold
        top_n = top_n if top_n is not None else DEFAULTS.retrieval_top_n

        scored: list[RetrievedMemory] = []
        for m in self._store.all():
            if chat_id and m.chat_id and m.chat_id != chat_id:
                continue
            s = self._score(m, query_embedding, query_tokens, query_entities, query_domain)
            if s >= threshold:
                scored.append(RetrievedMemory(memory=m, relevance=s))
        scored.sort(key=lambda r: (-r.relevance, assert_ascii_id(r.memory.id)))
        top = scored[:top_n]

        for item in top:
            self._store.touch(item.memory.id)
            self._ledger.log(item.memory.id, "read", self._actor, details={"query": query})

        if len(top) <= 1:
            strategy = "minimal"
        elif any(t.memory.type in ("personal", "preference") for t in top):
            strategy = "personal"
        else:
            strategy = "comprehensive"
        return QueryResult(
            memories=top,
            context=self.format_reinjection(top),
            trace=QueryTrace(
                retrieval_reason=f'hybrid ranking for "{query}" (domain: {query_domain})',
                strategy=strategy,
                scores={t.memory.id: to_fixed(t.relevance, 4) for t in top},
            ),
        )

    def format_reinjection(self, items: list[RetrievedMemory]) -> str:
        """Domain-grouped reinjection blocks with layer markers and entities (section 6.2)."""
        if not items:
            return ""
        by_domain: dict[str, list[RetrievedMemory]] = {}
        for it in items:
            by_domain.setdefault(it.memory.domain, []).append(it)
        lines = ["[MEMORY CONTEXT]"]
        for domain, group in js_sort_entries(list(by_domain.items())):
            lines.append(f"## {domain}")
            for it in group:
                m = it.memory
                ents = f" (entities: {', '.join(m.entities)})" if m.entities else ""
                lines.append(f"- [{_LAYER_MARKER[m.layer]}] {m.content}{ents} <{m.id}>")
        lines.append("[/MEMORY CONTEXT]")
        return "\n".join(lines)

    def feedback(self, memory_id: str, kind: FeedbackKind) -> None:
        """Exact feedback deltas (H-MEM AGENTS.md section 9.2)."""
        if kind not in FEEDBACK_DELTAS:
            raise ValidationFailed(f"H-MEM: unknown feedback kind {kind!r}")
        m = self._store.get(memory_id)
        if m is None:
            raise NotFound(f"H-MEM: unknown memory id {memory_id}")
        prev = snapshot(m)
        if kind == "helpful":
            m.access_count += 1
        m.confidence = clamp01(m.confidence + FEEDBACK_DELTAS[kind])
        if kind == "wrong" and "review" not in m.tags:
            m.tags.append("review")
        self._ledger.log(
            memory_id,
            "feedback",
            self._actor,
            previous_state=prev,
            new_state=snapshot(m),
            details={"kind": kind, "delta": FEEDBACK_DELTAS[kind]},
        )
        self._store.persist()
