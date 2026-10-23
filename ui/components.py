"""Shared Streamlit renderers (lane P5-A)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
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


def humanised_bullet(code: str, sentence: str) -> str:
    return f"**{code}** — {sentence}"


QUEUE_CAPTION = "All cases sorted by residual risk. Click a row to open its decision record."
AUDIT_CAPTION = "Append-only hash chain of every case, decision, contract, and action."
EVAL_CAPTION = (
    "Two views: the offline benchmark measures the decision pipeline on a fixed labelled set. "
    "The live section shows this instance's activity."
)
CAPTION_CONTROLS = "Required controls and the facts behind them."
CAPTION_CONTRADICTIONS = "A vendor claim and the system-of-record value it disagrees with."
CAPTION_COUNTERFACTUALS = "Evidence that would flip a control if it were verified."
CAPTION_PRECEDENTS = "Governed exceptions considered before this decision."
CAPTION_ACTIONS = "Signed contracts for the next step."
CAPTION_TIMELINE = "Agents on this run, in order."
CAPTION_TRACE = "Stored record, report, and trace."
EMPTY_PRECEDENTS = "No precedents were considered for this case."
NO_CONTRADICTIONS = "No contradictions on this case."
NO_CONTRACTS = "No contracts were issued for this case."
CASE_EMPTY = "Select a case from Cases, or run an assessment."
MEMORY_EMPTY = "No precedents stored."
ELIGIBLE_TITLE = "Eligible for C05 precedent."
ELIGIBLE_CAPTION = "Criteria met: bridge letter TRUE, C05 only failing control, reviewer role ≥ tprm_lead."
INELIGIBLE_TITLE = "Not eligible for precedent."
INELIGIBLE_CAPTION = "A review can still be recorded — no precedent will be created."
ELIGIBILITY_DISABLED = "Available when the case is eligible."
REVIEW_CAPTION = (
    "Record a reviewer decision on a pending case. An exception can be saved as a precedent "
    "so it applies consistently to later cases."
)
REVIEW_EMPTY = "No cases awaiting review."
MITIGATION_FACT = "assurance.bridge_letter_current"
MITIGATION_OPTIONS: tuple[str, ...] = (MITIGATION_FACT,)
CONDITION_OPTIONS: tuple[str, ...] = (
    "SOC 2 Type II report within 60 days",
    "ISO 27001 certificate within 90 days",
)
MITIGATION_HELP = (
    "The fact that the policy checks when applying the precedent. Pre-filled when the case is eligible."
)
CONDITIONS_HELP = (
    "Freeform notes for future reviewers — the renewal deadline, the specific report, "
    "any commitments the vendor has made. Not evaluated by the policy."
)
PRECEDENT_HELP = (
    "Save this exception to H-MEM. A later case with the same mitigation and conditions "
    "can reuse this decision."
)
EVAL_OFFLINE_CAPTION = "Fixed labelled set, no live services. Method: docs/EVALUATION.md."
LIVE_CAPTION = "Cases, backend, and provider on this API."
REPLAY_MATCH_CAPTION = "The decision reproduces identically from its inputs."
REPLAY_MISMATCH_CAPTION = (
    "The decision does not reproduce. Policy hash mismatch = policy file changed after the decision. "
    "Record hash or signature mismatch = the record differs from what was stored."
)
REPLAY_SECTION_CAPTION = "Reproduce the stored decision from its inputs."
MEMORY_CAPTION = (
    "Human exceptions saved to H-MEM. Each row shows a precedent, the control it addresses, and its ledger."
)
MEMORY_CASE_HEADING = "Precedents considered on a case"
MEMORY_CASE_CAPTION = "Select a case to see which precedents the policy retrieved for it."
LEDGER_CAPTION = "create, read, and feedback on this precedent."
NEW_ASSESSMENT_CAPTION = (
    "Start an assessment on a vendor. The pipeline runs the agent loop and produces a decision record."
)
RESULT_CAPTION = "Decision record from this run."
DRY_RUN_NOTE = "Dry-run only. Nothing was recorded."
AUDIT_EVENTS_CAPTION = "Latest rows on the hash chain."
AUDIT_EVENTS_EMPTY = "No audit events yet."


def strip_leading_h1(text: str) -> str:
    """Drop a leading run of lines that start with '# '. Leave later headings."""
    lines = text.splitlines(keepends=True)
    index = 0
    while index < len(lines) and lines[index].startswith("# "):
        index += 1
    return "".join(lines[index:])


def split_eval_summary(text: str, mark: str = "Synthetic data. Small n.") -> tuple[str, str]:
    """Return text through the line containing mark, then the remainder.

    When mark is absent, return the original text and an empty remainder.
    """
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if mark in line:
            return "".join(lines[: index + 1]), "".join(lines[index + 1 :])
    return text, ""


def review_conditions(selected: list[str], other: str) -> list[str]:
    """Selected options, then a non-blank other condition. Blanks dropped. No duplicates."""
    chosen: list[str] = []
    for item in [*selected, other.strip()]:
        text = item.strip()
        if text and text not in chosen:
            chosen.append(text)
    return chosen


def _first_text(*values: object) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
    return "unknown"


def live_run_summary(cases: list[dict[str, Any]], health: dict[str, Any]) -> dict[str, str]:
    """Keys n, latest, data_backend, llm_provider.

    latest is the max created stamp, or "—" when there are no cases.
    data_backend is health.mode.data, else health.data.backend, else "unknown".
    llm_provider is provider.provider_resolved, else provider.provider, else mode.llm.
    """
    stamps = [str(item.get("created")) for item in cases if item.get("created")]
    mode = health.get("mode") if isinstance(health.get("mode"), dict) else {}
    provider = health.get("provider") if isinstance(health.get("provider"), dict) else {}
    data_block = health.get("data") if isinstance(health.get("data"), dict) else {}
    return {
        "n": str(len(cases)),
        "latest": max(stamps) if stamps else "—",
        "data_backend": _first_text(mode.get("data"), data_block.get("backend")),
        "llm_provider": _first_text(
            provider.get("provider_resolved"),
            provider.get("provider"),
            mode.get("llm"),
        ),
    }


def see_raw(payload: object) -> None:
    with st.expander("See raw", expanded=False):
        st.code(json.dumps(payload, indent=2, sort_keys=True, default=str), language="json")


def _display_value(value: Any) -> str:
    if value is None:
        return "null"
    return str(value)


def _missing(value: object) -> str:
    if value is None or isinstance(value, (dict, list)):
        return "—"
    return str(value)


def contradiction_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    table: list[dict[str, str]] = []
    for row in rows:
        key = str(row.get("key") or "")
        claim = _display_value(row.get("claim_value"))
        table.append(
            {
                "Claim": f"{key}: {claim}" if key else claim,
                "System of record": _display_value(row.get("sor_value")),
            }
        )
    return table


def counterfactual_line(item: dict[str, Any]) -> str:
    evidence = [str(part) for part in item.get("evidence_required") or []]
    shown = "; ".join(evidence) if evidence else "—"
    questions = [str(qid) for qid in item.get("question_ids") or []]
    qids = ", ".join(questions) if questions else "none"
    return f"**{item.get('control_id') or ''}** — {shown}. Questions: {qids}"


def _age_days(as_of: str, created: object) -> str:
    if not as_of or created in (None, ""):
        return "—"
    try:
        end = date.fromisoformat(str(as_of)[:10])
        start = date.fromisoformat(str(created)[:10])
    except ValueError:
        return "—"
    return f"{(end - start).days} days"


def precedent_rows(
    considered: list[dict[str, Any]],
    *,
    candidates: list[dict[str, Any]],
    as_of: str,
) -> list[dict[str, str]]:
    by_id = {str(item.get("precedent_id")): item for item in candidates if isinstance(item, dict)}
    rows: list[dict[str, str]] = []
    for ref in considered:
        if not isinstance(ref, dict):
            continue
        pid = str(ref.get("precedent_id") or "")
        conf = ref.get("hmem_confidence")
        if isinstance(conf, bool) or not isinstance(conf, (int, float)):
            confidence = "—"
        else:
            confidence = f"{float(conf):.2f}"
        created = (by_id.get(pid) or {}).get("created_as_of")
        rows.append(
            {
                "precedent_id": pid,
                "confidence": confidence,
                "age": _age_days(as_of, created),
                "applied": "true" if ref.get("applied") is True else "false",
            }
        )
    return rows


def signature_short(signature: str) -> str:
    if len(signature) <= 16:
        return signature
    return f"{signature[:8]}…{signature[-4:]}"


def tool_plan_lines(steps: object) -> list[str]:
    if not isinstance(steps, list):
        return []
    lines: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        capability = str(step.get("capability") or "")
        args = step.get("args") if isinstance(step.get("args"), dict) else {}
        parts = [
            f"{key}={_display_value(args[key])}"
            for key in sorted(args)
            if args[key] is None or isinstance(args[key], (str, int, float, bool))
        ]
        lines.append(f"{capability} ({', '.join(parts)})" if parts else capability)
    return lines


def contract_card(contract: dict[str, Any]) -> dict[str, str]:
    params = contract.get("parameters") if isinstance(contract.get("parameters"), dict) else {}
    signed_by = str(contract.get("signed_by") or "")
    signature = signature_short(str(contract.get("signature") or ""))
    plan = tool_plan_lines(contract.get("tool_plan") or [])
    return {
        "Contract id": str(contract.get("contract_id") or ""),
        "Intent": str(contract.get("intent") or ""),
        "Outcome": _display_value(params.get("outcome")) if "outcome" in params else "—",
        "State": str(contract.get("state") or ""),
        "Signature": f"{signature} · {signed_by}" if signed_by else signature,
        "Tool plan": "; ".join(plan) if plan else "—",
    }


def ledger_line(entry: dict[str, Any]) -> str:
    action = str(entry.get("action") or "unknown")
    actor = str(entry.get("actor") or "unknown")
    memory_id = str(entry.get("memory_id") or "—")
    stamp = entry.get("timestamp")
    if isinstance(stamp, bool) or not isinstance(stamp, (int, float)):
        when = "—"
    else:
        when = datetime.fromtimestamp(float(stamp) / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    return f"{action} · {actor} · {memory_id} · {when}"


def memory_table_rows(precedents: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in precedents:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "precedent_id": _missing(item.get("precedent_id")),
                "hmem_id": _missing(item.get("hmem_id")),
                "confidence": _missing(item.get("confidence")),
                "control_id": _missing(item.get("control_id")),
            }
        )
    return rows


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
    st.graphviz_chart(build_timeline_dot(filtered))
    table = timeline_rows(filtered)
    for row in table:
        row["status"] = status_label(str(row.get("status", "")))
        if row.get("provider") == "meterless" or row.get("backend") == "zetaris":
            row["agent"] = f"{row.get('agent')} (sponsor)"
    st.dataframe(table, use_container_width=True, hide_index=True)
