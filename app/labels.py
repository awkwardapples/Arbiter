"""Plain-English labels, the deterministic analyst brief, and action drafts."""

from __future__ import annotations

import json
import re
from functools import lru_cache

from app.agents.catalogue import QUESTION_TEXTS
from app.policy.loader import Policy, load_default
from app.schemas.decision import ControlResult, DecisionRecord
from app.schemas.evidence import Contradiction, Fact
from app.schemas.report import AnalystBrief, BriefPoint, BriefWording, Draft, EvidenceRef, NextStep
from app.state import CaseState

_OUTCOMES: dict[str, tuple[str, str]] = {
    "APPROVE": ("Approve", "Every required control passed, so the vendor can be onboarded."),
    "APPROVE_WITH_CONDITIONS": (
        "Approve with conditions",
        "Approval stands only if the stated conditions are met.",
    ),
    "REQUEST_INFO": (
        "Request information",
        "Required evidence is missing, so the vendor must reply before a decision.",
    ),
    "ESCALATE": ("Escalate", "A person must decide; the policy will not approve this case as it stands."),
    "DECLINE": ("Decline", "A hard gate failed. Do not onboard this vendor."),
}
_REASONS: dict[str, str] = {
    "HARD_GATE_DECLINE": "A control that requires a decline has failed.",
    "UNTRUSTED_CONTENT_TAMPERING": "The vendor submission tried to change the assessment instructions.",
    "CONTRADICTION": "The vendor's claim conflicts with a system of record.",
    "HARD_GATE_ESCALATE": "A control that requires escalation has failed.",
    "CONTROL_FAILED": "A required control failed.",
    "EVIDENCE_MISSING": "A required control could not be verified.",
    "LOW_CONFIDENCE_ABSTAIN": "The evidence is too thin to approve.",
    "CONDITIONS": "Approval depends on a condition or a precedent exception.",
    "ALL_REQUIRED_CONTROLS_MET": "Every required control passed.",
}
_SYSTEMS: dict[str, str] = {
    "procurement": "Procurement (ERP)",
    "clm": "Contract system (CLM)",
    "itsm": "Service desk (ITSM)",
    "grc_watchlist": "Sanctions watchlist (GRC)",
    "trust_portal": "Vendor trust portal",
    "cisa_kev": "CISA Known Exploited Vulnerabilities",
}
_STATE_WORDS = {"TRUE": "met", "FALSE": "not met", "UNKNOWN": "unverified"}
_HEADLINE_LEAD = {
    "ESCALATE": "Escalate to the TPRM lead",
    "REQUEST_INFO": "Ask the vendor for more information",
    "DECLINE": "Decline, and tell the business owner",
    "APPROVE_WITH_CONDITIONS": "Approve with conditions",
    "APPROVE": "Approve",
}
_NAME = re.compile(r"\b[A-Z][a-zA-Z]{2,}\b")
_NUMBER = re.compile(r"\d+")


def outcome_label(outcome: str) -> str:
    return _OUTCOMES[outcome][0]


def outcome_meaning(outcome: str) -> str:
    return _OUTCOMES[outcome][1]


def reason_text(code: str) -> str:
    return _REASONS[code]


def system_label(system: str) -> str:
    return _SYSTEMS.get(system, system.replace("_", " "))


def question_text(question_id: str) -> str:
    return QUESTION_TEXTS[question_id]


def state_word(state: str) -> str:
    return _STATE_WORDS.get(state, "unverified")


@lru_cache(maxsize=1)
def _policy() -> Policy:
    policy, _calibration = load_default()
    return policy


def control_title(control_id: str, policy: Policy | None = None) -> str:
    source = policy or _policy()
    for control in source.controls:
        if control.id == control_id:
            return control.title
    raise KeyError(control_id)


def build_brief(record: DecisionRecord, state: CaseState | None = None) -> AnalystBrief:
    """Deterministic analyst brief. Prose uses labels, not reason codes or query ids."""
    vendor = _vendor(record, state)
    points = _why_points(record, state, vendor)[:4]
    if points:
        detail = points[0].text.rstrip(".")
        headline = f"{_HEADLINE_LEAD[record.outcome]}: {detail}."
    else:
        headline = f"{outcome_label(record.outcome)}: {vendor} meets the checks this assessment could verify."
    return AnalystBrief(
        headline=headline,
        why=points,
        next_steps=[_next_step(record.outcome)],
        generator="template:v2",
    )


def build_drafts(record: DecisionRecord, state: CaseState | None = None) -> list[Draft]:
    """Full action text for the outcome: email, ticket, or memo."""
    vendor = _vendor(record, state)
    owner = _owner(state)
    if record.outcome == "REQUEST_INFO":
        return [_email(record, vendor)]
    if record.outcome == "ESCALATE":
        return [_ticket(record, vendor)]
    if record.outcome == "DECLINE":
        return [_memo_decline(record, vendor, owner)]
    return [_memo_approve(record, vendor)]


