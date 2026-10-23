"""Page renderers for the reviewer console (lane P5-A)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from ui.client import ArbiterAPIError
from ui.components import (
    AUDIT_CAPTION,
    C05_EXPLANATION,
    C05_HEADING,
    CAPTION_ACTIONS,
    CAPTION_CONTRADICTIONS,
    CAPTION_COUNTERFACTUALS,
    CAPTION_PRECEDENTS,
    CAPTION_TIMELINE,
    CONDITIONS_HELP,
    EMPTY_PRECEDENTS,
    EVAL_CAPTION,
    EVAL_OFFLINE_CAPTION,
    HOW_TO_READ,
    HOW_TO_USE,
    LEDGER_CAPTION,
    MEMORY_CASE_CAPTION,
    MEMORY_INTRO,
    MITIGATION_FACT,
    MITIGATION_HELP,
    NEW_ASSESSMENT_CAPTION,
    NO_CONTRACTS,
    NO_CONTRADICTIONS,
    PRECEDENT_HELP,
    QUEUE_CAPTION,
    REPLAY_MATCH_CAPTION,
    REPLAY_MISMATCH_CAPTION,
    REVIEW_EMPTY,
    REVIEW_INTRO,
    confidence_gauge,
    contract_card,
    contradiction_rows,
    control_table,
    counterfactual_line,
    decision_badge,
    eligibility_body,
    humanise_outcome_reason,
    humanised_bullet,
    ledger_line,
    memory_table_rows,
    precedent_rows,
    replay_check_line,
    see_raw,
    split_eval_summary,
    tier_chip,
    timeline,
)
from ui.models import ReviewRequest
from ui.session import get_client
from ui.validation import parse_case_input

EVAL_SUMMARY_PATH = Path(__file__).resolve().parents[1] / "eval/results/20261022T080517661769Z/summary.md"

ASSESSMENT_SPINNER = (
    "Running the assessment loop — this takes 2–5 seconds in sample mode, up to 60 seconds live…"
)


def _show_eligibility(hint: dict[str, Any]) -> None:
    body = eligibility_body(hint)
    if hint.get("eligible"):
        st.success(body)
    else:
        st.warning(body)
    see_raw(hint)


def _eligibility_hint(client: Any, case_id: str, decision: str, rationale: str) -> dict[str, Any] | None:
    body = ReviewRequest(
        reviewer="reviewer@example.com",
        role="tprm_lead",
        decision=decision,  # type: ignore[arg-type]
        rationale=rationale if len(rationale) >= 30 else "x" * 30,
        mitigations=[],
        conditions=[],
        create_precedent=True,
    )
    try:
        hint = client.submit_review(case_id, body, dry_run=True)
    except ArbiterAPIError as exc:
        st.warning(exc.message)
        return None
    return hint if isinstance(hint, dict) else None


def _preferred_case_id(client: Any, items: list[dict[str, Any]]) -> str | None:
    ranked = sorted(items, key=lambda item: str(item.get("created") or ""), reverse=True)
    fallback = str(ranked[0].get("case_id")) if ranked else None
    for item in ranked:
        case_id = str(item.get("case_id") or "")
        if not case_id:
            continue
        try:
            detail = client.get_case(case_id)
        except ArbiterAPIError:
            continue
        considered = (detail.get("record") or {}).get("precedents_considered") or []
        if considered:
            return case_id
    return fallback


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


def _render_eval_markdown(text: str) -> None:
    head, tail = split_eval_summary(text)
    st.markdown(head)
    if "Synthetic data. Small n." in head:
        st.caption(EVAL_OFFLINE_CAPTION)
    if tail:
        st.markdown(tail)


def _render_replay(result: dict[str, Any]) -> None:
    if result.get("match"):
        st.success("Match — the decision replays identically")
        st.caption(REPLAY_MATCH_CAPTION)
    else:
        st.error("Mismatch — see diff")
        st.caption(REPLAY_MISMATCH_CAPTION)
        for item in result.get("diff") or []:
            st.markdown(f"- {item}")
    checks = result.get("checks") or {}
    if isinstance(checks, dict):
        for key, ok in checks.items():
            st.markdown(replay_check_line(str(key), bool(ok)))


def page_new_assessment() -> None:
    st.header("New assessment")
    st.caption(NEW_ASSESSMENT_CAPTION)
    with st.expander("How to use this app", expanded=False):
        st.markdown(HOW_TO_USE)
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
    st.caption(QUEUE_CAPTION)
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
    with st.expander("How to read this", expanded=True):
        st.markdown(HOW_TO_READ)
    decision_badge(str(record.get("outcome", "ESCALATE")))
    st.subheader(str(case_id))
    for code in record.get("outcome_reasons") or []:
        reason = str(code)
        st.markdown(f"- {humanised_bullet(reason, humanise_outcome_reason(reason))}")
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
    st.caption(CAPTION_CONTRADICTIONS)
    contradictions = list(record.get("contradictions") or [])
    if contradictions:
        st.dataframe(contradiction_rows(contradictions), use_container_width=True, hide_index=True)
    else:
        st.markdown(NO_CONTRADICTIONS)
    see_raw(contradictions)
    st.subheader("What would change this")
    st.caption(CAPTION_COUNTERFACTUALS)
    counterfactuals = list(record.get("counterfactuals") or [])
    st.markdown("**Evidence that would change this decision**")
    for item in counterfactuals:
        st.markdown(f"- {counterfactual_line(item)}")
    see_raw(counterfactuals)
    st.subheader("Precedents")
    st.caption(CAPTION_PRECEDENTS)
    considered = list(record.get("precedents_considered") or [])
    if considered:
        candidates = list((record.get("policy_inputs") or {}).get("precedents") or [])
        st.dataframe(
            precedent_rows(considered, candidates=candidates, as_of=str(record.get("as_of") or "")),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.markdown(EMPTY_PRECEDENTS)
    see_raw(considered)
    st.subheader("Actions")
    st.caption(CAPTION_ACTIONS)
    contracts = list(detail.get("contracts") or [])
    if not contracts:
        st.markdown(NO_CONTRACTS)
    for contract in contracts:
        with st.container(border=True):
            for label, value in contract_card(contract).items():
                st.markdown(f"**{label}:** {value}")
    see_raw(contracts)
    st.subheader("Agent timeline")
    st.caption(CAPTION_TIMELINE)
    timeline(trace)
    st.subheader("Report")
    if report.get("rationale"):
        for block in report["rationale"]:
            st.write(block.get("text", ""))
    see_raw({"record": record, "report": detail.get("report")})


def page_review() -> None:
    st.header("Review")
    with st.container(border=True):
        st.markdown(REVIEW_INTRO)
    st.subheader(C05_HEADING)
    st.markdown(C05_EXPLANATION)
    client = get_client()
    try:
        items = client.list_cases()
    except ArbiterAPIError as exc:
        st.error(exc.message)
        return
    if not items:
        st.info(REVIEW_EMPTY)
        return
    ids = [str(i.get("case_id")) for i in items]
    case_id = st.selectbox("Case", ids)
    st.subheader(f"Selected case · {case_id}")
    check_slot = st.empty()
    decision = st.selectbox(
        "Decision",
        ["APPROVE", "APPROVE_WITH_CONDITIONS", "REQUEST_INFO", "ESCALATE", "DECLINE"],
    )
    rationale = st.text_area("Rationale (min 30 characters)")
    st.caption(f"{len(rationale)} characters")
    clicked = check_slot.button("Check eligibility")
    st.markdown("**Eligibility status**")
    hint = _eligibility_hint(client, str(case_id), str(decision), rationale)
    if clicked:
        retried = _eligibility_hint(client, str(case_id), str(decision), rationale)
        if retried is not None:
            hint = retried
    if hint is not None:
        _show_eligibility(hint)
    mkey = f"review_mitigations_{case_id}"
    if hint is not None and hint.get("eligible") and mkey not in st.session_state:
        st.session_state[mkey] = MITIGATION_FACT
    mitigations = st.text_input("Mitigations (comma-separated)", key=mkey, help=MITIGATION_HELP)
    conditions = st.text_input("Conditions (comma-separated)", help=CONDITIONS_HELP)
    create_precedent = st.checkbox("Create precedent", help=PRECEDENT_HELP)
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
        except ArbiterAPIError as exc:
            st.error(exc.message)
        else:
            st.success(f"Review recorded for {case_id}.")
            see_raw(result)


def _memory_case_heading() -> None:
    st.subheader("Precedents considered on a specific case")
    st.caption(MEMORY_CASE_CAPTION)


def _render_memory_case(client: Any, items: list[dict[str, Any]]) -> None:
    _memory_case_heading()
    ids = [str(item.get("case_id")) for item in items]
    preferred = _preferred_case_id(client, items)
    index = ids.index(preferred) if preferred in ids else 0
    case_id = st.selectbox("Precedents considered on case", ids, index=index)
    st.subheader(f"Selected case · {case_id}")
    try:
        detail = client.get_case(str(case_id))
    except ArbiterAPIError as exc:
        st.error(exc.message)
        return
    record = detail.get("record") or {}
    considered = list(record.get("precedents_considered") or [])
    if considered:
        candidates = list((record.get("policy_inputs") or {}).get("precedents") or [])
        st.dataframe(
            precedent_rows(considered, candidates=candidates, as_of=str(record.get("as_of") or "")),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.markdown(EMPTY_PRECEDENTS)
    see_raw(considered)


def page_memory() -> None:
    st.header("Memory")
    with st.container(border=True):
        st.markdown(MEMORY_INTRO)
    client = get_client()
    try:
        precedents = client.list_precedents()
    except ArbiterAPIError as exc:
        st.error(exc.message)
        return
    rows = memory_table_rows(precedents)
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.markdown("No precedents are stored yet.")
    if precedents:
        st.caption(LEDGER_CAPTION)
    for item in precedents:
        if not isinstance(item, dict):
            continue
        st.markdown(f"**{item.get('precedent_id') or 'precedent'}**")
        entries = item.get("ledger") or []
        if not entries:
            st.caption("No ledger entries.")
        for entry in entries:
            if isinstance(entry, dict):
                st.markdown(f"- {ledger_line(entry)}")
    see_raw(precedents)
    try:
        items = client.list_cases()
    except ArbiterAPIError:
        items = []
    if not items:
        _memory_case_heading()
        st.selectbox("Precedents considered on case", ["—"])
    else:
        _render_memory_case(client, items)
    st.caption(
        "Full H-MEM retrieval JSONL is not exposed via the API; this view uses precedents endpoints only."
    )


def page_audit() -> None:
    st.header("Audit")
    st.caption(AUDIT_CAPTION)
    client = get_client()
    active = st.session_state.get("nav_case_id") or st.session_state.get("last_case_id")
    with st.container(border=True):
        st.markdown(f"**Active case · {active}**" if active else "**Active case · —**")
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
                see_raw(result)
    try:
        items = client.list_cases()
    except ArbiterAPIError as exc:
        st.error(exc.message)
        return
    for item in items:
        cid = str(item.get("case_id"))
        if st.button(f"Replay {cid}", key=f"replay_{cid}"):
            st.session_state["nav_case_id"] = cid
            with st.container(border=True):
                st.markdown(f"**{cid}**")
                try:
                    result = client.replay(cid)
                except ArbiterAPIError as exc:
                    st.error(exc.message)
                else:
                    _render_replay(result)
                    see_raw(result)


def page_evaluation() -> None:
    st.header("Evaluation")
    st.caption(EVAL_CAPTION)
    if EVAL_SUMMARY_PATH.is_file():
        _render_eval_markdown(EVAL_SUMMARY_PATH.read_text(encoding="utf-8"))
        return
    client = get_client()
    try:
        latest = client.eval_latest()
        _render_eval_markdown(str(latest.get("markdown", latest)))
    except ArbiterAPIError as exc:
        if exc.status_code == 404:
            st.info("Evaluation results are not published yet.")
        else:
            st.error(exc.message)
