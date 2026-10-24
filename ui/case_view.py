"""Case page: brief, claim-versus-record cards, next action, controls, workload (lane P14-B)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from ui.client import ArbiterAPIError
from ui.components import (
    CAPTION_ACTIONS,
    CAPTION_CONTRADICTIONS,
    CAPTION_CONTROLS,
    CAPTION_COUNTERFACTUALS,
    CAPTION_TRACE,
    CASE_EMPTY,
    EMPTY_PRECEDENTS,
    NO_CONTRACTS,
    NO_CONTRADICTIONS,
    contract_card,
    contradiction_rows,
    control_table,
    counterfactual_line,
    humanise_outcome_reason,
    humanised_bullet,
    precedent_rows,
    see_raw,
)
from ui.labels_ui import (
    confidence_sentence,
    control_rows,
    outcome_label,
    outcome_meaning,
    stage_rows,
    workload_sentence,
)
from ui.models import ApprovalRequest
from ui.session import get_client
from ui.timeline import build_timeline_dot

MIN_RATIONALE = 30
ROLES = ["tprm_analyst", "tprm_lead"]
_ROLE_WORDS = {"tprm_analyst": "TPRM analyst", "tprm_lead": "TPRM lead", "vendor": "the vendor"}
_CAPABILITY_WORDS = {
    "outbox.email.draft": "email draft",
    "itsm.ticket.create": "service-desk ticket",
    "procurement.status.update": "procurement status change",
}
_STATE_SENTENCE = {
    "executed": "Done",
    "pending_approval": "Waiting for approval",
    "rejected": "Rejected",
    "expired": "Expired",
}


def approval_refusal(rationale: str) -> str | None:
    """Reason a rationale cannot be sent, or None. Checked before any API call."""
    if len(rationale.strip()) < MIN_RATIONALE:
        return f"Give a rationale of at least {MIN_RATIONALE} characters so the audit file explains it."
    return None


def _role_word(role: str) -> str:
    return _ROLE_WORDS.get(role, role.replace("_", " "))


def _same(a: str, b: str) -> bool:
    return a.strip().lower() == b.strip().lower()


def _card(heading: str, ref: dict[str, Any], *, mismatch: bool) -> None:
    with st.container(border=True):
        st.caption(heading)
        st.markdown(f"**{ref.get('source_label', '')}**")
        st.write(f"{ref.get('record_label', '')} · {ref.get('field_label', '')}")
        value = str(ref.get("value", ""))
        st.markdown(f":red[**{value}**]" if mismatch else f"**{value}**")
        if ref.get("quote"):
            st.markdown(f"> {ref['quote']}")


def render_brief(brief: dict[str, Any]) -> None:
    st.info(f"**{brief.get('headline', '')}**")
    for point in brief.get("why") or []:
        claim, record = point.get("claim"), point.get("record")
        if claim and record:
            mismatch = not _same(str(claim.get("value", "")), str(record.get("value", "")))
            st.markdown(f"**{point.get('text', '')}**")
            left, right = st.columns(2)
            with left:
                _card("Vendor claim", claim, mismatch=mismatch)
            with right:
                _card("System of record", record, mismatch=mismatch)
        else:
            st.markdown(f"- {point.get('text', '')}")


def _questions(client: Any) -> dict[str, str]:
    if "question_texts" not in st.session_state:
        try:
            items = client.questions()
        except (ArbiterAPIError, AttributeError):
            items = []
        st.session_state["question_texts"] = {i["question_id"]: i["question"] for i in items}
    return st.session_state["question_texts"]


def render_changes(client: Any, record: dict[str, Any]) -> None:
    titles = {c["control_id"]: c.get("title", "") for c in record.get("controls") or []}
    texts = _questions(client)
    items = record.get("counterfactuals") or []
    if not items:
        st.info("Nothing further is needed: every required control is already verified.")
    for item in items:
        st.markdown(f"**{item['control_id']} · {titles.get(item['control_id'], '')}**")
        for needed in item.get("evidence_required") or []:
            st.markdown(f"- [ ] {needed}")
        asked = [texts[q] for q in item.get("question_ids") or [] if q in texts]
        if asked:
            st.caption("Ask the vendor: " + " ".join(asked))


def _copy_button(text: str) -> None:
    components.html(
        "<button id='c' style='padding:6px 14px;font:14px sans-serif;cursor:pointer'>Copy</button>"
        "<script>const t=" + json.dumps(text).replace("</", "<\\/") + ";"
        "document.getElementById('c').onclick=()=>{navigator.clipboard.writeText(t);"
        "document.getElementById('c').innerText='Copied'};</script>",
        height=44,
    )


def _render_draft(draft: dict[str, Any], index: int) -> None:
    st.markdown(
        f"**To:** {_role_word(str(draft.get('to_role', '')))}  \n**Subject:** {draft.get('subject', '')}"
    )
    key = "draft_body" if index == 0 else f"draft_body_{index}"
    body = st.text_area(
        "Draft", value=draft.get("body", ""), height=280, key=key, label_visibility="collapsed"
    )
    copy_col, save_col, _ = st.columns([1, 1, 4])
    with copy_col:
        _copy_button(body)
    with save_col:
        st.download_button(
            "Download .txt",
            data=f"Subject: {draft.get('subject', '')}\n\n{body}\n",
            file_name=f"draft-{index + 1}.txt",
            key="dl_draft" if index == 0 else f"dl_draft_{index}",
        )


def _render_approval(client: Any, contract: dict[str, Any], case_id: str) -> None:
    what = _CAPABILITY_WORDS.get(str((contract.get("tool_plan") or [{}])[0].get("capability", "")), "action")
    needed = (contract.get("risk") or {}).get("approvals_required") or []
    st.warning(
        f"{case_id}: the {what} waits for approval"
        + (f" from the {_role_word(needed[0])}." if needed else ".")
    )
    cols = st.columns(2)
    role = cols[0].selectbox("Approving as", ROLES, format_func=_role_word, key="approve_role", index=1)
    name = cols[1].text_input("Your name", value="analyst", key="approve_by")
    rationale = st.text_area("Rationale (at least 30 characters)", key="approve_rationale")
    approve, reject, _ = st.columns([1, 1, 4])
    decision = None
    if approve.button("Approve", type="primary", key="approve_btn"):
        decision = "approve"
    if reject.button("Reject", key="reject_btn"):
        decision = "reject"
    if decision is None:
        return
    refusal = approval_refusal(rationale)
    if refusal:
        st.error(refusal)
        return
    body = ApprovalRequest(
        by=name.strip() or "analyst", role=role, decision=decision, rationale=rationale.strip()
    )
    try:
        result = client.approve_contract(contract["contract_id"], body)
    except ArbiterAPIError as exc:
        st.error(exc.message)
        return
    artifact = result.get("artifact")
    done = "approved" if decision == "approve" else "rejected"
    st.success(
        f"{case_id}: {what} {done}."
        + (f" Written to the outbox as {Path(artifact).name}." if artifact else "")
    )


def render_next_action(client: Any, detail: dict[str, Any], case_id: str) -> None:
    report = detail.get("report") or {}
    drafts = list(report.get("drafts") or [])
    if not drafts and report.get("clarification_email"):
        drafts = [report["clarification_email"]]
    for index, draft in enumerate(drafts):
        _render_draft(draft, index)
    contracts = list(detail.get("contracts") or [])
    if not contracts and not drafts:
        st.info("No action was drafted for this case.")
    for contract in contracts:
        what = _CAPABILITY_WORDS.get(
            str((contract.get("tool_plan") or [{}])[0].get("capability", "")), "action"
        )
        state = str(contract.get("state", ""))
        if state == "pending_approval":
            _render_approval(client, contract, case_id)
        elif state == "executed":
            st.success(f"{case_id}: the {what} was sent to the outbox.")
        else:
            st.info(f"{case_id}: the {what} is {_STATE_SENTENCE.get(state, state.replace('_', ' '))}.")


def _render_downloads(client: Any, case_id: str) -> None:
    cols = st.columns([1, 1, 4])
    for col, fmt, label, mime in (
        (cols[0], "html", "Dossier (HTML)", "text/html"),
        (cols[1], "md", "Dossier (Markdown)", "text/markdown"),
    ):
        try:
            data = client.dossier(case_id, fmt)
        except ArbiterAPIError as exc:
            col.error(exc.message)
            continue
        col.download_button(
            label, data=data, file_name=f"{case_id}-dossier.{fmt}", mime=mime, key=f"dl_{fmt}"
        )


def _render_technical(
    detail: dict[str, Any], record: dict[str, Any], report: dict[str, Any], trace: list[dict[str, Any]]
) -> None:
    """Everything an auditor needs, with identifiers. Collapsed so the page above stays in business terms."""
    with st.expander("Technical details"):
        st.caption("Identifiers for the audit file: reasons, facts, queries, contracts and the record.")
        for code in record.get("outcome_reasons") or []:
            st.markdown(f"- {humanised_bullet(str(code), humanise_outcome_reason(str(code)))}")
        st.markdown("**Controls and the facts behind them**")
        st.caption(CAPTION_CONTROLS)
        controls = list(record.get("controls") or [])
        control_table(controls, list(record.get("facts") or []))
        see_raw(controls)
        st.markdown("**Contradictions**")
        st.caption(CAPTION_CONTRADICTIONS)
        contradictions = list(record.get("contradictions") or [])
        if contradictions:
            st.dataframe(contradiction_rows(contradictions), hide_index=True)
        else:
            st.info(NO_CONTRADICTIONS)
        see_raw(contradictions)
        st.markdown("**Counterfactuals**")
        st.caption(CAPTION_COUNTERFACTUALS)
        counterfactuals = list(record.get("counterfactuals") or [])
        for item in counterfactuals:
            st.markdown(f"- {counterfactual_line(item)}")
        see_raw(counterfactuals)
        considered = list(record.get("precedents_considered") or [])
        see_raw(considered)
        st.markdown("**Signed contracts**")
        st.caption(CAPTION_ACTIONS)
        contracts = list(detail.get("contracts") or [])
        if not contracts:
            st.info(NO_CONTRACTS)
        for contract in contracts:
            with st.container(border=True):
                for label, value in contract_card(contract).items():
                    st.markdown(f"**{label}:** {value}")
        see_raw(contracts)
        for point in (report.get("brief") or {}).get("why") or []:
            if point.get("citations"):
                st.code(", ".join(point["citations"]))
        st.markdown("**Trace and raw data**")
        st.caption(CAPTION_TRACE)
        see_raw({"record": record, "report": report, "trace": trace})


def render_case() -> None:
    client = get_client()
    case_id = st.query_params.get("case_id") or st.session_state.get("nav_case_id")
    if not case_id:
        st.title("Case")
        st.caption("Decision record for one assessment.")
        st.info(CASE_EMPTY)
        return
    try:
        detail = client.get_case(str(case_id))
        trace = client.get_trace(str(case_id))
    except ArbiterAPIError as exc:
        st.title(str(case_id))
        st.caption("Decision record for one assessment.")
        st.error(exc.message)
        return
    record = detail.get("record") or {}
    report = detail.get("report") or {}
    vendor = str(detail.get("vendor") or "—")
    outcome = str(record.get("outcome", "ESCALATE"))
    st.title(f"{case_id} · {vendor}")
    st.caption(f"{record.get('run_id') or '—'} · {record.get('created_at') or '—'}")

    head_a, head_b, head_c = st.columns([3, 1, 1])
    with head_a:
        st.subheader(outcome_label(outcome))
        st.write(outcome_meaning(outcome))
    head_b.metric("Tier", str(record.get("tier") or "—"))
    head_c.metric("Residual risk", record.get("residual_risk", "—"))
    conf = record.get("confidence") or {}
    st.progress(
        max(0.0, min(1.0, float(conf.get("value", 0)))),
        text=confidence_sentence(conf, list(record.get("controls") or [])),
    )

    brief = report.get("brief")
    if brief:
        render_brief(brief)
    elif report.get("summary"):
        st.info(report["summary"])

    st.subheader("Next action")
    st.caption("The drafted message or ticket for this decision. Edit it, then copy or download.")
    render_next_action(client, detail, str(case_id))

    st.subheader("Controls")
    st.caption("Each required control, in business terms.")
    st.dataframe(control_rows(list(record.get("controls") or [])), hide_index=True)

    st.subheader("What would change this decision")
    st.caption("Evidence that would turn an unverified or failed control into a pass.")
    render_changes(client, record)

    st.subheader("Precedents considered")
    st.caption("Governed exceptions the policy looked at before deciding.")
    considered = list(record.get("precedents_considered") or [])
    if considered:
        candidates = list((record.get("policy_inputs") or {}).get("precedents") or [])
        st.dataframe(
            precedent_rows(considered, candidates=candidates, as_of=str(record.get("as_of") or "")),
            hide_index=True,
        )
    else:
        st.info(EMPTY_PRECEDENTS)

    st.subheader("Agent timeline")
    st.caption("What the agents did on this run, in order.")
    if trace:
        st.dataframe(stage_rows(trace), hide_index=True)
        with st.expander("Technical details: agent graph"):
            st.graphviz_chart(build_timeline_dot(trace))

    st.subheader("Workload")
    st.caption("Measured from this run.")
    if detail.get("workload"):
        st.markdown(f"**{workload_sentence(detail['workload'])}**")
    else:
        st.info("The workload was not recorded for this case.")

    st.subheader("Dossier")
    st.caption("The full decision file for the audit record.")
    _render_downloads(client, str(case_id))
    _render_technical(detail, record, report, trace)