def accept_brief_wording(
    brief: AnalystBrief,
    candidate: BriefWording,
    record: DecisionRecord,
    state: CaseState | None,
) -> bool:
    """Reject a rewrite that adds a number or a name the case does not contain."""
    if len(candidate.why) != len(brief.why):
        return False
    corpus = _corpus(brief, record, state)
    text = candidate.headline + "\n" + "\n".join(candidate.why)
    if any(number not in corpus for number in _NUMBER.findall(text)):
        return False
    return all(name in corpus for name in _NAME.findall(text))


def _why_points(record: DecisionRecord, state: CaseState | None, vendor: str) -> list[BriefPoint]:
    points: list[BriefPoint] = []
    seen: set[str] = set()
    for item in sorted(record.contradictions, key=lambda row: (row.severity != "material", row.key)):
        if item.resolved:
            continue
        points.append(_contradiction_point(item, record, vendor))
        seen.add(item.control_id)
    failing = [control for control in record.controls if control.required and control.state != "TRUE"]
    failing.sort(key=lambda control: (control.state != "FALSE", control.control_id))
    for control in failing:
        if control.control_id in seen:
            continue
        points.append(_control_point(control, record, state, vendor))
        seen.add(control.control_id)
    if state is not None:
        for flag in state.dq_flags:
            points.append(
                BriefPoint(
                    text=f"Data quality flagged a {flag.table} record ({_record_id(flag.record_key)}).",
                    citations=[],
                )
            )
        if any(flag.level == "block" for flag in state.guard_flags):
            points.append(
                BriefPoint(
                    text="The vendor submission was blocked before it could be used as evidence.",
                    citations=[],
                )
            )
    return points


def _contradiction_point(item: Contradiction, record: DecisionRecord, vendor: str) -> BriefPoint:
    system = system_label(item.sor_provenance.system or "clm")
    record_id = _record_id(item.sor_provenance.record_key)
    claim = _show(item.claim_value)
    sor = _show(item.sor_value)
    if record_id.startswith("CTR-"):
        where = f"its contract ({record_id})"
    elif record_id:
        where = f"{system} record {record_id}"
    else:
        where = system
    text = f"{vendor} says {claim}, but {where} shows {sor}."
    claim_fact = _fact_by_key(record, item.key)
    return BriefPoint(
        text=text,
        claim=EvidenceRef(
            source_label=system_label("trust_portal"),
            record_label=vendor,
            field_label=_field_label(None, item.key),
            value=claim,
            quote=None if claim_fact is None else _quote(claim_fact),
            provenance_id="" if claim_fact is None else claim_fact.fact_id,
        ),
        record=EvidenceRef(
            source_label=system,
            record_label=record_id or system,
            field_label=_field_label(item.sor_provenance.field, item.key),
            value=sor,
            quote=item.sor_provenance.quote,
            provenance_id=item.sor_provenance.record_key or item.key,
        ),
        citations=[] if claim_fact is None else [claim_fact.fact_id],
    )


def _control_point(
    control: ControlResult, record: DecisionRecord, state: CaseState | None, vendor: str
) -> BriefPoint:
    title = control_title(control.control_id)
    facts = _control_facts(record, control)
    kev = next((fact for fact in facts if fact.key == "vuln.kev_matches"), None)
    if kev is None:
        kev = _fact_by_key(record, "vuln.kev_matches") if control.control_id == "C12" else None
    if kev is not None and _positive(kev.value):
        products = _products(state)
        product = ", ".join(products) if products else "a declared component"
        sla = _fact_by_key(record, "vuln.patch_sla_critical_days")
        text = f"{vendor} runs {product}, which has {_num(kev.value)} known-exploited vulnerabilities"
        if sla is not None and sla.value is not None:
            text += f" against a {_num(sla.value)}-day critical-patch SLA (policy limit 14 days)"
        text += "."
        return BriefPoint(text=text, citations=[fact.fact_id for fact in facts[:2]])
    evidence = _evidence_for(record, control.control_id)
    extra = f" What would satisfy it: {evidence}." if evidence else ""
    text = f"{title} is {state_word(control.state)}.{extra}"
    return BriefPoint(text=text, citations=[fact.fact_id for fact in facts[:1]])


def _email(record: DecisionRecord, vendor: str) -> Draft:
    lines = [f"Please send the following so we can finish the assessment of {vendor}.", ""]
    seen: set[str] = set()
    for item in record.counterfactuals:
        evidence = "; ".join(item.evidence_required)
        for question_id in item.question_ids:
            if question_id in seen or question_id not in QUESTION_TEXTS:
                continue
            seen.add(question_id)
            lines.append(question_text(question_id))
            if evidence:
                lines.append(f"Evidence that would satisfy this: {evidence}")
            lines.append("")
    if len(lines) == 2:
        lines.append("Please reply with the missing evidence described in the assessment.")
    return Draft(
        to_role="vendor",
        subject=f"Information requested for {vendor} ({record.case_id})",
        body="\n".join(lines).strip(),
    )


