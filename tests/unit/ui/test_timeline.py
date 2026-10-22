"""P5-T13: example-2 trace timeline graph."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ui.timeline import agent_nodes, build_timeline_dot, extract_edges

pytestmark = pytest.mark.p5a

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "ui" / "example_2_trace.json"

EXPECTED_AGENTS = frozenset(
    {
        "ActionExecutor",
        "ChallengerAgent",
        "EvaluatorAgent",
        "EvidenceAgent",
        "MemoryKeeper",
        "Orchestrator",
        "PlannerAgent",
        "ReporterAgent",
    }
)


@pytest.fixture(scope="module")
def example_2_events() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_p5_t13_agent_node_set(example_2_events: list[dict]) -> None:
    """P5-T13: node set matches example 2 collaborative trace."""
    assert agent_nodes(example_2_events) == EXPECTED_AGENTS


def test_p5_t13_dashed_evaluate_plan_edge(example_2_events: list[dict]) -> None:
    """P5-T13: EVALUATE→PLAN loop edge is dashed in DOT."""
    edges = extract_edges(example_2_events)
    loop = [e for e in edges if e.src == "EvaluatorAgent" and e.dst == "PlannerAgent" and e.dashed]
    assert loop, "expected dashed EvaluatorAgent→PlannerAgent edge"
    dot = build_timeline_dot(example_2_events)
    assert "style=dashed" in dot
    assert "EvaluatorAgent" in dot and "PlannerAgent" in dot
