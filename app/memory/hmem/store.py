"""Tiered memory store with enrichment (port of `reference/src/memoryStore.ts`).

A record with no source is rejected by construction. Enrichment runs on every add: domain
classification, namespace, entity extraction (cap 10), relatedTo discovery (cap 5,
bidirectional) and supersedes detection.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple

from app.errors import NotFound, ValidationFailed
from app.memory.hmem.embeddings import cosine, embed, tokenize
from app.memory.hmem.jsfmt import assert_ascii_id, clamp01, js_json_dumps, js_json_loads, js_trim
from app.memory.hmem.ledger import TrustLedgerService
from app.memory.hmem.types import DEFAULTS, MemoryLayer, MemoryRecord, MemoryType, Provenance

TECH_TERMS = [
    "react", "python", "typescript", "javascript", "rust", "sqlite", "postgres", "indexeddb",
    "node", "docker", "graphql", "redis", "webrtc", "tauri", "electron", "llm", "embedding",
]  # fmt: skip
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "tech": ["code", "bug", "api", "database", "deploy", "framework", "library", "server", *TECH_TERMS],
    "work": ["meeting", "deadline", "client", "project", "sprint", "review", "report"],
    "personal": ["family", "hobby", "prefer", "like", "dislike", "morning", "evening"],
}
_ENTITY = re.compile(r"\b([A-Z][a-zA-Z]{2,})\b", re.ASCII)
_ENTITY_STOPWORDS = ("the", "this", "that", "with")
_CORRECTION = re.compile(
    r"\b(actually|instead|no longer|not anymore|changed to|correction)\b", re.IGNORECASE | re.ASCII
)


class StoreSnapshot(NamedTuple):
    records: list[MemoryRecord]
    seq: int


def snapshot(r: MemoryRecord) -> dict[str, Any]:
    """A detached copy of the record for ledger entries, without the embedding."""
    out = r.to_json()
    out.pop("embedding", None)
    return out


class MemoryStoreService:
    def __init__(
        self,
        clock: Callable[[], int],
        ledger: TrustLedgerService,
        actor: str,
        persist_dir: str | Path | None = None,
    ) -> None:
        self._clock = clock
        self._ledger = ledger
        self._actor = actor
        self._records: dict[str, MemoryRecord] = {}
        self._seq = 0
        self._state_file: Path | None = None
        if persist_dir is not None:
            Path(persist_dir).mkdir(parents=True, exist_ok=True)
            self._state_file = Path(persist_dir) / "state.json"
            if self._state_file.exists():
                saved = js_json_loads(self._state_file.read_text(encoding="utf-8"))
                self._seq = int(saved["seq"])
                for raw in saved["records"]:
                    rec = MemoryRecord.model_validate(raw)
                    self._records[rec.id] = rec

    def persist(self) -> None:
        if self._state_file is None:
            return
        records = sorted(self._records.values(), key=lambda r: assert_ascii_id(r.id))
        text = js_json_dumps({"seq": self._seq, "records": [r.to_json() for r in records]}, indent=2) + "\n"
        tmp = self._state_file.with_name(self._state_file.name + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, self._state_file)

    def add(
        self,
        content: str,
        *,
        source: str | None,
        type: MemoryType | None = None,
        layer: MemoryLayer | None = None,
        tags: list[str] | None = None,
        confidence: float | None = None,
        provenance: Provenance | dict[str, Any] | None = None,
        chat_id: str | None = None,
        mission_id: str | None = None,
        goal_run_id: str | None = None,
        supersedes: str | None = None,
        derived_from: list[str] | None = None,
        agent_id: str | None = None,
        run_id: str | None = None,
        task_id: str | None = None,
    ) -> MemoryRecord:
        if not source or js_trim(source) == "":
            raise ValidationFailed(
                "H-MEM: a memory record with no source must be rejected by construction (AGENTS.md section 2)"
            )
        now = self._clock()
        self._seq += 1
        mem_id = f"mem-{self._seq}"
        mem_type: MemoryType = type if type is not None else "general"
        tag_list = list(tags or [])
        domain = self.classify_domain(content, tag_list, mem_type)
        if provenance is None:
            prov = Provenance(origin="manual", learned_at=now, label=source)
        else:
            prov = Provenance.model_validate(provenance)
        record = MemoryRecord(
            id=mem_id,
            content=content,
            type=mem_type,
            layer=layer if layer is not None else "working",
            timestamp=now,
            last_accessed=now,
            access_count=0,
            tags=tag_list,
            embedding=embed(content),
            confidence=clamp01(confidence if confidence is not None else 0.7),
            source=source,
            provenance=prov,
            chat_id=chat_id,
            mission_id=mission_id,
            goal_run_id=goal_run_id,
            domain=domain,
            namespace=self._namespace(domain, mem_type),
            entities=self.extract_entities(content),
            related_to=[],
            supersedes=supersedes,
            derived_from=list(derived_from) if derived_from is not None else None,
            agent_id=agent_id,
            run_id=run_id,
            task_id=task_id,
        )
        self._discover_relationships(record)
        self._records[mem_id] = record
        self._ledger.log(mem_id, "create", self._actor, new_state=snapshot(record))
        self.persist()
        return record

    def get(self, mem_id: str) -> MemoryRecord | None:
        return self._records.get(mem_id)

    def all(self) -> list[MemoryRecord]:
        return list(self._records.values())

    def update(self, mem_id: str, **patch: Any) -> MemoryRecord:
        rec = self._must_get(mem_id)
        unknown = set(patch) - set(MemoryRecord.model_fields)
        if unknown:
            raise ValidationFailed(f"H-MEM: unknown record fields {sorted(unknown)}")
        prev = snapshot(rec)
        for key, value in patch.items():
            setattr(rec, key, value)
        self._ledger.log(mem_id, "update", self._actor, previous_state=prev, new_state=snapshot(rec))
        self.persist()
        return rec

    def delete(self, mem_id: str, reason: str) -> None:
        rec = self._must_get(mem_id)
        del self._records[mem_id]
        self._ledger.log(
            mem_id, "delete", self._actor, previous_state=snapshot(rec), details={"reason": reason}
        )
        self.persist()

    def touch(self, mem_id: str) -> None:
        rec = self._must_get(mem_id)
        rec.last_accessed = self._clock()
        rec.access_count += 1

    def promote(self, mem_id: str, layer: MemoryLayer) -> None:
        rec = self._must_get(mem_id)
        prev = snapshot(rec)
        rec.layer = layer
        self._ledger.log(mem_id, "promote", self._actor, previous_state=prev, new_state=snapshot(rec))
        self.persist()

    def restore_all(self, records: list[MemoryRecord], seq: int) -> None:
        self._records = {r.id: r.model_copy(deep=True) for r in records}
        self._seq = seq
        self.persist()

    def snapshot_all(self) -> StoreSnapshot:
        return StoreSnapshot([r.model_copy(deep=True) for r in self._records.values()], self._seq)

    def _must_get(self, mem_id: str) -> MemoryRecord:
        rec = self._records.get(mem_id)
        if rec is None:
            raise NotFound(f"H-MEM: unknown memory id {mem_id}")
        return rec

    def classify_domain(self, content: str, tags: list[str], type: MemoryType) -> str:
        """Multi-pass domain classification (H-MEM AGENTS.md section 5)."""
        for t in tags:
            if t.startswith("project:"):
                return t[len("project:") :]
            if t.startswith("tech:"):
                return "tech"
        tokens = set(tokenize(content))
        best = "general"
        best_score = 0
        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in tokens)
            if domain == "personal" and type in ("personal", "preference"):
                score += 1
            if score > best_score:
                best = domain
                best_score = score
        return best if best_score > 0 else "general"

    @staticmethod
    def _namespace(domain: str, type: MemoryType) -> str:
        if type in ("preference", "personal"):
            bucket = "profile"
        elif type == "factual":
            bucket = "facts"
        else:
            bucket = "notes"
        return f"{domain}/{bucket}"

    def extract_entities(self, content: str) -> list[str]:
        entities: dict[str, None] = {}
        for t in tokenize(content):
            if t in TECH_TERMS:
                entities[t] = None
        for m in _ENTITY.finditer(content):
            norm = m.group(1).lower()
            if norm not in _ENTITY_STOPWORDS:
                entities[norm] = None
        return list(entities)[: DEFAULTS.entity_cap]

    def _discover_relationships(self, record: MemoryRecord) -> None:
        for other in self._records.values():
            if len(record.related_to) >= DEFAULTS.related_cap:
                break
            shared = [e for e in other.entities if e in record.entities]
            sim = cosine(record.embedding, other.embedding)
            if not record.supersedes and sim > 0.85 and _CORRECTION.search(record.content):
                record.supersedes = other.id
                continue
            if shared and other.domain == record.domain:
                record.related_to.append(other.id)
                if len(other.related_to) < DEFAULTS.related_cap and record.id not in other.related_to:
                    other.related_to.append(record.id)
