"""Page renderers for the reviewer console (lane P5-A)."""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

from ui.client import ArbiterAPIError
from ui.components import (
    confidence_gauge,
    control_table,
    decision_badge,
    humanise_eligibility_reason,
    humanise_outcome_reason,
    replay_check_line,
    tier_chip,
    timeline,
)
from ui.models import ReviewRequest
from ui.session import get_client
from ui.validation import parse_case_input

ASSESSMENT_SPINNER = (
    "Running the assessment loop — this takes 2–5 seconds in sample mode, up to 60 seconds live…"
)


def _render_eligibility(hint: dict[str, Any]) -> None:
    reasons = [str(code) for code in hint.get("reasons") or []]
    if hint.get("eligible") and not reasons:
        st.success("Eligible to create a precedent")
        return
    for code in reasons:
        st.markdown(f"- {humanise_eligibility_reason(code)}")
        st.caption(code)


def _chain_intact_text(result: dict[str, Any], client: Any) -> str:
    count = result.get("entries")
    if isinstance(count, bool) or not isinstance(count, int):
        try:
            health = client.health()
        except ArbiterAPIError:
            return "Chain intact"
        count = health.get("audit_chain_length") if isinstance(health, dict) else None
    if isinstance(count, bool) or not isinstance(count, int):
        return "Chain intact"
    return f"Chain intact — {count} entries across all cases"


def _render_replay(result: dict[str, Any]) -> None:
    if result.get("match"):
        st.success("Match — the decision replays identically")
    else:
        st.error("Mismatch — see diff")
        for item in result.get("diff") or []:
            st.markdown(f"- {item}")
    checks = result.get("checks") or {}
    if isinstance(checks, dict):
        for key, ok in checks.items():
            st.markdown(replay_check_line(str(key), bool(ok)))


def page_new_assessment() -> None:
    st.header("New assessment")
    client = get_client()
    mode = st.radio("Intake", ["Pick vendor", "Paste / upload JSON"], horizontal=True)
    case_input = None
    errors: list[str] = []
    if mode == "Pick vendor":
        try:
            vendors = client.list_vendors()
        except ArbiterAPIError as exc:
            st.error(exc.message)
            return
        labels = {str(v.get("vendor_id", v.get("legal_name", "vendor"))): v for v in vendors}
        pick = st.selectbox("Vendor", sorted(labels) if labels else ["—"])
        if pick and pick != "—":
            case_input, errors = parse_case_input({"vendor_id": pick})
    else:
        uploaded = st.file_uploader("Upload JSON", type=["json"])
        raw_text = st.text_area("Or paste JSON", height=200)
        payload: str | dict[str, Any] | None = None
        if uploaded is not None:
            payload = uploaded.read().decode("utf-8")
        elif raw_text.strip():
            payload = raw_text
        if payload is not None:
            case_input, errors = parse_case_input(payload)
    if errors:
        for err in errors:
            st.error(err)
    if st.button("Run assessment", type="primary", disabled=case_input is None):
        if case_input is None:
            return
        with st.spinner(ASSESSMENT_SPINNER):
            try:
                resp = client.run(case_input)
            except ArbiterAPIError as exc:
                st.error(exc.message)
                return
        output = resp.get("output") or {}
        case_id = output.get("case_id", "unknown")
        st.success(f"Run {resp.get('status')} — case {case_id}")
        if output.get("case_id"):
            st.session_state["last_case_id"] = output["case_id"]
            st.session_state["nav_case_id"] = output["case_id"]


def page_queue() -> None:
    st.header("Queue")
    client = get_client()
    try:
        items = client.list_cases()
    except ArbiterAPIError as exc:
        st.error(exc.message)
        return
    outcomes = sorted({str(i.get("outcome")) for i in items})
    tiers = sorted({str(i.get("tier")) for i in items})
    fo = st.multiselect("Filter outcome", outcomes, default=outcomes)
    ft = st.multiselect("Filter tier", tiers, default=tiers)
    for item in items:
        if str(item.get("outcome")) not in fo or str(item.get("tier")) not in ft:
            continue
        with st.container(border=True):
            decision_badge(str(item.get("outcome")))
            st.write(
                f"{item.get('case_id')} · {item.get('vendor')} · "
                f"risk {item.get('residual_risk')} · {item.get('status')}"
            )
            tier_chip(str(item.get("tier")))
            if st.button("Open case", key=f"open_{item.get('case_id')}"):
                case_id = item.get("case_id")
                st.session_state["last_case_id"] = case_id
                st.session_state["nav_case_id"] = case_id
                st.switch_page("pages/case.py")