def _ticket(record: DecisionRecord, vendor: str) -> Draft:
    lines = [
        f"- {control_title(control.control_id)} is {state_word(control.state)}"
        for control in record.controls
        if control.state != "TRUE"
    ]
    for item in record.contradictions:
        if not item.resolved:
            claim = _show(item.claim_value)
            record_value = _show(item.sor_value)
            lines.append(f"- Claim {claim} does not match the record {record_value}")
    evidence = "\n".join(lines) or "- No single control failed; the case still needs a person."
    body = "\n".join(
        [
            f"Summary: {vendor} needs a decision from the TPRM lead.",
            "",
            "Evidence:",
            evidence,
            "",
            f"Risk: residual risk {record.residual_risk} out of 100, tier {record.tier}.",
            "",
            f"Requested decision: continue, ask {vendor} for evidence, or decline.",
        ]
    )
    return Draft(to_role="tprm_lead", subject=f"Escalation ticket: {vendor}", body=body)


def _memo_decline(record: DecisionRecord, vendor: str, owner: str) -> Draft:
    failed = [
        control_title(control.control_id)
        for control in record.controls
        if control.state == "FALSE" and control.hard_gate == "decline"
    ]
    because = ", ".join(failed) if failed else "a hard gate in the onboarding policy"
    body = "\n".join(
        [
            f"Dear {owner},",
            "",
            f"This memo is for the business owner of {vendor}.",
            f"Do not onboard {vendor}. The assessment declined the vendor because {because} is not met.",
            "No approval contract should be signed.",
        ]
    )
    return Draft(to_role="business_owner", subject=f"Decline memo: {vendor}", body=body)


def _memo_approve(record: DecisionRecord, vendor: str) -> Draft:
    conditions = record.conditions or ["None."]
    listed = "\n".join(f"- {item}" for item in conditions)
    kind = "conditional approval" if record.outcome == "APPROVE_WITH_CONDITIONS" else "approval"
    body = "\n".join(
        [
            f"This memo records {kind} for {vendor}.",
            f"Tier {record.tier}. Residual risk {record.residual_risk} out of 100.",
            "",
            "Conditions:",
            listed,
        ]
    )
    return Draft(to_role="tprm_analyst", subject=f"Approval memo: {vendor}", body=body)


def _next_step(outcome: str) -> NextStep:
    steps = {
        "REQUEST_INFO": ("Send the clarification email and wait for the vendor's reply.", "tprm_analyst"),
        "ESCALATE": ("Open the service-desk ticket for the TPRM lead.", "tprm_lead"),
        "DECLINE": ("Tell the business owner the vendor is declined.", "business_owner"),
        "APPROVE": ("Record the approval once the required approvers sign.", "tprm_analyst"),
        "APPROVE_WITH_CONDITIONS": (
            "Record the conditional approval and track each condition.",
            "tprm_analyst",
        ),
    }
    action, role = steps[outcome]
    return NextStep(action=action, owner_role=role)


def _vendor(record: DecisionRecord, state: CaseState | None) -> str:
    if state is not None:
        name = state.profile.get("legal_name")
        if name:
            return str(name)
        submission = state.input.submission
        if submission is not None:
            return submission.legal_name
    return record.case_id


def _owner(state: CaseState | None) -> str:
    if state is not None and state.profile.get("business_owner"):
        return str(state.profile["business_owner"])
    return "business owner"


def _products(state: CaseState | None) -> list[str]:
    if state is None:
        return []
    result = state.executed_queries.get("Q_VENDOR_COMPONENTS")
    if result is None:
        return []
    names: list[str] = []
    for row in result.rows:
        product = row.get("product")
        if product and str(product) not in names:
            names.append(str(product))
    return names


def _num(value: object) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _control_facts(record: DecisionRecord, control: ControlResult) -> list[Fact]:
    by_id = {fact.fact_id: fact for fact in record.facts}
    return [by_id[fact_id] for fact_id in control.fact_ids if fact_id in by_id]


def _fact_by_key(record: DecisionRecord, key: str) -> Fact | None:
    for fact in record.facts:
        if fact.key == key:
            return fact
    return None


def _evidence_for(record: DecisionRecord, control_id: str) -> str:
    for item in record.counterfactuals:
        if item.control_id == control_id and item.evidence_required:
            return "; ".join(item.evidence_required)
    return ""


def _quote(fact: Fact) -> str | None:
    for item in fact.provenance:
        if item.quote:
            return item.quote
    return None


def _record_id(record_key: str | None) -> str:
    if not record_key:
        return ""
    if "=" in record_key:
        return record_key.split("=", 1)[1]
    return record_key


def _field_label(field: str | None, fact_key: str | None) -> str:
    raw = field or fact_key or "value"
    return raw.replace("_", " ").replace(".", " ")


def _show(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if value is None:
        return "unknown"
    return str(value)


def _positive(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _corpus(brief: AnalystBrief, record: DecisionRecord, state: CaseState | None) -> str:
    parts = [brief.headline, *(point.text for point in brief.why), record.model_dump_json()]
    parts.extend(outcome_label(code) for code in _OUTCOMES)
    parts.extend(outcome_meaning(code) for code in _OUTCOMES)
    if state is not None:
        parts.append(json.dumps(state.profile, default=str))
        for result in state.executed_queries.values():
            parts.append(json.dumps(result.rows, default=str))
    return "\n".join(parts)
