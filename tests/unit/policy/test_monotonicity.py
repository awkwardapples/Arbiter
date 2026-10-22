"""P2-T35: safety monotonicity over control results."""

from __future__ import annotations

import random

import pytest

from app.policy.engine import decide
from app.policy.loader import load_default
from tests.unit.policy.support import facts_from, policy_inputs, profile

pytestmark = pytest.mark.p2c

SEED = 20261022
TRIALS = 2000
CONTROLS = [f"C{index:02d}" for index in range(1, 13)]
RANK = {
    "APPROVE": 0,
    "APPROVE_WITH_CONDITIONS": 1,
    "REQUEST_INFO": 2,
    "ESCALATE": 3,
    "DECLINE": 4,
}
APPROVALS = {"APPROVE", "APPROVE_WITH_CONDITIONS"}

# Personal + payment, high criticality, spend above £100k → T1, every control required.
T1 = profile(categories=["personal", "payment"], criticality="high", spend=150_000.0)


def _control_facts(control_id: str, state: str) -> dict:
    """Facts that realise one control state. Keys do not overlap across controls."""
    if control_id == "C01":
        if state == "TRUE":
            return {"mfa.admin_enforced": (True, "TRUE"), "mfa.remote_enforced": (True, "TRUE")}
        if state == "FALSE":
            return {"mfa.admin_enforced": (False, "FALSE"), "mfa.remote_enforced": (True, "TRUE")}
        return {"mfa.remote_enforced": (True, "TRUE"), "mfa.admin_enforced": None}
    if control_id == "C02":
        if state == "TRUE":
            return {"creds.vaulted": (True, "TRUE"), "creds.rotation_days": (90, "TRUE")}
        if state == "FALSE":
            return {"creds.vaulted": (True, "TRUE"), "creds.rotation_days": (120, "TRUE")}
        return {"creds.vaulted": (True, "TRUE"), "creds.rotation_days": None}
    if control_id == "C03":
        if state == "TRUE":
            return {"access.review_interval_days": (90, "TRUE")}
        if state == "FALSE":
            return {"access.review_interval_days": (180, "TRUE")}
        return {"access.review_interval_days": None}
    if control_id == "C04":
        if state == "TRUE":
            return {"crypto.at_rest": (True, "TRUE"), "crypto.in_transit_tls12": (True, "TRUE")}
        if state == "FALSE":
            return {"crypto.at_rest": (False, "FALSE"), "crypto.in_transit_tls12": (True, "TRUE")}
        return {"crypto.at_rest": None, "crypto.in_transit_tls12": (True, "TRUE")}
    if control_id == "C05":
        if state == "TRUE":
            return {"assurance.soc2_type2_current": (True, "TRUE"), "assurance.iso27001_current": None}
        if state == "FALSE":
            return {
                "assurance.soc2_type2_current": (False, "FALSE"),
                "assurance.iso27001_current": (False, "FALSE"),
            }
        return {"assurance.soc2_type2_current": None, "assurance.iso27001_current": None}
    if control_id == "C06":
        if state == "TRUE":
            return {"incidents.material_unremediated_24m": (0, "TRUE")}
        if state == "FALSE":
            return {"incidents.material_unremediated_24m": (2, "TRUE")}
        return {"incidents.material_unremediated_24m": None}
    if control_id == "C07":
        if state == "TRUE":
            return {"breach.notify_hours": (72, "TRUE")}
        if state == "FALSE":
            return {"breach.notify_hours": (96, "TRUE")}
        return {"breach.notify_hours": None}
    if control_id == "C08":
        if state == "TRUE":
            return {"dpa.signed": (True, "TRUE")}
        if state == "FALSE":
            return {"dpa.signed": (False, "FALSE")}
        return {"dpa.signed": None}
    if control_id == "C09":
        if state == "TRUE":
            return {"residency.regions": (["EU"], "TRUE"), "transfer.mechanism": None}
        if state == "FALSE":
            return {"residency.regions": (["US"], "TRUE"), "transfer.mechanism": ("BCR", "TRUE")}
        return {"residency.regions": None, "transfer.mechanism": None}
    if control_id == "C10":
        if state == "TRUE":
            return {"subprocessors.disclosed": (True, "TRUE")}
        if state == "FALSE":
            return {"subprocessors.disclosed": (False, "FALSE")}
        return {"subprocessors.disclosed": None}
    if control_id == "C11":
        if state == "TRUE":
            return {"sanctions.watchlist_matches": (0, "TRUE")}
        if state == "FALSE":
            return {"sanctions.watchlist_matches": (1, "TRUE")}
        return {"sanctions.watchlist_matches": None}
    if control_id == "C12":
        if state == "TRUE":
            return {"vuln.kev_matches": (0, "TRUE"), "vuln.patch_sla_critical_days": None}
        if state == "FALSE":
            return {"vuln.kev_matches": (4, "TRUE"), "vuln.patch_sla_critical_days": (45, "TRUE")}
        return {"vuln.kev_matches": None, "vuln.patch_sla_critical_days": None}
    raise AssertionError(control_id)


def _facts(states: dict[str, str]):
    spec: dict = {"vendor.data_categories": (["personal", "payment"], "TRUE")}
    for control_id, state in states.items():
        spec.update(_control_facts(control_id, state))
    return facts_from(spec)


def _outcome(bundle, states: dict[str, str], confidence_value: float):
    policy, calibration = bundle
    record = decide(
        policy_inputs(
            _facts(states),
            tier_profile=T1,
            confidence_value=confidence_value,
        ),
        policy,
        calibration,
    )
    return record


def test_p2_t35_safety_monotonicity() -> None:
    """P2-T35: degrading a control never improves a safe outcome and never creates an approval."""
    bundle = load_default()
    _policy, calibration = bundle
    gate = calibration.gate("T1")
    rng = random.Random(SEED)
    completed = 0
    while completed < TRIALS:
        states = {control_id: rng.choice(["TRUE", "FALSE", "UNKNOWN"]) for control_id in CONTROLS}
        target = rng.choice(CONTROLS)
        if states[target] == "FALSE":
            continue
        degraded = dict(states)
        degraded[target] = "UNKNOWN" if states[target] == "TRUE" else "FALSE"
        confidence_value = rng.random()
        before = _outcome(bundle, states, confidence_value)
        after = _outcome(bundle, degraded, confidence_value)
        observed = {control.control_id: control.state for control in before.controls}
        observed_after = {control.control_id: control.state for control in after.controls}
        if observed[target] != states[target] or observed_after[target] != degraded[target]:
            raise AssertionError(
                f"seed={SEED} trial={completed} control {target} "
                f"wanted {states[target]}->{degraded[target]} "
                f"got {observed[target]}->{observed_after[target]}"
            )
        if confidence_value >= gate and RANK[after.outcome] < RANK[before.outcome]:
            raise AssertionError(
                f"seed={SEED} trial={completed} rank improved {before.outcome} -> {after.outcome} "
                f"on {target} {states[target]}->{degraded[target]}"
            )
        entered_approval = before.outcome not in APPROVALS and after.outcome in APPROVALS
        relaxed_conditions = before.outcome == "APPROVE_WITH_CONDITIONS" and after.outcome == "APPROVE"
        if entered_approval or relaxed_conditions:
            raise AssertionError(
                f"seed={SEED} trial={completed} approval created {before.outcome} -> {after.outcome} "
                f"confidence={confidence_value}"
            )
        completed += 1
