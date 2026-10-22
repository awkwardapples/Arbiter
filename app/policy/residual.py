"""Residual risk score from the policy residual_risk block."""

from __future__ import annotations

from app.policy.loader import Policy
from app.schemas.common import Tier
from app.schemas.decision import ControlResult, PolicyInputs


def residual_risk(tier: Tier, controls: list[ControlResult], inputs: PolicyInputs, policy: Policy) -> int:
    spec = policy.residual_risk
    score = float(spec.tier_base[tier])
    for control in controls:
        if not control.required:
            continue
        if control.state == "FALSE":
            score += spec.per_false_weight * control.weight
        elif control.state == "UNKNOWN":
            score += spec.per_unknown_weight * control.weight
    material = sum(1 for item in inputs.contradictions if item.severity == "material" and not item.resolved)
    score += spec.per_material_contradiction * material
    if any(flag.level == "block" for flag in inputs.guard_flags):
        score += spec.injection
    return int(min(spec.cap, score))
