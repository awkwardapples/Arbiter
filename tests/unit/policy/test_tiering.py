"""P2-T37: inherent boundaries and the special-category override."""

from __future__ import annotations

import pytest

from app.policy.loader import load_default
from app.policy.tiering import assign_tier, tier
from tests.unit.policy.support import profile

pytestmark = pytest.mark.p2c


def test_p2_t37_tier_boundaries() -> None:
    """P2-T37: inherent 2/3/5/6 and special_category."""
    policy, _calibration = load_default()
    cases = [
        (profile(categories=["internal"], criticality="low", spend=0), "T3", 2),
        (profile(categories=["internal"], criticality="medium", spend=0), "T2", 3),
        (profile(categories=["personal"], criticality="low", spend=20_000), "T2", 5),
        (profile(categories=["personal"], criticality="high", spend=0), "T1", 6),
        (profile(categories=["special_category"], criticality="low", spend=0), "T1", 6),
    ]
    for tier_profile, expected_tier, expected_inherent in cases:
        got_tier, inherent = tier(tier_profile, policy)
        assert (got_tier, inherent) == (expected_tier, expected_inherent)
    assert assign_tier(5, ["special_category"], policy) == "T1"
    assert assign_tier(5, ["personal"], policy) == "T2"
    assert assign_tier(2, ["internal"], policy) == "T3"
    assert assign_tier(6, ["none"], policy) == "T1"
