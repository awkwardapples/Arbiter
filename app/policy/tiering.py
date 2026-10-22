"""Inherent-risk score and tier assignment from the policy tables."""

from __future__ import annotations

from app.errors import PolicyError
from app.policy.loader import Policy
from app.schemas.common import Tier
from app.schemas.decision import TierProfile


def tier(profile: TierProfile, policy: Policy) -> tuple[Tier, int]:
    score = inherent_score(profile, policy)
    return assign_tier(score, list(profile.data_categories), policy), score


def inherent_score(profile: TierProfile, policy: Policy) -> int:
    if not profile.data_categories:
        raise PolicyError("invalid tier: data categories are empty")
    try:
        sensitivity = max(policy.tiering.sensitivity[category] for category in profile.data_categories)
        criticality = policy.tiering.criticality[profile.criticality]
    except KeyError as exc:
        raise PolicyError(f"invalid tier: unknown category or criticality {exc}") from exc
    return 2 * sensitivity + criticality + _spend_score(profile.annual_spend_gbp, policy)


def assign_tier(inherent: int, data_categories: list[str], policy: Policy) -> Tier:
    for rule in policy.tiering.tiers:
        if rule.default:
            return _as_tier(rule.tier)
        if rule.or_data_category is not None and rule.or_data_category in data_categories:
            return _as_tier(rule.tier)
        if rule.inherent_gte is not None and inherent >= rule.inherent_gte:
            return _as_tier(rule.tier)
    raise PolicyError(f"invalid tier: no rule matches inherent {inherent}")


def _spend_score(amount: float, policy: Policy) -> int:
    for band in policy.tiering.spend_bands:
        if band.lt is None or amount < band.lt:
            return band.score
    raise PolicyError("invalid tier: no spend band")


def _as_tier(value: str) -> Tier:
    if value not in {"T1", "T2", "T3"}:
        raise PolicyError(f"invalid tier: {value}")
    return value  # type: ignore[return-value]
