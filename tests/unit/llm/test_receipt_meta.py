"""P15-T2: `receipt_meta` keeps the routing receipt subset and drops everything else."""

from __future__ import annotations

from typing import Any

import pytest

from app.llm.providers.meterless import receipt_meta

pytestmark = pytest.mark.p15

_DROPPED = (
    "phases",
    "egress",
    "lineage",
    "cache",
    "consensus",
    "job",
    "usage",
    "privacy",
    "receipt_envelope",
)


@pytest.mark.parametrize("route", ["fast", "deep"])
def test_p15_t2_receipt_subset(route: str, chat_fixture: dict[str, Any]) -> None:
    body = chat_fixture[route]["body"]
    receipt = body["meterless"]
    policy = receipt["receipt"]["app_policy"]
    meta = receipt_meta(body)

    assert meta["receipt_id"] == receipt["receipt_id"]
    assert meta["requested_model"] == receipt["requested_model"]
    assert meta["routed_model"] == receipt["routed_model"]
    assert meta["provider_model"] == receipt["provider_model"]
    assert meta["response_id"] == body["id"]
    assert meta["winning_route.model"] == receipt["winning_route"]["model"]
    assert meta["winning_route.provider"] == receipt["winning_route"]["provider"]
    assert meta["app_policy.mode_coerced"] == str(policy["mode_coerced"])
    assert meta["app_policy.requested_mode"] == policy["requested_mode"]
    assert meta["app_policy.routed_mode"] == policy["routed_mode"]
    assert meta["app_policy.bound_mode"] == policy["bound_mode"]
    assert meta["cost.actual_usd"] == str(receipt["cost"]["actual_usd"])
    assert meta["cost.baseline.model"] == receipt["cost"]["baseline"]["model"]
    assert meta["savings.amount"] == str(receipt["savings"]["amount"])
    assert meta["savings.vs"] == receipt["savings"]["vs"]

    for key in meta:
        assert not key.startswith(_DROPPED), key
    assert all(isinstance(value, str) for value in meta.values())
    # Null policy fields are not stringified as "None".
    assert "None" not in meta.values()


def test_p15_t2_app_policy_at_top_level_is_read() -> None:
    body = {"meterless": {"receipt_id": "rcpt_x", "app_policy": {"mode_coerced": False, "lanes": None}}}
    meta = receipt_meta(body)
    assert meta["app_policy.mode_coerced"] == "False"
    assert "app_policy.lanes" not in meta


def test_p15_t2_no_receipt_is_empty() -> None:
    assert receipt_meta({"choices": []}) == {}
