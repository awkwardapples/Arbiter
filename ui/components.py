"""Shared Streamlit renderers (lane P5-A)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import streamlit as st

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

OUTCOME_REASON_TEXT: dict[str, str] = {
    "CONTRADICTION": "Contradiction on a system-of-record claim",
    "CONTROL_FAILED": "One or more controls failed",
    "EVIDENCE_MISSING": "Evidence is missing for a required control",
    "LOW_CONFIDENCE_ABSTAIN": "Confidence below the gate — abstained",
    "HARD_GATE_DECLINE": "A hard gate requires decline",
    "HARD_GATE_ESCALATE": "A hard gate requires escalation",
    "ALL_REQUIRED_CONTROLS_MET": "All required controls met",
    "UNTRUSTED_CONTENT_TAMPERING": "Untrusted content tampering detected",
}

ELIGIBILITY_REASON_TEXT: dict[str, str] = {
    "mitigation_not_true": "The mitigation fact is not TRUE — this precedent can't apply",
    "no_exception_control_failing": "No exception-eligible control is failing",
    "non_exception_control_failing": "A control that can't be excepted is failing",
    "reviewer_authority": "The reviewer's role is below the required authority",
    "precedent_age": "The precedent is older than the 365-day window",
    "retrieval_quality": "H-MEM confidence or relevance is below the threshold",
    "tier_risk": "This case's risk tier is higher than the precedent's",
    "reviewer_role_insufficient": "The reviewer's role is below the required authority",
    "no_failing_controls": "No required control is failing",
    "decision_not_approving": "The review decision is not an approval",
}

REPLAY_CHECK_TEXT: dict[str, str] = {
    "policy_hash": "policy hash",
    "record_hash": "record hash",
    "contract_signatures": "contract signatures",
}


def humanise_outcome_reason(code: str) -> str:
    return OUTCOME_REASON_TEXT.get(code, code)


def humanise_eligibility_reason(code: str) -> str:
    return ELIGIBILITY_REASON_TEXT.get(code, code)


def replay_check_line(key: str, ok: bool) -> str:
    name = REPLAY_CHECK_TEXT.get(key, key.replace("_", " "))
    if ok:
        return f"✓ {name} matches"
    return f"✗ {name} mismatch"


def _display_value(value: Any) -> str:
    if value is None:
        return "null"
    return str(value)


def evidence_summary_line(fact: dict[str, Any]) -> str:
    key = fact.get("key")
    state = fact.get("state")
    return f"`{key}` = `{_display_value(fact.get('value'))}` → `{state}`"


def evidence_from_line(fact: dict[str, Any], provenance: dict[str, Any]) -> str:
    text = fact.get("evidence_text") or provenance.get("evidence_text") or provenance.get("quote")
    if not text:
        text = "No narrative is stored for this fact."
    return f"From: {text}"


def control_rows(controls: list[dict[str, Any]], facts: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Table rows for the case page. `rule_id` stays on the control and is not a column."""
    del facts
    rows: list[dict[str, str]] = []
    for ctrl in controls:
        fact_ids = [str(fid) for fid in ctrl.get("fact_ids") or []]
        rows.append(
            {
                "Control id": str(ctrl.get("control_id") or ""),
                "Name": str(ctrl.get("title") or ""),
                "Status": str(ctrl.get("state") or ""),
                "Fact ids": ", ".join(fact_ids) if fact_ids else "—",
            }
        )
    return rows


@dataclass
class TimelineFilters:
    agents: list[str] | None = None
    statuses: list[str] | None = None


def status_label(status: str) -> str:
    icon = STATUS_ICONS.get(status, "•")
    text = status.replace("_", " ").upper()
    return f"{icon} {text}"


def decision_badge(outcome: str) -> None:
    key = str(outcome)
    label = OUTCOME_LABELS.get(key, key)
    st.markdown(f"**{label}**")


def tier_chip(tier: str) -> None:
    st.markdown(f"**Tier {tier}**")


def confidence_gauge(value: float, gate: float, abstained: bool) -> None:
    pct = int(round(max(0.0, min(1.0, value)) * 100))
    st.progress(pct / 100.0, text=f"Confidence {pct}% (gate {int(gate * 100)}%)")
    if abstained:
        st.caption("Confidence abstained — decision did not meet the gate.")


def evidence_chip(provenance: dict[str, Any], *, fact: dict[str, Any] | None = None) -> None:
    parts = [provenance.get(key) for key in ("system", "query_id", "record_key", "field")]
    shown = [str(part) for part in parts if part]
    label = " · ".join(shown) if shown else str(provenance.get("kind") or "evidence")
    with st.expander(label, expanded=False):
        if fact is not None:
            st.markdown(evidence_summary_line(fact))
            st.markdown(evidence_from_line(fact, provenance))
            raw = {"key": fact.get("key"), "value": fact.get("value"), "state": fact.get("state")}
            with st.expander("See raw", expanded=False):
                st.code(json.dumps(raw, indent=2, sort_keys=True), language="json")
        elif provenance.get("quote"):
            st.write(provenance["quote"])


def control_table(controls: list[dict[str, Any]], facts: list[dict[str, Any]]) -> None:
    facts_by_id = {str(fact.get("fact_id")): fact for fact in facts}
    st.dataframe(control_rows(controls, facts), use_container_width=True, hide_index=True)
    for ctrl in controls:
        for fid in ctrl.get("fact_ids") or []:
            fact = facts_by_id.get(str(fid))
            provenance = (fact or {}).get("provenance") or []
            if fact and provenance:
                chip = provenance[0] if isinstance(provenance[0], dict) else {}
                evidence_chip(chip, fact=fact)


def glossary() -> None:
    st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)
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
