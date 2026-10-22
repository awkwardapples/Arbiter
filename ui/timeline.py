"""Trace timeline graph and table builders (lane P5-A)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_PHASE_TO_AGENT = {
    "PLAN": "PlannerAgent",
    "GATHER": "EvidenceAgent",
    "EVALUATE": "EvaluatorAgent",
    "CHALLENGE": "ChallengerAgent",
    "REPORT": "ReporterAgent",
    "DECIDE_1": "Orchestrator",
    "DECIDE_2": "Orchestrator",
    "MEMORY_CHECK": "MemoryKeeper",
    "ACTIONS": "ActionExecutor",
}


@dataclass(frozen=True)
class TimelineEdge:
    src: str
    dst: str
    dashed: bool
    label: str


def agent_nodes(events: list[dict[str, Any]]) -> set[str]:
    return {str(e.get("agent_name", "")) for e in events if e.get("agent_name")}


def _phase_agent(phase: str) -> str:
    return _PHASE_TO_AGENT.get(phase, phase)


def extract_edges(events: list[dict[str, Any]]) -> list[TimelineEdge]:
    edges: list[TimelineEdge] = []
    seen: set[tuple[str, str, str]] = set()
    for event in events:
        if event.get("agent_name") != "Orchestrator" or event.get("action") != "transition":
            continue
        summary = str(event.get("output_summary", ""))
        if "→" not in summary:
            continue
        head, _, tail = summary.partition(" ")
        parts = head.split("→", 1)
        if len(parts) != 2:
            continue
        src_phase, dst_phase = parts
        label = tail.strip() if tail else ""
        src = _phase_agent(src_phase)
        dst = _phase_agent(dst_phase)
        dashed = (
            src_phase == "EVALUATE" and dst_phase == "PLAN" and event.get("status") == "needs_revision"
        ) or (src_phase == "CHALLENGE" and dst_phase == "PLAN")
        key = (src, dst, label)
        if key in seen:
            continue
        seen.add(key)
        edges.append(TimelineEdge(src=src, dst=dst, dashed=dashed, label=label))
    return edges


def build_timeline_dot(events: list[dict[str, Any]]) -> str:
    nodes = sorted(agent_nodes(events))
    edges = extract_edges(events)
    lines = [
        "digraph G {",
        "  rankdir=LR;",
        "  node [shape=box, fontsize=10];",
    ]
    for node in nodes:
        safe = node.replace('"', '\\"')
        lines.append(f'  "{safe}";')
    for edge in edges:
        attrs = ["fontsize=9"]
        if edge.dashed:
            attrs.append("style=dashed")
        if edge.label:
            attrs.append(f'label="{edge.label.replace(chr(34), "")}"')
        attr_str = f" [{', '.join(attrs)}]" if attrs else ""
        lines.append(f'  "{edge.src}" -> "{edge.dst}"{attr_str};')
    lines.append("}")
    return "\n".join(lines)


def timeline_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in events:
        rows.append(
            {
                "time": event.get("timestamp"),
                "agent": event.get("agent_name"),
                "action": event.get("action"),
                "target": event.get("target_agent") or "—",
                "status": event.get("status"),
                "summary": event.get("output_summary") or event.get("input_summary"),
                "provider": event.get("provider"),
                "model": event.get("model"),
                "query_id": event.get("query_id"),
                "rows": event.get("rows"),
                "latency_ms": event.get("latency_ms"),
                "backend": event.get("backend"),
            }
        )
    return rows
