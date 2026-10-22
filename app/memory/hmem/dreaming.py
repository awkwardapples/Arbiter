"""Dreaming (port of `reference/src/dreaming.ts`): constructive synthesis with a human
approval boundary. Proposals are NEVER auto-materialised; only `approve()` turns one into
durable memory, with derivedFrom lineage.
"""

from __future__ import annotations

from collections.abc import Callable

from app.errors import NotFound
from app.memory.hmem.embeddings import cosine, jaccard
from app.memory.hmem.jsfmt import js_slice
from app.memory.hmem.ledger import TrustLedgerService
from app.memory.hmem.store import MemoryStoreService
from app.memory.hmem.types import DEFAULTS, DreamProposal, DreamProposalType, MemoryRecord, Provenance


class DreamingService:
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
        self._proposals: dict[str, DreamProposal] = {}
        self._seq = 0

    @staticmethod
    def _relatedness(a: MemoryRecord, b: MemoryRecord) -> float:
        """Content similarity, tag overlap, shared domain and entity overlap."""
        return (
            0.5 * max(0.0, cosine(a.embedding, b.embedding))
            + 0.2 * jaccard(a.tags, b.tags)
            + 0.1 * (1 if a.domain == b.domain else 0)
            + 0.2 * jaccard(a.entities, b.entities)
        )

    def _cluster(self) -> list[list[MemoryRecord]]:
        records = self._store.all()
        used: set[str] = set()
        clusters: list[list[MemoryRecord]] = []
        for seed in records:
            if seed.id in used:
                continue
            group = [seed]
            for other in records:
                if other.id == seed.id or other.id in used:
                    continue
                if self._relatedness(seed, other) >= DEFAULTS.dream_relatedness:
                    group.append(other)
            if len(group) >= DEFAULTS.dream_cluster_min_size:
                used.update(g.id for g in group)
                clusters.append(group)
        return clusters

    def _propose(
        self,
        created: list[DreamProposal],
        type: DreamProposalType,
        content: str,
        derived_from: list[str],
        suggested_domain: str | None = None,
    ) -> None:
        self._seq += 1
        proposal = DreamProposal(
            id=f"dream-{self._seq}",
            type=type,
            content=content,
            derived_from=derived_from,
            suggested_domain=suggested_domain,
            status="proposed",
        )
        self._proposals[proposal.id] = proposal
        created.append(proposal)
        self._ledger.log(
            proposal.id, "dream_proposed", self._actor, details={"type": type, "derivedFrom": derived_from}
        )

    def dream(self) -> list[DreamProposal]:
        created: list[DreamProposal] = []
        cap = DEFAULTS.max_dream_proposals_per_type

        # Insights from clusters.
        for cluster in self._cluster()[:cap]:
            domains = "/".join(dict.fromkeys(m.domain for m in cluster))
            self._propose(
                created,
                "insight",
                f"Across {len(cluster)} related memories ({domains}): "
                + " + ".join(m.content for m in cluster),
                [m.id for m in cluster],
            )

        # Domain suggestions for uncategorised memories.
        domain_count = 0
        for m in self._store.all():
            if domain_count >= cap:
                break
            if m.domain != "general":
                continue
            suggested = self._store.classify_domain(m.content, m.tags, m.type)
            if suggested != "general":
                self._propose(
                    created,
                    "domain",
                    f'Reclassify "{js_slice(m.content, 0, 60)}" as {suggested}',
                    [m.id],
                    suggested,
                )
                domain_count += 1

        # Invariants from preference/personal/correction signals.
        invariants = 0
        by_domain: dict[str, list[MemoryRecord]] = {}
        for m in self._store.all():
            if m.type in ("preference", "personal") or "event:user_correction" in m.tags:
                by_domain.setdefault(m.domain, []).append(m)
        for domain, group in by_domain.items():
            if invariants >= cap:
                break
            if len(group) < 2:
                continue
            self._propose(
                created,
                "invariant",
                f"Stable pattern in {domain}: " + "; ".join(m.content for m in group),
                [m.id for m in group],
            )
            invariants += 1

        return created

    def pending(self) -> list[DreamProposal]:
        return [p for p in self._proposals.values() if p.status == "proposed"]

    def _must_get_pending(self, proposal_id: str) -> DreamProposal:
        p = self._proposals.get(proposal_id)
        if p is None or p.status != "proposed":
            raise NotFound(f"H-MEM: no pending proposal {proposal_id}")
        return p

    def approve(self, proposal_id: str) -> MemoryRecord | None:
        p = self._must_get_pending(proposal_id)
        p.status = "approved"
        self._ledger.log(proposal_id, "dream_approved", self._actor, details={"type": p.type})

        if p.type == "domain":
            for mem_id in p.derived_from:
                if self._store.get(mem_id) is not None and p.suggested_domain:
                    self._store.update(mem_id, domain=p.suggested_domain)
            return None
        # insight -> long-term factual; invariant -> long-term preference. Both carry lineage.
        return self._store.add(
            p.content,
            type="factual" if p.type == "insight" else "preference",
            layer="long_term",
            tags=[f"dream:{p.type}"],
            confidence=0.75,
            source="dreaming",
            provenance=Provenance(
                origin="dream", learned_at=self._clock(), label=f"approved {p.type} proposal"
            ),
            derived_from=list(p.derived_from),
        )

    def reject(self, proposal_id: str) -> None:
        p = self._must_get_pending(proposal_id)
        p.status = "rejected"  # logged, not materialised
        self._ledger.log(proposal_id, "dream_rejected", self._actor, details={"type": p.type})
