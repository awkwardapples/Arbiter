"""Page renderers for the reviewer console (lane P5-A)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from ui.client import ArbiterAPIError
from ui.components import (
    AUDIT_CAPTION,
    AUDIT_EVENTS_CAPTION,
    AUDIT_EVENTS_EMPTY,
    CAPTION_ACTIONS,
    CAPTION_CONTRADICTIONS,
    CAPTION_CONTROLS,
    CAPTION_COUNTERFACTUALS,
    CAPTION_PRECEDENTS,
    CAPTION_TIMELINE,
    CAPTION_TRACE,
    CASE_EMPTY,
    CONDITION_OPTIONS,
    CONDITIONS_HELP,
    DRY_RUN_NOTE,
    ELIGIBILITY_DISABLED,
    ELIGIBLE_CAPTION,
    ELIGIBLE_TITLE,
    EMPTY_PRECEDENTS,
    EVAL_CAPTION,
    EVAL_OFFLINE_CAPTION,
    INELIGIBLE_CAPTION,
    INELIGIBLE_TITLE,
    LEDGER_CAPTION,
    LIVE_CAPTION,
    MEMORY_CAPTION,
    MEMORY_CASE_CAPTION,
    MEMORY_CASE_HEADING,
    MEMORY_EMPTY,
    MITIGATION_FACT,
    MITIGATION_HELP,
    MITIGATION_OPTIONS,
    NEW_ASSESSMENT_CAPTION,
    NO_CONTRACTS,
    NO_CONTRADICTIONS,
    PRECEDENT_HELP,
    QUEUE_CAPTION,
    REPLAY_MATCH_CAPTION,
    REPLAY_MISMATCH_CAPTION,
    REPLAY_SECTION_CAPTION,
    RESULT_CAPTION,
    REVIEW_CAPTION,
    REVIEW_EMPTY,
    confidence_gauge,
    contract_card,
    contradiction_rows,
    control_table,
    counterfactual_line,
    decision_badge,
    humanise_eligibility_reason,
    humanise_outcome_reason,
    humanised_bullet,
    ledger_line,
    live_run_summary,
    memory_table_rows,
    precedent_rows,
    replay_check_line,
    review_conditions,
    see_raw,
    split_eval_summary,
    tier_chip,
    timeline,
)
from ui.models import ReviewRequest
from ui.session import get_client
from ui.validation import parse_case_input

EVAL_SUMMARY_PATH = Path(__file__).resolve().parents[1] / "eval/results/20261022T080517661769Z/summary.md"
_QUEUE_PAGE = Path(__file__).resolve().parent / "pages" / "queue.py"

ASSESSMENT_SPINNER = (
    "Running the assessment loop — this takes 2–5 seconds in sample mode, up to 60 seconds live…"
)
_DECISIONS = ["APPROVE", "APPROVE_WITH_CONDITIONS", "REQUEST_INFO", "ESCALATE", "DECLINE"]


def _section(title: str, caption: str) -> None:
    st.subheader(title)
    st.caption(caption)


def _show_eligibility(hint: dict[str, Any]) -> None:
    if hint.get("eligible"):
        st.success(ELIGIBLE_TITLE)
        st.caption(ELIGIBLE_CAPTION)
    else:
        st.warning(INELIGIBLE_TITLE)
        st.caption(INELIGIBLE_CAPTION)
        reasons = [str(code) for code in hint.get("reasons") or []]
        if reasons:
            with st.expander("Why not eligible?", expanded=False):
                for code in reasons:
                    st.markdown(f"- {humanised_bullet(code, humanise_eligibility_reason(code))}")
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


def _render_recorded(recorded: dict[str, Any]) -> None:
    case_id = str(recorded.get("case_id") or "")
    st.success(f"Review recorded for {case_id}.")
    result = recorded.get("result") if isinstance(recorded.get("result"), dict) else {}
    precedent = result.get("precedent") if isinstance(result.get("precedent"), dict) else None
    if precedent:
        st.dataframe(
            [
                {
                    "precedent_id": str(precedent.get("precedent_id") or ""),
                    "control_id": str(precedent.get("control_id") or ""),
                }
            ],
            hide_index=True,
        )
    see_raw(result)


def _precedent_reviews(detail: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for review in detail.get("reviews") or []:
        if not isinstance(review, dict) or review.get("create_precedent") is not True:
            continue
        rows.append(
            {
                "review_id": str(review.get("review_id") or ""),
                "decision": str(review.get("decision") or ""),
                "reviewer": str(review.get("reviewer") or ""),
            }
        )
    return rows


def _audit_events(client: Any) -> list[dict[str, Any]] | None:
    fetch = getattr(client, "audit_recent", None)
    if not callable(fetch):
        return []
    try:
        rows = fetch()
    except ArbiterAPIError as exc:
        st.error(exc.message)
        return None
    return list(rows) if isinstance(rows, list) else []


def _review_request(
    *,
    decision: str,
    rationale: str,
    mitigations: list[str],
    conditions: list[str],
    create_precedent: bool,
) -> ReviewRequest:
    return ReviewRequest(
        reviewer="reviewer@example.com",
        role="tprm_lead",
        decision=decision,  # type: ignore[arg-type]
        rationale=rationale,
        mitigations=mitigations,
        conditions=conditions,
        create_precedent=create_precedent,
    )


def page_new_assessment() -> None:
    st.title("New assessment")
    st.caption(NEW_ASSESSMENT_CAPTION)
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
        _section("Result", RESULT_CAPTION)
        st.success(f"Run {resp.get('status')} — case {case_id}")
        see_raw(resp)
        if output.get("case_id"):
            st.session_state["last_case_id"] = output["case_id"]
            st.session_state["nav_case_id"] = output["case_id"]


def page_queue() -> None:
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
    rows = [
        {
            "Case": str(item.get("case_id") or ""),
            "Vendor": str(item.get("vendor") or ""),
            "Outcome": str(item.get("outcome") or ""),
            "Tier": str(item.get("tier") or ""),
            "Residual risk": item.get("residual_risk"),
            "Status": str(item.get("status") or ""),
            "Created": str(item.get("created") or ""),
        }
        for item in items
    ]
    state = st.dataframe(
        rows,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="cases_table",
    )
    picked = list(state.selection.rows)
    if picked and picked[0] < len(rows):
        case_id = rows[picked[0]]["Case"]
        st.session_state["last_case_id"] = case_id
        st.session_state["nav_case_id"] = case_id
        st.switch_page("pages/case.py")


def page_case() -> None:
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
    vendor = str(detail.get("vendor") or "—")
    st.title(f"{case_id} · {vendor}")
    st.caption(f"{record.get('run_id') or '—'} · {record.get('created_at') or '—'}")
    outcome, tier, risk, confidence = st.columns(4)
    with outcome:
        st.caption("Outcome")
        decision_badge(str(record.get("outcome", "ESCALATE")))
    with tier:
        st.caption("Tier")
        tier_chip(str(record.get("tier") or "—"))
    with risk:
        st.metric("Residual risk", record.get("residual_risk", "—"))
    conf = record.get("confidence") or {}
    with confidence:
        confidence_gauge(
            float(conf.get("value", 0)),
            float(conf.get("gate", 1)),
            bool(conf.get("abstained", False)),
        )
    for code in record.get("outcome_reasons") or []:
        reason = str(code)
        st.markdown(f"- {humanised_bullet(reason, humanise_outcome_reason(reason))}")
    report = detail.get("report") or {}
    if report.get("summary"):
        st.write(report["summary"])
    _section("Controls", CAPTION_CONTROLS)
    controls = list(record.get("controls") or [])
    control_table(controls, list(record.get("facts") or []))
    see_raw(controls)
    _section("Timeline", CAPTION_TIMELINE)
    timeline(trace)
    see_raw(trace)
    _section("Contradictions", CAPTION_CONTRADICTIONS)
    contradictions = list(record.get("contradictions") or [])
    if contradictions:
        st.dataframe(contradiction_rows(contradictions), hide_index=True)
    else:
        st.info(NO_CONTRADICTIONS)
    see_raw(contradictions)
    _section("Counterfactuals", CAPTION_COUNTERFACTUALS)
    counterfactuals = list(record.get("counterfactuals") or [])
    for item in counterfactuals:
        st.markdown(f"- {counterfactual_line(item)}")
    see_raw(counterfactuals)
    _section("Precedents considered", CAPTION_PRECEDENTS)
    considered = list(record.get("precedents_considered") or [])
    if considered:
        candidates = list((record.get("policy_inputs") or {}).get("precedents") or [])
        st.dataframe(
            precedent_rows(considered, candidates=candidates, as_of=str(record.get("as_of") or "")),
            hide_index=True,
        )
    else:
        st.info(EMPTY_PRECEDENTS)
    see_raw(considered)
    _section("Actions", CAPTION_ACTIONS)
    contracts = list(detail.get("contracts") or [])
    if not contracts:
        st.info(NO_CONTRACTS)
    for contract in contracts:
        with st.container(border=True):
            for label, value in contract_card(contract).items():
                st.markdown(f"**{label}:** {value}")
    see_raw(contracts)
    _section("Trace and raw data", CAPTION_TRACE)
    see_raw({"record": record, "report": report, "trace": trace})


def page_review() -> None:
    st.title("Review")
    st.caption(REVIEW_CAPTION)
    client = get_client()
    try:
        items = client.list_cases()
    except ArbiterAPIError as exc:
        st.error(exc.message)
        return
    recorded = st.session_state.get("review_recorded")
    if not isinstance(recorded, dict):
        recorded = None
    if not items:
        if recorded:
            _render_recorded(recorded)
        else:
            st.info(REVIEW_EMPTY)
        return
    ids = [str(item.get("case_id")) for item in items]
    case_id = str(st.selectbox("Case", ids))
    decision_key = f"review_decision_{case_id}"
    rationale_key = f"review_rationale_{case_id}"
    if decision_key not in st.session_state:
        st.session_state[decision_key] = "APPROVE"
    if rationale_key not in st.session_state:
        st.session_state[rationale_key] = ""
    hint = _eligibility_hint(
        client,
        case_id,
        str(st.session_state[decision_key]),
        str(st.session_state[rationale_key]),
    )
    eligible = bool(hint and hint.get("eligible"))
    if hint is not None:
        _show_eligibility(hint)
    decision = str(st.selectbox("Decision", _DECISIONS, key=decision_key))
    rationale = str(st.text_area("Rationale (min 30 characters)", key=rationale_key))
    st.caption(f"{len(rationale)} characters")
    mitigation_key = f"review_mitigations_{case_id}"
    if mitigation_key not in st.session_state:
        st.session_state[mitigation_key] = [MITIGATION_FACT]
    mitigations = list(
        st.multiselect(
            "Mitigations",
            list(MITIGATION_OPTIONS),
            key=mitigation_key,
            disabled=not eligible,
            help=MITIGATION_HELP,
        )
    )
    if not eligible:
        st.caption(ELIGIBILITY_DISABLED)
    selected_conditions = list(
        st.multiselect(
            "Conditions",
            list(CONDITION_OPTIONS),
            key=f"review_conditions_{case_id}",
            disabled=not eligible,
            help=CONDITIONS_HELP,
        )
    )
    if not eligible:
        st.caption(ELIGIBILITY_DISABLED)
    other = str(st.text_input("Other condition", key=f"review_other_{case_id}", disabled=not eligible))
    if not eligible:
        st.caption(ELIGIBILITY_DISABLED)
    create_precedent = bool(
        st.checkbox(
            "Create precedent",
            key=f"review_precedent_{case_id}",
            disabled=not eligible,
            help=PRECEDENT_HELP,
        )
    )
    if not eligible:
        st.caption(ELIGIBILITY_DISABLED)
        mitigations = []
        selected_conditions = []
        other = ""
        create_precedent = False
    conditions = review_conditions(selected_conditions, other)
    submitted_col, dry_col = st.columns(2)
    with submitted_col:
        submitted = st.button("Submit", type="primary")
    with dry_col:
        dry = st.button("Dry-run")
    if submitted or dry:
        if len(rationale) < 30:
            st.error("Rationale must be at least 30 characters.")
        else:
            body = _review_request(
                decision=decision,
                rationale=rationale,
                mitigations=mitigations,
                conditions=conditions,
                create_precedent=create_precedent,
            )
            try:
                result = client.submit_review(case_id, body, dry_run=bool(dry and not submitted))
            except ArbiterAPIError as exc:
                st.error(exc.message)
            else:
                if dry and not submitted:
                    st.info(DRY_RUN_NOTE)
                    see_raw(result)
                else:
                    st.session_state["review_recorded"] = {"case_id": case_id, "result": result}
                    _render_recorded(st.session_state["review_recorded"])
    try:
        detail = client.get_case(case_id)
    except ArbiterAPIError as exc:
        st.error(exc.message)
        detail = {}
    reviews = _precedent_reviews(detail if isinstance(detail, dict) else {})
    if reviews:
        st.caption("Precedents recorded on this case.")
        st.dataframe(reviews, hide_index=True)
    recorded_now = st.session_state.get("review_recorded")
    if isinstance(recorded_now, dict) and str(recorded_now.get("case_id")) not in ids and not submitted:
        _render_recorded(recorded_now)


def _memory_case_heading() -> None:
    _section(MEMORY_CASE_HEADING, MEMORY_CASE_CAPTION)


def _render_memory_case(client: Any, items: list[dict[str, Any]]) -> None:
    _memory_case_heading()
    ids = [str(item.get("case_id")) for item in items]
    preferred = _preferred_case_id(client, items)
    index = ids.index(preferred) if preferred in ids else 0
    case_id = st.selectbox("Precedents considered on case", ids, index=index)
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
            hide_index=True,
        )
    else:
        st.info(EMPTY_PRECEDENTS)
    see_raw(considered)


def page_memory() -> None:
    st.title("Precedents")
    st.caption(MEMORY_CAPTION)
    client = get_client()
    try:
        precedents = client.list_precedents()
    except ArbiterAPIError as exc:
        st.error(exc.message)
        return
    rows = memory_table_rows(precedents)
    if rows:
        st.dataframe(rows, hide_index=True)
    else:
        st.info(MEMORY_EMPTY)
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


def page_audit() -> None:
    st.title("Audit")
    st.caption(AUDIT_CAPTION)
    client = get_client()
    with st.container(border=True):
        if st.button("Verify audit chain", type="primary"):
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
    _section("Recent events", AUDIT_EVENTS_CAPTION)
    events = _audit_events(client)
    if events:
        st.dataframe(events, hide_index=True)
    elif events is not None:
        st.info(AUDIT_EVENTS_EMPTY)
    if events is not None:
        see_raw(events)
    _section("Replay a case", REPLAY_SECTION_CAPTION)
    try:
        items = client.list_cases()
    except ArbiterAPIError as exc:
        st.error(exc.message)
        return
    if not items:
        st.info("No cases yet.")
        return
    ids = [str(item.get("case_id")) for item in items]
    case_id = str(st.selectbox("Case", ids))
    if st.button("Replay"):
        try:
            result = client.replay(case_id)
        except ArbiterAPIError as exc:
            st.error(exc.message)
        else:
            _render_replay(result)
            see_raw(result)


def page_evaluation() -> None:
    st.title("Evaluation")
    st.caption(EVAL_CAPTION)
    _section("Offline benchmark", EVAL_OFFLINE_CAPTION)
    client = get_client()
    if EVAL_SUMMARY_PATH.is_file():
        _render_eval_markdown(EVAL_SUMMARY_PATH.read_text(encoding="utf-8"))
    else:
        try:
            latest = client.eval_latest()
            _render_eval_markdown(str(latest.get("markdown", latest)))
        except ArbiterAPIError as exc:
            if exc.status_code == 404:
                st.info("Evaluation results are not published yet.")
            else:
                st.error(exc.message)
    _section("Live runs on this instance", LIVE_CAPTION)
    try:
        health = client.health()
        cases = client.list_cases()
    except ArbiterAPIError as exc:
        st.error(exc.message)
        return
    summary = live_run_summary(cases if isinstance(cases, list) else [], health)
    cases_col, recent_col, data_col, llm_col = st.columns(4)
    cases_col.metric("Cases", summary["n"])
    recent_col.metric("Most recent", summary["latest"])
    data_col.metric("Data backend", summary["data_backend"])
    llm_col.metric("LLM provider", summary["llm_provider"])
    st.page_link(str(_QUEUE_PAGE), label="Cases")
