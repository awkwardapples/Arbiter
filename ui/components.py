"""Shared Streamlit renderers (lane P5-A)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st

from app.schemas.common import Outcome, Provenance, Tier
from app.schemas.decision import ControlResult
from app.schemas.evidence import Fact
from ui.timeline import build_timeline_dot, timeline_rows

OUTCOME_LABELS: dict[str, str] = {
    "APPROVE": "✓ APPROVE",
    "APPROVE_WITH_CONDITIONS": "✓ APPROVE_WITH_CONDITIONS",
    "REQUEST_INFO": "? REQUEST_INFO",
    "ESCALATE": "⬆ ESCALATE",
    "DECLINE": "✗ DECLINE",
}

TRACE_STATUSES: tuple[str, ...] = (
    "success",
    "needs_revision",
    "retrying",
    "fallback",
    "blocked",
    "escalated",
    "partial_success",
    "error",
    "pending_approval",
)

STATUS_ICONS: dict[str, str] = {
    "success": "✓",
    "needs_revision": "↻",
    "retrying": "↻",
    "fallback": "⚠",
    "blocked": "⛔",
    "escalated": "⬆",
    "partial_success": "◐",
    "error": "✗",
    "pending_approval": "⏳",
}


@dataclass
class TimelineFilters:
    agents: list[str] | None = None
    statuses: list[str] | None = None


def status_label(status: str) -> str:
    icon = STATUS_ICONS.get(status, "•")
    text = status.replace("_", " ").upper()
    return f"{icon} {text}"


def decision_badge(outcome: Outcome | str) -> None:
    key = str(outcome)
    label = OUTCOME_LABELS.get(key, key)
    st.markdown(f"**{label}**")


def tier_chip(tier: Tier | str) -> None:
    st.markdown(f"**Tier {tier}**")


def confidence_gauge(value: float, gate: float, abstained: bool) -> None:
    pct = int(round(max(0.0, min(1.0, value)) * 100))
    st.progress(pct / 100.0, text=f"Confidence {pct}% (gate {int(gate * 100)}%)")
    if abstained:
        st.caption("Confidence abstained — decision did not meet the gate.")


def evidence_chip(provenance: Provenance, *, fact: Fact | None = None) -> None:
    parts = [
        p
        for p in (
            provenance.system,
            provenance.query_id,
            provenance.record_key,
            provenance.field,
        )
        if p
    ]
    label = " · ".join(parts) if parts else provenance.kind
    with st.expander(label, expanded=False):
        if provenance.quote:
            st.write(provenance.quote)
        if fact is not None:
            st.json({"key": fact.key, "value": fact.value, "state": fact.state})


def control_table(controls: list[ControlResult], facts: list[Fact]) -> None:
    facts_by_id = {f.fact_id: f for f in facts}
    rows = []
    for ctrl in controls:
        cited = ", ".join(ctrl.fact_ids) if ctrl.fact_ids else "—"
        rows.append(
            {
                "Control": ctrl.control_id,
                "Title": ctrl.title,
                "State": ctrl.state,
                "Rule": ctrl.rule_id,
                "Facts": cited,
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)
    for ctrl in controls:
        for fid in ctrl.fact_ids:
            fact = facts_by_id.get(fid)
            if fact and fact.provenance:
                evidence_chip(fact.provenance[0], fact=fact)


def glossary() -> None:
    with st.expander("Glossary", expanded=False):
        st.markdown(
            """
- **SoR (system of record):** authoritative enterprise data federated via Zetaris or DuckDB sample mode.
- **KEV:** CISA Known Exploited Vulnerabilities catalogue.
- **USL:** Zetaris unified semantic layer over onboarded sources.
- **DQ:** data-quality rules applied to query results.
- **Precedent:** governed human exception stored in H-MEM when policy allows.
- **Counterfactual:** evidence that would flip a failing control if verified.
            """
        )


def timeline(events: list[dict[str, Any]], *, filters: TimelineFilters | None = None) -> None:
    if not events:
        st.info("No trace events for this case.")
        return
    agents = sorted({str(e.get("agent_name")) for e in events if e.get("agent_name")})
    statuses = sorted({str(e.get("status")) for e in events if e.get("status")})
    f = filters or TimelineFilters()
    selected_agents = f.agents if f.agents is not None else agents
    selected_statuses = f.statuses if f.statuses is not None else statuses
    col1, col2 = st.columns(2)
    with col1:
        agent_pick = st.multiselect("Filter agents", agents, default=selected_agents, key="tl_agents")
    with col2:
        status_pick = st.multiselect("Filter status", statuses, default=selected_statuses, key="tl_status")
    filtered = [
        e for e in events if str(e.get("agent_name")) in agent_pick and str(e.get("status")) in status_pick
    ]
    st.subheader("Agent collaboration graph")
    st.graphviz_chart(build_timeline_dot(filtered))
    st.subheader("Agent timeline")
    table = timeline_rows(filtered)
    for row in table:
        row["status"] = status_label(str(row.get("status", "")))
        if row.get("provider") == "meterless" or row.get("backend") == "zetaris":
            row["agent"] = f"{row.get('agent')} (sponsor)"
    st.dataframe(table, use_container_width=True, hide_index=True)
