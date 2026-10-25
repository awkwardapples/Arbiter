"""Page renderers for the reviewer console (lane P5-A)."""

from __future__ import annotations

from typing import Any

import streamlit as st

from ui.client import ArbiterAPIError
from ui.components import (
    AUDIT_CAPTION,
    AUDIT_EVENTS_CAPTION,
    AUDIT_EVENTS_EMPTY,
    CONDITION_OPTIONS,
    CONDITIONS_HELP,
    DRY_RUN_NOTE,
    ELIGIBILITY_DISABLED,
    ELIGIBLE_CAPTION,
    ELIGIBLE_TITLE,
    EMPTY_PRECEDENTS,
    EVAL_CAPTION,
    EVAL_LIVE_CAPTION,
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
    PRECEDENT_HELP,
    REPLAY_MATCH_CAPTION,
    REPLAY_MISMATCH_CAPTION,
    REPLAY_SECTION_CAPTION,
    REVIEW_CAPTION,
    REVIEW_EMPTY,
    humanise_eligibility_reason,
    humanised_bullet,
    ledger_line,
    live_run_summary,
    memory_table_rows,
    precedent_rows,
    replay_check_line,
    review_conditions,
    see_raw,
    split_eval_summary,
    strip_leading_h1,
)
from ui.models import ReviewRequest
from ui.session import get_client

ASSESSMENT_SPINNER = (
    "Running the assessment. Sample mode takes a few seconds; "
    "a live run takes about 2–4 minutes (measured median 142 s)."
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
    body = strip_leading_h1(text)
    # P20: summaries now open with "### Evaluation results"; the page title already says Evaluation.
    if body.startswith("### Evaluation results"):
        body = body.split("\n", 1)[1] if "\n" in body else ""
    head, tail = split_eval_summary(body)
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
    client = get_client()
    latest: dict[str, Any] = {}
    try:
        latest = client.eval_latest()
    except ArbiterAPIError as exc:
        if exc.status_code != 404:
            st.error(exc.message)
    if latest.get("live_markdown"):
        _section("Live evaluation", EVAL_LIVE_CAPTION)
        _render_eval_markdown(str(latest["live_markdown"]))
    _section("Offline benchmark", EVAL_OFFLINE_CAPTION)
    if latest.get("offline_markdown"):
        _render_eval_markdown(str(latest["offline_markdown"]))
    else:
        st.info("Evaluation results are not published yet.")
    _section("Live runs on this instance", LIVE_CAPTION)
    try:
        health = client.health()
        cases = client.list_cases()
    except ArbiterAPIError as exc:
        st.error(exc.message)
        return
    summary = live_run_summary(cases if isinstance(cases, list) else [], health)
    cases_col, data_col, llm_col, recent_col = st.columns(4)
    cases_col.metric("Cases", summary["n"])
    data_col.metric("Data backend", summary["data_backend"])
    llm_col.metric("LLM provider", summary["llm_provider"])
    recent_col.metric("Most recent", summary["latest"])
