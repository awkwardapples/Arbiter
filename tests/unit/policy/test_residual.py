"""Residual risk uses control weights, contradictions, and the injection penalty."""

from __future__ import annotations

import pytest

from app.policy.loader import load_default
from app.policy.residual import residual_risk
from app.schemas.decision import ControlResult
from tests.unit.policy.support import block_flag, contradiction, policy_inputs

pytestmark = pytest.mark.p2c


def _control(control_id: str, state: str, weight: float, *, required: bool = True) -> ControlResult:
    return ControlResult(
        control_id=control_id,
        title=control_id,
        required=required,
        state=state,  # type: ignore[arg-type]
        fact_ids=[],
        rule_id=control_id,
        weight=weight,
    )


def test_residual_weights_and_cap() -> None:
    policy, _calibration = load_default()
    inputs = policy_inputs(
        [],
        contradictions=[contradiction("residency.regions")],
        guard_flags=[block_flag()],
    )
    controls = [
        _control("C01", "FALSE", 3),
        _control("C02", "UNKNOWN", 2),
        _control("C04", "TRUE", 2),
        _control("C10", "FALSE", 1, required=False),
    ]
    # T2 base 35 + 6*3 + 3*2 + 10 + 15 = 84. The non-required FALSE control adds nothing.
    assert residual_risk("T2", controls, inputs, policy) == 84
    heavy = [_control(f"C{i:02d}", "FALSE", 3) for i in range(1, 13)]
    assert residual_risk("T1", heavy, inputs, policy) == 100