def page_case() -> None:
    st.header("Case")
    client = get_client()
    case_id = st.query_params.get("case_id") or st.session_state.get("nav_case_id")
    if not case_id:
        st.info("Select a case from the queue or run a new assessment.")
        return
    try:
        detail = client.get_case(str(case_id))
        trace = client.get_trace(str(case_id))
    except ArbiterAPIError as exc:
        st.error(exc.message)
        return
    record = detail.get("record", {})
    decision_badge(str(record.get("outcome", "ESCALATE")))
    for code in record.get("outcome_reasons") or []:
        reason = str(code)
        st.markdown(f"- {humanise_outcome_reason(reason)}")
        st.caption(reason)
    report = detail.get("report") or {}
    if report.get("summary"):
        st.write(report["summary"])
    conf = record.get("confidence", {})
    confidence_gauge(
        float(conf.get("value", 0)),
        float(conf.get("gate", 1)),
        bool(conf.get("abstained", False)),
    )
    st.subheader("Why")
    control_table(list(record.get("controls") or []), list(record.get("facts") or []))
    st.subheader("Contradictions")
    for row in record.get("contradictions", []):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Claim**")
            st.write(row.get("claim_value"))
        with c2:
            st.markdown("**System of record**")
            st.write(row.get("sor_value"))
    st.subheader("What would change this")
    for cf in record.get("counterfactuals", []):
        st.checkbox(
            f"{cf.get('control_id')}: verify {', '.join(cf.get('evidence_required', []))}",
            value=False,
            disabled=True,
        )
    st.subheader("Precedents")
    for pref in record.get("precedents_considered", []):
        st.write(f"{pref.get('precedent_id')} · {pref.get('control_id')} · applied={pref.get('applied')}")
    st.subheader("Actions")
    for contract in detail.get("contracts", []):
        st.json(contract)
    st.subheader("Agent timeline")
    timeline(trace)
    st.subheader("Report")
    if report.get("rationale"):
        for block in report["rationale"]:
            st.write(block.get("text", ""))
    with st.expander("Raw JSON"):
        st.json({"record": record, "report": detail.get("report")})


def page_review() -> None:
    st.header("Review")
    client = get_client()
    try:
        items = client.list_cases()
    except ArbiterAPIError as exc:
        st.error(exc.message)
        return
    ids = [str(i.get("case_id")) for i in items]
    case_id = st.selectbox("Case", ids if ids else ["—"])
    if case_id == "—":
        return
    decision = st.selectbox(
        "Decision",
        ["APPROVE", "APPROVE_WITH_CONDITIONS", "REQUEST_INFO", "ESCALATE", "DECLINE"],
    )
    rationale = st.text_area("Rationale (min 30 characters)")
    st.caption(f"{len(rationale)} characters")
    mitigations = st.text_input("Mitigations (comma-separated)")
    conditions = st.text_input("Conditions (comma-separated)")
    create_precedent = st.checkbox("Create precedent")
    if create_precedent and st.button("Check eligibility"):
        body = ReviewRequest(
            reviewer="reviewer@example.com",
            role="tprm_lead",
            decision=decision,  # type: ignore[arg-type]
            rationale=rationale if len(rationale) >= 30 else "x" * 30,
            mitigations=[m.strip() for m in mitigations.split(",") if m.strip()],
            conditions=[c.strip() for c in conditions.split(",") if c.strip()],
            create_precedent=True,
        )
        try:
            hint = client.submit_review(case_id, body, dry_run=True)
        except ArbiterAPIError as exc:
            st.warning(exc.message)
        else:
            _render_eligibility(hint)
    if st.button("Submit review", type="primary"):
        if len(rationale) < 30:
            st.error("Rationale must be at least 30 characters.")
            return
        body = ReviewRequest(
            reviewer="reviewer@example.com",
            role="tprm_lead",
            decision=decision,  # type: ignore[arg-type]
            rationale=rationale,
            mitigations=[m.strip() for m in mitigations.split(",") if m.strip()],
            conditions=[c.strip() for c in conditions.split(",") if c.strip()],
            create_precedent=create_precedent,
        )
        try:
            result = client.submit_review(case_id, body)
            st.success(json.dumps(result))
        except ArbiterAPIError as exc:
            st.error(exc.message)


def page_memory() -> None:
    st.header("Memory")
    client = get_client()
    try:
        precedents = client.list_precedents()
    except ArbiterAPIError as exc:
        st.error(exc.message)
        return
    st.dataframe(precedents, use_container_width=True)
    try:
        items = client.list_cases()
    except ArbiterAPIError:
        items = []
    case_id = st.selectbox(
        "Precedents considered on case",
        [str(i.get("case_id")) for i in items] if items else ["—"],
    )
    if case_id != "—":
        detail = client.get_case(case_id)
        st.json(detail.get("record", {}).get("precedents_considered", []))
    st.caption(
        "Full H-MEM retrieval JSONL is not exposed via the API; this view uses precedents endpoints only."
    )


def page_audit() -> None:
    st.header("Audit")
    client = get_client()
    if st.button("Verify audit chain"):
        try:
            result = client.audit_verify()
        except ArbiterAPIError as exc:
            st.error(exc.message)
        else:
            if result.get("ok"):
                st.success(_chain_intact_text(result, client))
            else:
                st.error(f"Chain broken at sequence {result['first_bad_seq']}")
    try:
        items = client.list_cases()
    except ArbiterAPIError as exc:
        st.error(exc.message)
        return
    for item in items:
        cid = str(item.get("case_id"))
        if st.button(f"Replay {cid}", key=f"replay_{cid}"):
            try:
                _render_replay(client.replay(cid))
            except ArbiterAPIError as exc:
                st.error(exc.message)


def page_evaluation() -> None:
    st.header("Evaluation")
    client = get_client()
    try:
        latest = client.eval_latest()
        st.markdown(str(latest.get("markdown", latest)))
    except ArbiterAPIError as exc:
        if exc.status_code == 404:
            st.info("Evaluation results are not published yet.")
        else:
            st.error(exc.message)
