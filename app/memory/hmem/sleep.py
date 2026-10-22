"""Sleep cycle (port of `reference/src/sleepCycle.ts`).

Preview-first: `preview()` computes the full action plan and mutates nothing; `execute()`
takes a backup snapshot first and exposes `restore()`. Guardrails: superseding/current
records, derived/synthesised memories and relationship hubs are NEVER archived.
"""

from __future__ import annotations

from collections.abc import Callable

from app.errors import NotFound
from app.memory.hmem.embeddings import cosine
from app.memory.hmem.ledger import TrustLedgerService
from app.memory.hmem.store import MemoryStoreService, StoreSnapshot
from app.memory.hmem.types import DAY_MS, DEFAULTS, MemoryRecord, Provenance, SleepPreview, SleepReport

HUB_THRESHOLD = 3


class SleepCycleService:
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
        self._backups: dict[str, StoreSnapshot] = {}
        self._backup_seq = 0

    def preview(self) -> SleepPreview:
        now = self._clock()
        records = self._store.all()
        referenced: set[str] = set()
        for m in records:
            referenced.update(m.related_to)
            if m.supersedes:
                referenced.add(m.supersedes)
            referenced.update(m.derived_from or [])

        to_consolidate = [
            m.id
            for m in records
            if m.layer == "short_term" and now - m.last_accessed >= DEFAULTS.consolidation_days * DAY_MS
        ]

        def archivable(m: MemoryRecord) -> bool:
            old_enough = now - m.timestamp >= DEFAULTS.archive_min_days * DAY_MS
            low_access = m.access_count <= DEFAULTS.archive_max_access
            if not (old_enough and low_access and m.id not in referenced):
                return False
            # Guardrails (section 8.2): never archive these three classes.
            if m.supersedes:  # superseding/current record
                return False
            if m.derived_from:  # derived/synthesised memory
                return False
            return len(m.related_to) < HUB_THRESHOLD  # relationship hub

        to_archive = [m.id for m in records if archivable(m)]

        to_synthesize: list[list[str]] = []
        used: set[str] = set()
        for i in range(len(records)):
            if records[i].id in used:
                continue
            group = [records[i]]
            for j in range(i + 1, len(records)):
                if records[j].id in used:
                    continue
                if cosine(records[i].embedding, records[j].embedding) >= DEFAULTS.synthesis_cosine:
                    group.append(records[j])
            if len(group) >= 2:
                used.update(g.id for g in group)
                to_synthesize.append([g.id for g in group])

        return SleepPreview(to_consolidate=to_consolidate, to_archive=to_archive, to_synthesize=to_synthesize)

    def execute(self, preview: SleepPreview | None = None) -> SleepReport:
        plan = preview if preview is not None else self.preview()
        self._backup_seq += 1
        backup_id = f"backup-{self._backup_seq}"
        self._backups[backup_id] = self._store.snapshot_all()
        action_log = [f"backup {backup_id} created"]

        for mem_id in plan.to_consolidate:
            if self._store.get(mem_id) is None:
                continue
            self._store.promote(mem_id, "long_term")
            self._ledger.log(
                mem_id, "sleep_consolidate", self._actor, details={"from": "short_term", "to": "long_term"}
            )
            action_log.append(f"consolidated {mem_id}")

        for mem_id in plan.to_archive:
            m = self._store.get(mem_id)
            if m is None:
                continue
            self._ledger.log(
                mem_id,
                "sleep_archive",
                self._actor,
                details={"age": self._clock() - m.timestamp, "accessCount": m.access_count},
            )
            self._store.delete(mem_id, "sleep archive")
            action_log.append(f"archived {mem_id}")

        synthesized = 0
        for group in plan.to_synthesize:
            members = [m for m in (self._store.get(mem_id) for mem_id in group) if m is not None]
            if len(members) < 2:
                continue
            merged = self._store.add(
                "Synthesis: " + " | ".join(m.content for m in members),
                type="factual",
                layer="long_term",
                tags=list(dict.fromkeys(t for m in members for t in m.tags)),
                confidence=max(m.confidence for m in members),
                source="sleep:synthesis",
                provenance=Provenance(
                    origin="sleep_synthesis",
                    learned_at=self._clock(),
                    label=f"synthesized from {len(members)} memories",
                ),
                derived_from=[m.id for m in members],
            )
            self._ledger.log(merged.id, "sleep_synthesize", self._actor, details={"sources": list(group)})
            for m in members:
                self._store.delete(m.id, "merged by sleep synthesis")
            synthesized += 1
            action_log.append(f"synthesized {merged.id} from {', '.join(group)}")

        self._store.persist()
        return SleepReport(
            backup_id=backup_id,
            consolidated=len(plan.to_consolidate),
            archived=len(plan.to_archive),
            synthesized=synthesized,
            action_log=action_log,
        )

    def restore(self, backup_id: str) -> None:
        backup = self._backups.get(backup_id)
        if backup is None:
            raise NotFound(f"H-MEM: unknown backup {backup_id}")
        self._store.restore_all(backup.records, backup.seq)
        self._ledger.log("*", "restore", self._actor, details={"backupId": backup_id})
