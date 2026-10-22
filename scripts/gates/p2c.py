"""Pass 2c gate: the default policy and calibration load."""

from __future__ import annotations


def main() -> int:
    from app.policy import load_default

    policy, calibration = load_default()
    ids = [control.id for control in policy.controls]
    expected = [f"C{index:02d}" for index in range(1, 13)]
    if ids != expected:
        print(f"gate p2c: controls {ids} != {expected}")
        return 1
    if calibration.version != "cal-initial":
        print(f"gate p2c: calibration {calibration.version}")
        return 1
    if [calibration.gate(tier) for tier in ("T1", "T2", "T3")] != [0.90, 0.85, 0.80]:
        print("gate p2c: tier gates")
        return 1
    print("gate p2c: ok")
    return 0
