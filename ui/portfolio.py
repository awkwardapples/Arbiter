"""Cases page: portfolio summary, filters and the case table (lane P14-B)."""

from __future__ import annotations

from typing import Any

import streamlit as st

from ui.client import ArbiterAPIError
from ui.components import QUEUE_CAPTION
from ui.labels_ui import outcome_label, portfolio_metrics
from ui.session import get_client

_PENDING_SCAN_LIMIT = 40


def _pending_approvals(client: Any, items: list[dict[str, Any]]) -> int:
    pending = 0
    for item in items[:_PENDING_SCAN_LIMIT]:
        try:
            detail = client.get_case(str(item.get("case_id")))
        except ArbiterAPIError:
            continue
        pending += sum(1 for c in detail.get("contracts") or [] if c.get("state") == "pending_approval")
    return pending


def render_portfolio() -> None:
    st.title("Cases")
    st.caption(QUEUE_CAPTION)
    client = get_client()
    try:
        items = client.list_cases()
    except ArbiterAPIError as exc:
        st.error(exc.message)
        return
    if not items:
        st.info("No cases yet.")
        return
    metrics = portfolio_metrics(items)
    columns = st.columns(2 + len(metrics["by_outcome"]))
    columns[0].metric("Cases", metrics["total"])
    columns[1].metric("Waiting for approval", _pending_approvals(client, items))
    for column, (outcome, count) in zip(columns[2:], sorted(metrics["by_outcome"].items()), strict=False):
        column.metric(outcome_label(outcome), count)
    left, right = st.columns(2)
    outcomes = left.multiselect(
        "Outcome", sorted(metrics["by_outcome"]), format_func=outcome_label, key="f_outcome"
    )
    tiers = right.multiselect("Tier", sorted({str(i.get("tier")) for i in items}), key="f_tier")
    shown = [
        i
        for i in items
        if (not outcomes or i.get("outcome") in outcomes) and (not tiers or str(i.get("tier")) in tiers)
    ]
    rows = [
        {
            "Case": str(item.get("case_id") or ""),
            "Vendor": str(item.get("vendor") or ""),
            "Decision": outcome_label(str(item.get("outcome") or "")),
            "Tier": str(item.get("tier") or ""),
            "Residual risk": item.get("residual_risk"),
            "Created": str(item.get("created") or "")[:10],
        }
        for item in shown
    ]
    state = st.dataframe(
        rows, hide_index=True, on_select="rerun", selection_mode="single-row", key="cases_table"
    )
    picked = list(state.selection.rows)
    if picked and picked[0] < len(rows):
        case_id = rows[picked[0]]["Case"]
        st.session_state["last_case_id"] = case_id
        st.session_state["nav_case_id"] = case_id
        st.switch_page("pages/case.py")
