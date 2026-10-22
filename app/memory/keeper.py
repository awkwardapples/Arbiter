"""MemoryKeeper: H-MEM-backed MemoryPort (lane P4-A)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.agents.memory_port import MemoryPort, NullMemory
from app.config import Settings
from app.memory import assessments, precedents
from app.memory.hmem import HMEM
from app.policy.loader import load_default
from app.schemas.common import Tier
from app.schemas.decision import DecisionRecord, PrecedentCandidate, TierProfile
from app.tracing import Tracer


def _ms_clock(clock: Callable[[], datetime]) -> Callable[[], int]:
    def _inner() -> int:
        dt = clock()
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return int(dt.timestamp() * 1000)

    return _inner


class HMemMemory:
    name = "hmem"

    def __init__(
        self,
        *,
        var_dir: Path,
        clock: Callable[[], datetime],
        tracer: Tracer | None = None,
    ) -> None:
        self._var_dir = var_dir
        self._clock = clock
        self._tracer = tracer
        self._run_id = "run-local"
        self._case_tier: Tier = "T2"
        self._failing: list[str] = []
        self._vendor_ref = ""
        logs = Path("logs")
        self._hmem = HMEM(
            clock=_ms_clock(clock),
            actor="MemoryKeeper",
            persist_dir=var_dir / "hmem",
            ledger_mirror=logs / "hmem-ledger.jsonl",
        )
        self._policy, _ = load_default()

    def set_run_context(
        self, *, run_id: str, case_tier: Tier, failing: list[str], vendor_ref: str = ""
    ) -> None:
        self._run_id = run_id
        self._case_tier = case_tier
        self._failing = list(failing)
        if vendor_ref:
            self._vendor_ref = vendor_ref

    def find_precedents(self, profile: TierProfile, failing_controls: list[str]) -> list[PrecedentCandidate]:
        del failing_controls
        found = precedents.find_precedents(
            profile,
            self._failing,
            hmem=self._hmem,
            as_of=datetime.now(UTC).date(),
            run_id=self._run_id,
            case_tier=self._case_tier,
            precedents_path=self._var_dir / "precedents.json",
            policy=self._policy,
        )
        if self._tracer is not None:
            self._tracer.event(
                "MemoryKeeper",
                "retrieve_precedents",
                input_summary=f"failing={','.join(self._failing) or '-'}",
                output_summary=f"found={len(found)}",
                status="success",
            )
        return found

    def prior_assessments(self, vendor_ref: str) -> list[dict[str, Any]]:
        return assessments.prior_assessments(vendor_ref, hmem=self._hmem)

    def record_assessment(self, record: DecisionRecord) -> None:
        vendor_ref = self._vendor_ref or record.case_id
        assessments.record_assessment(record, hmem=self._hmem, vendor_ref=vendor_ref)

    def precedent_alignment(self, candidates: list[PrecedentCandidate]) -> float:
        if not self._failing:
            return 1.0
        if not candidates:
            return 0.5
        return 1.0

    def trace_precedent_outcomes(self, record: DecisionRecord) -> None:
        if self._tracer is None:
            return
        for ref in record.precedents_considered:
            action = "precedent_applied" if ref.applied else "precedent_rejected"
            self._tracer.event(
                "MemoryKeeper",
                action,
                input_summary=ref.precedent_id,
                output_summary=",".join(ref.failed_criteria) or "ok",
                status="success" if ref.applied else "escalated",
            )


def build_memory(
    settings: Settings,
    *,
    var_dir: Path,
    clock: Callable[[], datetime],
    tracer: Tracer | None = None,
) -> MemoryPort:
    if settings.ARBITER_MEMORY == "off":
        return NullMemory()
    return HMemMemory(var_dir=var_dir, clock=clock, tracer=tracer)


def shared_hmem(var_dir: Path, clock: Callable[[], datetime]) -> HMEM:
    """Single H-MEM instance for API routes (same persistence as the port)."""
    mem = HMemMemory(var_dir=var_dir, clock=clock, tracer=None)
    return mem._hmem


def count_records(var_dir: Path) -> int:
    state = var_dir / "hmem" / "state.json"
    if not state.is_file():
        return 0
    import json

    data = json.loads(state.read_text(encoding="utf-8"))
    return len(data.get("records") or [])
