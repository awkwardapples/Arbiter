"""Conflict detection and resolution (port of `reference/src/conflictDetection.ts`).

The losing record is marked supersededBy (kept, penalised in ranking), never deleted.
Auto-resolve only at decision confidence >= 0.70; everything else queues.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Literal

from app.errors import NotFound
from app.memory.hmem.embeddings import cosine
from app.memory.hmem.jsfmt import clamp01, js_len, to_fixed
from app.memory.hmem.ledger import TrustLedgerService
from app.memory.hmem.store import MemoryStoreService, snapshot
from app.memory.hmem.types import DEFAULTS, ConflictRecord, MemoryRecord

_FLAGS = re.IGNORECASE | re.ASCII
# Ported verbatim, including the alternation precedence in `\bavoid[s]?|dislike[s]?\b`.
OPPOSING_PAIRS: list[tuple[re.Pattern[str], re.Pattern[str]]] = [
    (re.compile(r"\balways\b", _FLAGS), re.compile(r"\bnever\b", _FLAGS)),
    (re.compile(r"\benable[ds]?\b", _FLAGS), re.compile(r"\bdisable[ds]?\b", _FLAGS)),
    (re.compile(r"\bprefer[s]?\b", _FLAGS), re.compile(r"\bavoid[s]?|dislike[s]?\b", _FLAGS)),
    (re.compile(r"\bon\b", _FLAGS), re.compile(r"\boff\b", _FLAGS)),
    (re.compile(r"\byes\b", _FLAGS), re.compile(r"\bno\b", _FLAGS)),
]
_NUMBER = re.compile(r"\d+(\.\d+)?", re.ASCII)


def _numbers(text: str) -> list[str]:
    return [m.group(0) for m in _NUMBER.finditer(text)]


class ConflictDetectionService:
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
        self._conflicts: list[ConflictRecord] = []
        self._seq = 0

    def scan(self) -> list[ConflictRecord]:
        found: list[ConflictRecord] = []
        records = self._store.all()
        for i in range(len(records)):
            for j in range(i + 1, len(records)):
                conflict = self._check(records[i], records[j])
                if conflict is not None:
                    found.append(conflict)
                    self._conflicts.append(conflict)
                    self._ledger.log(
                        conflict.memory_a,
                        "conflict_detected",
                        self._actor,
                        details={
                            "with": conflict.memory_b,
                            "reason": conflict.reason,
                            "confidence": conflict.confidence,
                        },
                    )
        return found

    def _check(self, a: MemoryRecord, b: MemoryRecord) -> ConflictRecord | None:
        # A supersedes relation suppresses conflict: it is an intended replacement.
        if a.supersedes == b.id or b.supersedes == a.id or a.superseded_by == b.id or b.superseded_by == a.id:
            return None

        sim = cosine(a.embedding, b.embedding)
        reason = ""
        confidence = 0.0
        for p, q in OPPOSING_PAIRS:
            opposed = (p.search(a.content) and q.search(b.content)) or (
                q.search(a.content) and p.search(b.content)
            )
            if opposed and sim > 0.5:
                reason = "opposing phrase pair on similar content"
                confidence = 0.5 + 0.3 * sim
        if not reason and sim > 0.8:
            nums_a, nums_b = _numbers(a.content), _numbers(b.content)
            if nums_a and nums_b and ",".join(nums_a) != ",".join(nums_b):
                reason = "high-similarity conflicting numeric values"
                confidence = 0.55 + 0.25 * sim
        if not reason:
            return None

        # Confidence modifiers (section 10.1).
        if any(e in b.entities for e in a.entities):
            confidence += 0.1
        if a.domain == b.domain:
            confidence += 0.05
        if b.id in a.related_to:
            confidence -= 0.1  # explicit relation lowers false positives

        self._seq += 1
        return ConflictRecord(
            id=f"conflict-{self._seq}",
            memory_a=a.id,
            memory_b=b.id,
            reason=reason,
            confidence=clamp01(confidence),
            resolved=False,
        )

    def auto_resolve(self, conflict: ConflictRecord) -> Literal["resolved", "queued"]:
        """Weighted auto-decision heuristics (section 10.2)."""
        a = self._store.get(conflict.memory_a)
        b = self._store.get(conflict.memory_b)
        if a is None or b is None:
            raise NotFound(f"H-MEM: conflict {conflict.id} refers to a missing memory")

        def score_of(m: MemoryRecord) -> float:
            return (
                0.3 * (m.last_accessed / max(1, self._clock()))
                + 0.2 * min(1, m.access_count / 10)
                + 0.25 * m.confidence
                + 0.1 * min(1, js_len(m.content) / 200)
                + 0.15 * (1 if m.provenance.origin == "user_correction" else 0.5)
            )

        sa, sb = score_of(a), score_of(b)
        margin = abs(sa - sb) / max(sa, sb)
        decision_confidence = clamp01(conflict.confidence * 0.6 + margin * 0.8)
        if decision_confidence < DEFAULTS.conflict_auto_resolve_gate:
            return "queued"

        winner, loser = (a, b) if sa >= sb else (b, a)
        prev = snapshot(loser)
        loser.superseded_by = winner.id  # kept and penalised, never deleted
        conflict.resolved = True
        conflict.resolution = "keep_a" if winner.id == conflict.memory_a else "keep_b"
        self._ledger.log(
            loser.id,
            "conflict_resolved",
            self._actor,
            previous_state=prev,
            new_state=snapshot(loser),
            details={
                "conflictId": conflict.id,
                "winner": winner.id,
                "decisionConfidence": to_fixed(decision_confidence, 3),
            },
        )
        self._store.persist()
        return "resolved"

    def queue(self) -> list[ConflictRecord]:
        return [c for c in self._conflicts if not c.resolved]
