"""Working-layer prior assessments for the Planner (lane P4-A)."""

from __future__ import annotations

from typing import Any

from app.memory.hmem import HMEM
from app.schemas.decision import DecisionRecord

_VENDOR_TAG = "vendor_assessment"


def record_assessment(record: DecisionRecord, *, hmem: HMEM, vendor_ref: str) -> None:
    failing = sorted(c.control_id for c in record.controls if c.required and c.state != "TRUE")
    unknown = sorted(c.control_id for c in record.controls if c.state == "UNKNOWN")
    content = (
        f"assessment vendor {vendor_ref} outcome {record.outcome} "
        f"failing {','.join(failing) or '-'} unknown {','.join(unknown) or '-'}"
    )
    hmem.add(
        content,
        source=f"assessment:{record.case_id}",
        type="factual",
        layer="working",
        tags=[_VENDOR_TAG, vendor_ref.lower(), record.outcome.lower()],
        confidence=0.85,
        agent_id="MemoryKeeper",
        run_id=record.run_id,
        task_id=record.case_id,
    )


def prior_assessments(vendor_ref: str, *, hmem: HMEM) -> list[dict[str, Any]]:
    result = hmem.query(f"assessment vendor {vendor_ref}", top_n=10, threshold=0.0)
    out: list[dict[str, Any]] = []
    for item in result.memories:
        mem = item.memory
        if _VENDOR_TAG not in mem.tags or vendor_ref.lower() not in mem.tags:
            continue
        failing: list[str] = []
        unknown: list[str] = []
        outcome = "ESCALATE"
        parts = mem.content.split()
        try:
            idx = parts.index("outcome")
            outcome = parts[idx + 1]
            fidx = parts.index("failing")
            uidx = parts.index("unknown")
            failing = [c for c in parts[fidx + 1 : uidx] if c != "-"]
            unknown = [c for c in parts[uidx + 1 :] if c != "-"]
        except ValueError:
            pass
        out.append(
            {
                "vendor_ref": vendor_ref,
                "outcome": outcome,
                "failing_controls": failing,
                "unknown_controls": unknown,
                "case_id": mem.task_id,
            }
        )
    return out


def plan_queries_from_priors(vendor_ref: str, memory: Any) -> list[tuple[str, str]]:
    """One-call hook for the Planner: prior C09 escalation → verify contract."""
    if memory is None or not hasattr(memory, "prior_assessments"):
        return []
    priors = memory.prior_assessments(vendor_ref)
    for item in priors:
        if item.get("outcome") == "ESCALATE" and "C09" in item.get("failing_controls", []):
            return [
                (
                    "Q_VENDOR_CONTRACT",
                    "prior assessment: verify contract after C09 escalation",
                )
            ]
    return []
