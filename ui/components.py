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


QUEUE_CAPTION = "Assessed cases. Filter, then open one to see why it was decided."
AUDIT_CAPTION = "Replay a case to confirm the same decision. Verify checks the hash chain for every case."
EVAL_CAPTION = "How these numbers were produced: `docs/EVALUATION.md`."
CAPTION_CONTRADICTIONS = "A vendor claim and the system-of-record value it disagrees with."
CAPTION_COUNTERFACTUALS = "Evidence that would flip a control if it were verified."
CAPTION_PRECEDENTS = "Governed exceptions considered before this decision."
CAPTION_ACTIONS = "Signed contracts for the next step. This page does not run them."
CAPTION_TIMELINE = "What each agent did on this run, in order."
EMPTY_PRECEDENTS = "No precedents were considered for this case."
NO_CONTRADICTIONS = "No contradictions on this case."
NO_CONTRACTS = "No contracts were issued for this case."
ELIGIBILITY_NOTE = "You can still record this review. No precedent will be created."
ELIGIBLE_TITLE = (
    "This case is eligible for a C05 precedent. "
    "The criteria that the policy requires for an exception are met."
)
INELIGIBLE_TITLE = (
    "This case cannot create a precedent. You can still record a review — "
    "the human decision is stored on the case — but no exception will be saved to memory. "
    "The reasons are below."
)
REVIEW_EMPTY = (
    "No cases are currently awaiting review. Cases that reach DECLINE will appear here "
    "as pending approvals — the policy engine gates those actions on a human sign-off."
)
MITIGATION_FACT = "assurance.bridge_letter_current"
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
C05_HEADING = "About C05 (current independent assurance)"
EVAL_OFFLINE_CAPTION = (
    "This is the offline evaluation — the same decision pipeline run without live Nightshift or Zetaris. "
    "The accuracy is measured against the policy engine's expected outcomes on a labelled set. "
    "For the live run, see the demo video or the trace logs."
)
REPLAY_MATCH_CAPTION = (
    "A match means the decision replays identically. The policy hash, the record hash, and every "
    "contract signature all match — nothing has changed since the decision was recorded."
)
REPLAY_MISMATCH_CAPTION = (
    "A mismatch means the decision as stored does not replay identically from its inputs. "
    "This can happen if the policy engine changed after the decision was recorded, or if the record "
    "was edited. Check the per-item lines — a policy_hash mismatch is the most common: it means the "
    "policy file has been updated since this decision. Record_hash and contract_signatures mismatches "
    "are more serious."
)
MEMORY_CASE_CAPTION = (
    "Pick a case. The policy retrieves precedents that could apply to it, and records the result "
    "of applying each one. Empty list means the policy considered no precedent for this case."
)
LEDGER_CAPTION = (
    "Ledger — the audit trail for this precedent. create is when the precedent was stored; "
    "read is when it was retrieved for a case; feedback is when a later case's outcome rated "
    "this precedent helpful or wrong."
)

HOW_TO_USE = (
    "Pick a vendor from the sample set or paste a vendor JSON to start an assessment. "
    "The pipeline runs the five-agent loop and produces a decision record — outcome, controls, "
    "evidence, and a signed next action. From the decision you can:\n"
    "- Open the case to see the full record — the outcome, each control's status and evidence, "
    "the timeline of the agent loop, and the audit chain.\n"
    "- Record a human review if the policy gated the decision, and optionally save an exception "
    "to memory as a precedent.\n"
    "- Replay the decision to prove it reproduces identically from its inputs.\n"
    "- Inspect the trace to see every fact and query behind it.\n\n"
    "Every decision is reproducible, every fact is cited, and every action is a signed contract "
    "in the audit chain."
)
NEW_ASSESSMENT_CAPTION = "Start a new assessment — the full review flow is in How to use this app."

HOW_TO_READ = (
    "The badge is the policy engine's outcome. Each bullet under it is a reason code, "
    "then what that code means. **Why** is the control and the fact behind it. "
    "**Contradictions** compare a vendor claim with a system of record. "
    "**What would change this** is evidence that is still missing. "
    "**Precedents** are exceptions the policy considered. "
    "**Actions** are signed contracts. **Agent timeline** is the trace of this run."
)

