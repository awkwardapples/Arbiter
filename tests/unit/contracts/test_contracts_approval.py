"""P2-T46: approval re-issues child contract."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.actions.contracts import add_approval, issue
from app.policy.engine import required_approvals
from tests.unit.contracts.support import CAPABILITIES_MAP, sample_report, t1_approve_decision

pytestmark = pytest.mark.p2d


def test_p2_t46_add_approval_child_contract() -> None:
    decision, policy = t1_approve_decision()
    now = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
    parent = issue(
        decision,
        sample_report(),
        capabilities_map=CAPABILITIES_MAP,
        policy=policy,
        trace_id="trace-1",
        registry_version=1,
        now=now,
    )
    parent_dump = parent.model_dump()
    child = add_approval(
        parent,
        by="reviewer@example.com",
        role="tprm_analyst",
        decision="approve",
        rationale="Looks good after review of evidence pack.",
        now=now,
        policy=policy,
    )
    assert child.parent_id == parent.contract_id
    assert child.contract_id != parent.contract_id
    assert parent.model_dump() == parent_dump
    roles = required_approvals(decision, policy)
    assert [row["role"] for row in child.risk.approvals_required] == roles
    assert child.state == "approved"
