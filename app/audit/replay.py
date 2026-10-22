"""Recompute a stored decision and check policy, record and contract signatures."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from app.actions import contracts
from app.canon import sha256_hex
from app.policy.engine import decide, force_escalate
from app.policy.loader import load_calibration, load_policy, policy_sha256
from app.schemas.contract import ExecutionContract
from app.schemas.decision import DecisionRecord
from app.store import Store

_POLICY_ROOT = Path(__file__).resolve().parents[2] / "policy"


class ReplayChecks(BaseModel):
    policy_hash: bool
    record_hash: bool
    contract_signatures: bool


class ReplayResult(BaseModel):
    match: bool
    diff: list[str]
    checks: ReplayChecks


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
    major = str(record.policy_version).split(".", 1)[0]
    policy = load_policy(root / f"arbiter_policy.v{major}.yaml")
    calibration = load_calibration(root / "calibration" / f"{record.calibration_version}.json")
    policy_ok = policy_sha256(policy) == record.policy_sha256
    recomputed = decide(record.policy_inputs, policy, calibration)
    for reason in record.escalation_reasons:
        recomputed = force_escalate(recomputed, reason)
    content_ok = sha256_hex(record.model_dump(exclude={"record_sha256"})) == record.record_sha256
    record_ok = recomputed.record_sha256 == record.record_sha256 and content_ok
    diff = _diff(record, recomputed)
    signatures_ok = _signatures(store.contracts_for(case_id))
    return ReplayResult(
        match=policy_ok and record_ok and signatures_ok and not diff,
        diff=diff,
        checks=ReplayChecks(
            policy_hash=policy_ok,
            record_hash=record_ok,
            contract_signatures=signatures_ok,
        ),
    )


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
