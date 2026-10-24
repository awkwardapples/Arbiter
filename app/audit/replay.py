"""Recompute a stored decision and check policy, record and contract signatures.

A human-reviewed case stores the reviewer's record. Replay then replays the machine record kept
when the review replaced it, and verifies the review on its own (lane P19).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from app.actions import contracts
from app.canon import sha256_hex
from app.policy.engine import decide, force_escalate, required_approvals
from app.policy.loader import Calibration, Policy, load_calibration, load_policy, policy_sha256
from app.schemas.contract import ExecutionContract
from app.schemas.decision import DecisionRecord
from app.store import Store

_POLICY_ROOT = Path(__file__).resolve().parents[2] / "policy"
_HUMAN_REVIEW = ["HUMAN_REVIEW"]
# Fields a review changes; the rest of the human record must equal the machine record.
_REVIEW_FIELDS = {"outcome", "outcome_reasons", "run_id", "created_at", "record_sha256"}


class ReplayChecks(BaseModel):
    policy_hash: bool
    record_hash: bool
    contract_signatures: bool


class HumanOverride(BaseModel):
    reviewer: str
    role: str
    decision: str
    rationale: str
    review_id: str
    at: datetime | None = None


class ReplayResult(BaseModel):
    match: bool
    diff: list[str]
    checks: ReplayChecks
    human_override: HumanOverride | None = None
    machine_outcome: str | None = None
    machine_source: Literal["stored", "reconstructed"] | None = None


def replay(
    case_id: str,
    *,
    store: Store | None = None,
    policy_root: Path | None = None,
    now: datetime | None = None,
) -> ReplayResult:
    """Replay one case. `now` is unused: signatures are checked at each contract's issued_at."""
    del now
    store = store or Store()
    root = policy_root or _POLICY_ROOT
    record = store.get(case_id).decision
    signatures_ok = _signatures(store.contracts_for(case_id))
    if record.outcome_reasons == _HUMAN_REVIEW:
        return _replay_reviewed(case_id, record, store, root, signatures_ok)
    policy, calibration = _policy_for(record, root)
    policy_ok, record_ok, diff, _recomputed = _replay_machine(record, policy, calibration)
    return ReplayResult(
        match=policy_ok and record_ok and signatures_ok and not diff,
        diff=diff,
        checks=ReplayChecks(
            policy_hash=policy_ok,
            record_hash=record_ok,
            contract_signatures=signatures_ok,
        ),
    )


def _policy_for(record: DecisionRecord, root: Path) -> tuple[Policy, Calibration]:
    major = str(record.policy_version).split(".", 1)[0]
    policy = load_policy(root / f"arbiter_policy.v{major}.yaml")
    calibration = load_calibration(root / "calibration" / f"{record.calibration_version}.json")
    return policy, calibration


def _recompute(record: DecisionRecord, policy: Policy, calibration: Calibration) -> DecisionRecord:
    recomputed = decide(record.policy_inputs, policy, calibration)
    for reason in record.escalation_reasons:
        recomputed = force_escalate(recomputed, reason)
    return recomputed


def _content_ok(record: DecisionRecord) -> bool:
    return sha256_hex(record.model_dump(exclude={"record_sha256"})) == record.record_sha256


def _replay_machine(
    record: DecisionRecord, policy: Policy, calibration: Calibration
) -> tuple[bool, bool, list[str], DecisionRecord]:
    policy_ok = policy_sha256(policy) == record.policy_sha256
    recomputed = _recompute(record, policy, calibration)
    record_ok = recomputed.record_sha256 == record.record_sha256 and _content_ok(record)
    return policy_ok, record_ok, _diff(record, recomputed), recomputed


def _replay_reviewed(
    case_id: str, human: DecisionRecord, store: Store, root: Path, signatures_ok: bool
) -> ReplayResult:
    policy, calibration = _policy_for(human, root)
    machine = store.machine_decision_for(case_id)
    source: Literal["stored", "reconstructed"]
    if machine is not None:
        source = "stored"
        policy_ok, record_ok, diff, _recomputed = _replay_machine(machine, policy, calibration)
        if human.model_dump(exclude=_REVIEW_FIELDS) != machine.model_dump(exclude=_REVIEW_FIELDS):
            diff.append("review.record")
    else:
        # Reviewed before P19: no machine record was kept. Re-decide from the human record's
        # inputs; the machine record hash cannot be checked, so record_hash covers the human record.
        source = "reconstructed"
        machine = _recompute(human, policy, calibration)
        policy_ok = policy_sha256(policy) == human.policy_sha256
        record_ok = _content_ok(human)
        diff = [item for item in _diff(human, machine) if item != "outcome"]
    reviews = store.reviews_for(case_id)
    latest = reviews[-1] if reviews else None
    diff.extend(_review_diff(human, latest, policy))
    override = None
    if latest is not None:
        override = HumanOverride(
            reviewer=str(latest.get("reviewer", "")),
            role=str(latest.get("role", "")),
            decision=str(latest.get("decision", "")),
            rationale=str(latest.get("rationale", "")),
            review_id=str(latest.get("review_id", "")),
            at=human.created_at,
        )
    return ReplayResult(
        match=policy_ok and record_ok and signatures_ok and not diff,
        diff=diff,
        checks=ReplayChecks(
            policy_hash=policy_ok,
            record_hash=record_ok,
            contract_signatures=signatures_ok,
        ),
        human_override=override,
        machine_outcome=machine.outcome,
        machine_source=source,
    )


def _review_diff(human: DecisionRecord, review: dict[str, Any] | None, policy: Policy) -> list[str]:
    if review is None:
        return ["review.missing"]
    diff: list[str] = []
    if review.get("decision") != human.outcome:
        diff.append("review.decision")
    if review.get("human_run_id") != human.run_id:
        diff.append("review.run_id")
    if not _content_ok(human):
        diff.append("review.record_hash")
    role = review.get("role")
    needed = [policy.roles.get(item, 0) for item in required_approvals(human, policy)]
    if role not in policy.roles or policy.roles[str(role)] < max(needed, default=0):
        diff.append("review.role")
    return diff


def _diff(stored: DecisionRecord, recomputed: DecisionRecord) -> list[str]:
    by_key = {fact.key: fact for fact in recomputed.facts}
    diff: list[str] = []
    for fact in stored.facts:
        other = by_key.get(fact.key)
        if other is None or other.value != fact.value:
            diff.append(f"facts.{fact.key}")
    if stored.outcome != recomputed.outcome:
        diff.append("outcome")
    return diff


def _signatures(found: list[ExecutionContract]) -> bool:
    if not found:
        return False
    for contract in found:
        ok, _reason = contracts.verify(contract, now=contract.issued_at)
        if not ok:
            return False
    return True
