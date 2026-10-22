"""P2-T5: additive agentId / runId / taskId fields."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.memory.hmem import HMEM
from tests.conformance.test_hmem_conformance import load_vectors, run_all

pytestmark = pytest.mark.p2a

T0 = 1_750_000_000_000
AGENT = {"agent_id": "planner", "run_id": "run-123", "task_id": "task-7"}


def test_agent_fields_set_and_serialised(tmp_path: Path) -> None:
    hmem = HMEM(clock=lambda: T0, persist_dir=tmp_path)
    m = hmem.add("agent scoped memory", source="t", **AGENT)
    assert (m.agent_id, m.run_id, m.task_id) == ("planner", "run-123", "task-7")
    dumped = m.model_dump(by_alias=True, exclude_none=True)
    assert dumped["agentId"] == "planner" and dumped["runId"] == "run-123" and dumped["taskId"] == "task-7"

    saved = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert saved["records"][0]["agentId"] == "planner"
    created = hmem.ledger.history(m.id)[0]
    assert created.new_state is not None and created.new_state["taskId"] == "task-7"

    reloaded = HMEM(clock=lambda: T0, persist_dir=tmp_path).store.get(m.id)
    assert reloaded is not None and (reloaded.agent_id, reloaded.run_id, reloaded.task_id) == (
        "planner",
        "run-123",
        "task-7",
    )


def test_agent_fields_absent_by_default() -> None:
    m = HMEM(clock=lambda: T0).add("plain memory", source="t")
    dumped = m.model_dump(by_alias=True, exclude_none=True)
    assert not {"agentId", "runId", "taskId"} & dumped.keys()


def test_agent_fields_do_not_change_conformance_outcomes() -> None:
    plain = run_all()
    tagged = run_all(extra=AGENT)
    assert [(r[1], r[3] is None) for r in plain] == [(r[1], r[3] is None) for r in tagged]
    assert len(plain) == 13


def test_agent_fields_do_not_change_ranking() -> None:
    for case in load_vectors()["sections"]["ranking-order"]:
        results = []
        for extra in ({}, AGENT):
            hmem = HMEM(clock=lambda: T0)
            for r in case["records"]:
                hmem.add(r["content"], confidence=r["confidence"], layer=r["layer"], source="c", **extra)
            res = hmem.query(case["query"], threshold=0, top_n=10)
            results.append(([(m.memory.id, m.relevance) for m in res.memories], res.trace))
        assert results[0] == results[1]
