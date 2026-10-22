"""P2-T30: every control is TRUE, FALSE, or UNKNOWN on crafted facts."""

from __future__ import annotations

import pytest

from app.policy.dsl import evaluate
from app.policy.loader import load_default
from tests.unit.policy.support import fact_map, facts_from, make_fact

pytestmark = pytest.mark.p2c

# None removes a base fact. Each control has at least three rows.
CASES: list[tuple[str, dict, str]] = [
    ("C01", {}, "TRUE"),
    ("C01", {"mfa.admin_enforced": (False, "FALSE")}, "FALSE"),
    ("C01", {"mfa.remote_enforced": None}, "UNKNOWN"),
    ("C01", {"mfa.admin_enforced": (True, "UNKNOWN")}, "UNKNOWN"),
    ("C02", {}, "TRUE"),
    ("C02", {"creds.rotation_days": (91, "TRUE")}, "FALSE"),
    ("C02", {"creds.vaulted": None}, "UNKNOWN"),
    ("C02", {"creds.rotation_days": (90.0, "TRUE")}, "TRUE"),
    ("C03", {}, "TRUE"),
    ("C03", {"access.review_interval_days": (91, "TRUE")}, "FALSE"),
    ("C03", {"access.review_interval_days": None}, "UNKNOWN"),
    ("C03", {"access.review_interval_days": (0, "TRUE")}, "TRUE"),
    ("C04", {}, "TRUE"),
    ("C04", {"crypto.in_transit_tls12": (False, "FALSE")}, "FALSE"),
    ("C04", {"crypto.at_rest": None}, "UNKNOWN"),
    ("C05", {}, "TRUE"),
    ("C05", {"assurance.soc2_type2_current": (False, "FALSE"), "assurance.iso27001_current": (False, "FALSE")}, "FALSE"),
    ("C05", {"assurance.soc2_type2_current": None, "assurance.iso27001_current": None}, "UNKNOWN"),
    ("C05", {"assurance.soc2_type2_current": (False, "FALSE"), "assurance.iso27001_current": (True, "TRUE")}, "TRUE"),
    ("C06", {}, "TRUE"),
    ("C06", {"incidents.material_unremediated_24m": (1, "TRUE")}, "FALSE"),
    ("C06", {"incidents.material_unremediated_24m": None}, "UNKNOWN"),
    ("C07", {}, "TRUE"),
    ("C07", {"breach.notify_hours": (73, "TRUE")}, "FALSE"),
    ("C07", {"breach.notify_hours": None}, "UNKNOWN"),
    ("C07", {"breach.notify_hours": (0, "TRUE")}, "TRUE"),
    ("C08", {}, "TRUE"),
    ("C08", {"dpa.signed": (False, "FALSE")}, "FALSE"),
    ("C08", {"dpa.signed": None}, "UNKNOWN"),
    ("C09", {}, "TRUE"),
    ("C09", {"residency.regions": (["US"], "TRUE"), "transfer.mechanism": ("BCR", "TRUE")}, "FALSE"),
    ("C09", {"residency.regions": None, "transfer.mechanism": None}, "UNKNOWN"),
    ("C09", {"residency.regions": None, "transfer.mechanism": ("IDTA", "TRUE")}, "TRUE"),
    ("C09", {"residency.regions": (["EU", "UK"], "TRUE")}, "TRUE"),
    ("C10", {}, "TRUE"),
    ("C10", {"subprocessors.disclosed": (False, "FALSE")}, "FALSE"),
    ("C10", {"subprocessors.disclosed": None}, "UNKNOWN"),
    ("C11", {}, "TRUE"),
    ("C11", {"sanctions.watchlist_matches": (1, "TRUE")}, "FALSE"),
    ("C11", {"sanctions.watchlist_matches": None}, "UNKNOWN"),
    ("C11", {"sanctions.watchlist_matches": (0, "UNKNOWN")}, "UNKNOWN"),
    ("C12", {}, "TRUE"),
    ("C12", {"vuln.kev_matches": (2, "TRUE"), "vuln.patch_sla_critical_days": (30, "TRUE")}, "FALSE"),
    ("C12", {"vuln.kev_matches": None, "vuln.patch_sla_critical_days": None}, "UNKNOWN"),
    ("C12", {"vuln.kev_matches": None, "vuln.patch_sla_critical_days": (14, "TRUE")}, "TRUE"),
]


@pytest.mark.parametrize(("control_id", "overrides", "expected"), CASES)
def test_p2_t30_control_tristate(control_id: str, overrides: dict, expected: str) -> None:
    """P2-T30: each control yields TRUE, FALSE, or UNKNOWN."""
    policy, _calibration = load_default()
    control = next(item for item in policy.controls if item.id == control_id)
    facts = fact_map(facts_from(overrides))
    assert evaluate(control.rule, facts) == expected


def test_p2_t30_covers_every_control() -> None:
    """P2-T30: at least three crafted fact sets per control."""
    counts: dict[str, int] = {}
    for control_id, _overrides, _expected in CASES:
        counts[control_id] = counts.get(control_id, 0) + 1
    assert set(counts) == {f"C{i:02d}" for i in range(1, 13)}
    assert all(count >= 3 for count in counts.values())


def test_p2_t30_remaining_leaf_ops() -> None:
    """P2-T30: leaf ops outside the control table still return a tri-state."""
    present = make_fact("creds.rotation_days", 10, "TRUE")
    missing_state = make_fact("creds.rotation_days", 10, "UNKNOWN")
    assert evaluate({"fact": "creds.rotation_days", "op": "gt", "value": 9}, {"creds.rotation_days": present}) == "TRUE"
    assert evaluate({"fact": "creds.rotation_days", "op": "lt", "value": 10}, {"creds.rotation_days": present}) == "FALSE"
    assert evaluate({"fact": "creds.rotation_days", "op": "ne", "value": 11}, {"creds.rotation_days": present}) == "TRUE"
    assert evaluate({"fact": "creds.rotation_days", "op": "gte", "value": 10}, {"creds.rotation_days": present}) == "TRUE"
    assert (
        evaluate(
            {"fact": "transfer.mechanism", "op": "not_in", "value": ["SCCs", "IDTA"]},
            {"transfer.mechanism": make_fact("transfer.mechanism", "BCR", "TRUE")},
        )
        == "TRUE"
    )
    assert evaluate({"fact": "creds.rotation_days", "op": "exists"}, {"creds.rotation_days": present}) == "TRUE"
    assert evaluate({"fact": "creds.rotation_days", "op": "exists"}, {"creds.rotation_days": missing_state}) == "UNKNOWN"
    assert evaluate({"fact": "creds.rotation_days", "op": "eq", "value": 10}, {}) == "UNKNOWN"
    regions = make_fact("residency.regions", [], "TRUE")
    assert (
        evaluate({"fact": "residency.regions", "op": "subset_of", "value": ["UK", "EU"]}, {"residency.regions": regions})
        == "TRUE"
    )
    assert (
        evaluate({"fact": "residency.regions", "op": "in_any", "value": ["UK"]}, {"residency.regions": regions})
        == "FALSE"
    )