REVIEW_INTRO = (
    "Use this page to record a human decision on a case the policy has flagged. Every assessment "
    "reaches a deterministic outcome through the policy engine. Review is where a qualified reviewer "
    "can override that outcome — with a rationale, and optionally an exception saved to memory for "
    "consistency with later cases.\n\n"
    "The human decision is stored and becomes part of the case record. If you tick Create precedent, "
    "the decision is also saved to H-MEM so that a later case with the same mitigations and conditions "
    "can reuse this reasoning rather than re-deciding from scratch. Tick it when you want this specific "
    "exception to be applied consistently to future cases.\n\n"
    "Only certain cases qualify for a precedent. The four requirements are checked when you click "
    "Check eligibility:\n"
    "- The mitigation fact must be TRUE in this case's data.\n"
    "- The failing control must be the one the precedent addresses (C05, current independent assurance).\n"
    "- No other control that cannot be excepted may also be failing.\n"
    "- The reviewer's role must meet the policy's authority requirement (tprm_lead for C05).\n\n"
    "Any case that satisfies the criteria above will be eligible. The Check eligibility button tells "
    "you whether a selected case is."
)

C05_EXPLANATION = (
    "C05 is the control that checks whether the vendor has a current SOC 2 Type II report or "
    "ISO 27001 certificate — an independent auditor's assessment of their security controls. "
    "It is the only control where an exception is defensible, because a vendor that is mid-renewal "
    "can legitimately have a gap covered by a bridge letter. Other controls (encryption, MFA, "
    "residency, known-vulnerabilities) cannot be excepted, because they either hold or they don't.\n\n"
    "An exception (precedent) is only allowed when:\n"
    "- C05 is the specific control that is failing.\n"
    "- The vendor has a bridge letter confirming renewal within a defined window — recorded as "
    "fact assurance.bridge_letter_current = TRUE.\n"
    "- No other non-exception control is failing.\n"
    "- The reviewer has authority to grant the exception.\n"
    "The page pre-fills the mitigation key when these are satisfied."
)

MEMORY_INTRO = (
    "This page shows where Precedents are stored in H-MEM memory, and the trust-ledger lines for "
    "each one. A precedent is a human exception the system has decided to remember. A case is one "
    "assessment of one vendor. The policy is the deterministic rulebook that decides outcomes. "
    "H-MEM is the memory that lets a human reviewer's past decision influence future cases — but "
    "only when the policy's exception criteria are met.\n\n"
    "Each row is one precedent: its id, the confidence the system assigns to it, the control it "
    "addresses (C05), and the ledger of every time it was created, read, or given feedback. "
    "Confidence starts at 0.70, rises with helpful feedback, and drops with wrong feedback "
    "(a wrong determination costs 0.20). Select a case below to see which of those precedents "
    "the policy considered for that case."
)

ELIGIBILITY_HELD: tuple[tuple[str, str], ...] = (
    ("C05", "The only failing required control is C05, which allows a precedent"),
    ("assurance.bridge_letter_current", "That mitigation fact is TRUE"),
    ("APPROVE", "The decision is APPROVE or APPROVE_WITH_CONDITIONS"),
    ("tprm_lead", "The reviewer role is high enough"),
)


def split_eval_summary(text: str, mark: str = "Synthetic data. Small n.") -> tuple[str, str]:
    """Return text through the line containing mark, then the remainder.

    When mark is absent, return the original text and an empty remainder.
    """
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if mark in line:
            return "".join(lines[: index + 1]), "".join(lines[index + 1 :])
    return text, ""


def see_raw(payload: object) -> None:
    with st.expander("See raw", expanded=False):
        st.code(json.dumps(payload, indent=2, sort_keys=True, default=str), language="json")


def eligibility_body(hint: dict[str, Any]) -> str:
    if hint.get("eligible"):
        lines = [f"- {humanised_bullet(code, text)}" for code, text in ELIGIBILITY_HELD]
        return f"{ELIGIBLE_TITLE}\n\n" + "\n".join(lines)
    reasons = [str(code) for code in hint.get("reasons") or []]
    lines = [f"- {humanised_bullet(code, humanise_eligibility_reason(code))}" for code in reasons]
    body = INELIGIBLE_TITLE
    if lines:
        body += "\n\n" + "\n".join(lines)
    return f"{body}\n\n{ELIGIBILITY_NOTE}"


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
