"""The memory port the orchestrator and Planner use (H-MEM implementation arrives in P4-A)."""

from __future__ import annotations

from typing import Any, Protocol

from app.schemas.decision import DecisionRecord, PrecedentCandidate, TierProfile


class MemoryPort(Protocol):
    def find_precedents(
        self, profile: TierProfile, failing_controls: list[str]
    ) -> list[PrecedentCandidate]: ...

    def prior_assessments(self, vendor_ref: str) -> list[dict[str, Any]]: ...

    def record_assessment(self, record: DecisionRecord) -> None: ...


class NullMemory:
    """No memory: no precedents, no prior assessments, nothing recorded."""

    name = "null"

    def find_precedents(self, profile: TierProfile, failing_controls: list[str]) -> list[PrecedentCandidate]:
        del profile, failing_controls
        return []

    def prior_assessments(self, vendor_ref: str) -> list[dict[str, Any]]:
        del vendor_ref
        return []

    def record_assessment(self, record: DecisionRecord) -> None:
        del record
