"""Governed precedent adapter over Meterless H-MEM (lane P4-A)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Literal

from app.audit.chain import AuditChain
from app.errors import NotFound, PolicyIneligible
from app.memory.hmem import HMEM
from app.memory.hmem.types import MemoryRecord
from app.policy.loader import Policy
from app.schemas.api import ReviewRequest
from app.schemas.common import Outcome, Tier
from app.schemas.decision import PrecedentCandidate, PrecedentRef, TierProfile
from app.store import CaseBundle

_MITIGATION_SLUGS = {"assurance.bridge_letter_current": "bridge letter"}
_PASSING: frozenset[Outcome] = frozenset({"APPROVE", "APPROVE_WITH_CONDITIONS"})


def precedent_key(control_id: str, mitigation_fact: str, tier: Tier, category: str) -> str:
    slug = _MITIGATION_SLUGS.get(mitigation_fact, mitigation_fact.split(".")[-1].replace("_", " "))
    cat = category.strip().lower()
    return f"precedent control {control_id.lower()} mitigation {slug} tier {tier.lower()} category {cat}"


def _precedents_path(root: Path) -> Path:
    return root / "precedents.json"


def _load_store(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_store(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _next_precedent_id(store: dict[str, Any]) -> str:
    nums = [int(k.split("-")[1]) for k in store if k.startswith("P-") and k[2:].isdigit()]
    n = max(nums, default=0) + 1
    return f"P-{n:04d}"


def check_eligibility(review: ReviewRequest, bundle: CaseBundle, policy: Policy) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    record = bundle.decision
    eligible_controls = {
        c.id for c in policy.controls if c.precedent_exception is not None and c.precedent_exception.allowed
    }
    failing_required = [c.control_id for c in record.controls if c.required and c.state == "FALSE"]
    if not failing_required:
        reasons.append("no_failing_controls")
    if any(c not in eligible_controls for c in failing_required):
        reasons.append("non_exception_control_failing")
    if not any(c in eligible_controls for c in failing_required):
        reasons.append("no_exception_control_failing")
    if review.decision not in _PASSING:
        reasons.append("decision_not_approving")
    spec = next(
        (c.precedent_exception for c in policy.controls if c.id == "C05" and c.precedent_exception),
        None,
    )
    if spec is not None:
        held = policy.roles.get(review.role, 0)
        need = policy.roles.get(spec.approver_role, 99)
        if held < need:
            reasons.append("reviewer_role_insufficient")
        indexed = {f.key: f for f in record.facts}
        mit = indexed.get(spec.mitigation_fact)
        if mit is None or mit.state != "TRUE":
            reasons.append("mitigation_not_true")
    return (len(reasons) == 0, sorted(set(reasons)))


def record_precedent(
    review: ReviewRequest,
    bundle: CaseBundle,
    *,
    hmem: HMEM,
    audit: AuditChain,
    precedents_path: Path,
    run_id: str,
    policy: Policy,
) -> PrecedentRef:
    ok, reasons = check_eligibility(review, bundle, policy)
    if not ok:
        raise PolicyIneligible("precedent ineligible", reasons=reasons)
    record = bundle.decision
    control_id = "C05"
    spec = next(c for c in policy.controls if c.id == control_id).precedent_exception
    assert spec is not None
    category = bundle.decision.policy_inputs.profile.vendor_category or "unknown"
    tier = record.tier
    key = precedent_key(control_id, spec.mitigation_fact, tier, category)
    summary = review.rationale.strip().split(".")[0][:200]
    content = f"{key}. {summary}."
    tags = ["precedent", "c05", "bridge_letter", "approve_with_conditions", tier.lower()]
    store = _load_store(precedents_path)
    precedent_id = _next_precedent_id(store)
    memory = hmem.add(
        content,
        source=f"human_review:{review.reviewer}",
        type="factual",
        layer="long_term",
        tags=tags,
        confidence=0.7,
        agent_id="MemoryKeeper",
        run_id=run_id,
        task_id=bundle.case_id,
    )
    payload = {
        "precedent_id": precedent_id,
        "hmem_id": memory.id,
        "control_id": control_id,
        "mitigation": spec.mitigation_fact,
        "category": category,
        "tier": tier,
        "reviewer_role": review.role,
        "decision": review.decision,
        "created_as_of": record.as_of.isoformat(),
        "case_id": bundle.case_id,
        "review_id": f"{bundle.case_id}-review",
    }
    store[precedent_id] = payload
    _save_store(precedents_path, store)
    audit.append(
        "precedent_created",
        bundle.case_id,
        {"precedent_id": precedent_id, "hmem_id": memory.id, "control_id": control_id},
    )
    return PrecedentRef(
        precedent_id=precedent_id,
        hmem_id=memory.id,
        control_id=control_id,
        relevance=1.0,
        hmem_confidence=memory.confidence,
        applied=False,
    )


def find_precedents(
    profile: TierProfile,
    failing_controls: list[str],
    *,
    hmem: HMEM,
    as_of: date,
    run_id: str,
    case_tier: Tier,
    log_dir: Path = Path("logs"),
    precedents_path: Path = Path("var/precedents.json"),
    policy: Policy | None = None,
) -> list[PrecedentCandidate]:
    from app.policy.loader import load_default

    policy = policy or load_default()[0]
    del as_of  # reserved for future age filtering at retrieval layer
    store = _load_store(precedents_path)
    category = profile.vendor_category or "unknown"
    tier = case_tier
    candidates: list[PrecedentCandidate] = []
    log_dir.mkdir(parents=True, exist_ok=True)
    trace_path = log_dir / f"hmem-retrieval-{run_id}.jsonl"
    lines: list[str] = []
    for control_id in sorted(failing_controls):
        control = next((c for c in policy.controls if c.id == control_id), None)
        if control is None or control.precedent_exception is None or not control.precedent_exception.allowed:
            continue
        spec = control.precedent_exception
        key = precedent_key(control_id, spec.mitigation_fact, tier, category)
        result = hmem.query(key, top_n=5, threshold=0.0)
        trace_line = {
            "retrievalReason": result.trace.retrieval_reason,
            "strategy": result.trace.strategy,
            "scores": result.trace.scores,
            "query": key,
            "control_id": control_id,
        }
        lines.append(json.dumps(trace_line, sort_keys=True))
        for item in result.memories:
            mem = item.memory
            if "precedent" not in mem.tags:
                continue
            payload = _payload_for_memory(store, mem.id)
            if payload is None:
                continue
            candidates.append(
                PrecedentCandidate(
                    precedent_id=str(payload["precedent_id"]),
                    hmem_id=mem.id,
                    control_id=str(payload["control_id"]),
                    mitigation=str(payload["mitigation"]),
                    reviewer_role=str(payload["reviewer_role"]),
                    decision=payload["decision"],  # type: ignore[arg-type]
                    created_as_of=date.fromisoformat(str(payload["created_as_of"])),
                    tier=payload["tier"],  # type: ignore[arg-type]
                    hmem_confidence=mem.confidence,
                    relevance=item.relevance,
                )
            )
    if lines:
        trace_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    candidates.sort(key=lambda c: (-c.relevance, c.precedent_id))
    return candidates


def _payload_for_memory(store: dict[str, Any], hmem_id: str) -> dict[str, Any] | None:
    for payload in store.values():
        if payload.get("hmem_id") == hmem_id:
            return payload
    return None


def feedback(
    precedent_id: str,
    kind: Literal["helpful", "not_helpful", "wrong"],
    *,
    hmem: HMEM,
    audit: AuditChain,
    precedents_path: Path = Path("var/precedents.json"),
    case_id: str = "",
) -> float:
    store = _load_store(precedents_path)
    payload = store.get(precedent_id)
    if payload is None:
        raise NotFound(f"precedent {precedent_id} not found")
    hmem_id = str(payload["hmem_id"])
    hmem.feedback(hmem_id, kind)
    mem = _memory_by_id(hmem, hmem_id)
    audit.append(
        "feedback_recorded",
        case_id or str(payload.get("case_id", "")),
        {"precedent_id": precedent_id, "kind": kind},
    )
    return mem.confidence if mem is not None else 0.0


def _memory_by_id(hmem: HMEM, memory_id: str) -> MemoryRecord | None:
    for mem in hmem.store.all():
        if mem.id == memory_id:
            return mem
    return None


def list_precedents(
    *,
    hmem: HMEM,
    precedents_path: Path = Path("var/precedents.json"),
) -> list[dict[str, Any]]:
    store = _load_store(precedents_path)
    out: list[dict[str, Any]] = []
    for pid in sorted(store):
        payload = store[pid]
        mem = _memory_by_id(hmem, str(payload["hmem_id"]))
        ledger = [e.model_dump(mode="json") for e in hmem.ledger.history(str(payload["hmem_id"]))]
        out.append(
            {
                "precedent_id": pid,
                "hmem_id": payload["hmem_id"],
                "confidence": mem.confidence if mem is not None else None,
                "control_id": payload.get("control_id"),
                "ledger": ledger,
            }
        )
    return out
