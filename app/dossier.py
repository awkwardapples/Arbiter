"""Export a stored case as a Markdown or self-contained HTML decision dossier."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Literal

from app.actions.contracts import verify
from app.labels import control_title, outcome_label, outcome_meaning, question_text, state_word, system_label
from app.policy.engine import required_approvals
from app.policy.loader import load_default
from app.store import CaseBundle, Store

_SECTIONS = (
    "Analyst brief",
    "Evidence",
    "Controls",
    "What would change this decision",
    "Drafts",
    "Approvals",
    "Precedents",
    "Integrity",
)
_CRITERIA = {
    "exception_not_allowed": "the policy does not allow a precedent on this control",
    "mitigation_fact": "the required mitigation was not verified",
    "reviewer_authority": "the reviewer did not have authority",
    "precedent_age": "the precedent is too old",
    "retrieval_quality": "the precedent was not a strong enough match",
    "tier_risk": "this case is riskier than the precedent",
    "superseded": "another precedent was applied instead",
    "control_already_satisfied": "the control already passed",
    "control_not_applicable": "the control does not apply",
}


def render(bundle: CaseBundle, fmt: Literal["md", "html"] = "md") -> str:
    """Render one case. HTML has no external assets."""
    sections = _sections(bundle)
    if fmt == "html":
        return _html(bundle, sections)
    lines = [f"# Decision dossier: {bundle.legal_name}", ""]
    for title, body in sections:
        lines.append(f"## {title}")
        lines.append("")
        lines.append(body)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _sections(bundle: CaseBundle) -> list[tuple[str, str]]:
    record = bundle.decision
    report = bundle.report
    policy, _calibration = load_default()
    unknown = record.confidence.unknown_controls
    if unknown:
        named = ", ".join(f"{control_id} {control_title(control_id)}" for control_id in unknown)
        confidence = f"Confidence {record.confidence.value:.0%}. Unverified controls: {named}."
    else:
        confidence = f"Confidence {record.confidence.value:.0%}."
    header = "\n".join(
        [
            f"Vendor: {bundle.legal_name}",
            f"Decision: {outcome_label(record.outcome)}. {outcome_meaning(record.outcome)}",
            f"Tier: {record.tier}",
            f"Residual risk: {record.residual_risk}",
            confidence,
        ]
    )
    brief = _brief(report)
    evidence = _evidence(record)
    controls = _controls(record)
    changes = _counterfactuals(record)
    drafts = _drafts(report)
    approvals = _approvals(bundle, required_approvals(record, policy))
    precedents = _precedents(record)
    integrity = _integrity(bundle)
    bodies = [header, brief, evidence, controls, changes, drafts, approvals, precedents, integrity]
    return [("Header", bodies[0]), *zip(_SECTIONS, bodies[1:], strict=True)]


def _brief(report: object) -> str:
    brief = getattr(report, "brief", None)
    if brief is None:
        return "No analyst brief was stored with this case."
    lines = [brief.headline, ""]
    for point in brief.why:
        lines.append(f"- {point.text}")
    if brief.next_steps:
        lines.append("")
        lines.append("Next steps:")
        for step in brief.next_steps:
            due = f" (due {step.due})" if step.due else ""
            lines.append(f"- {step.action} Owner: {step.owner_role}{due}.")
    return "\n".join(lines)


def _evidence(record: object) -> str:
    lines = ["| Source | Record | Field | Value | Quote | Request |", "| --- | --- | --- | --- | --- | --- |"]
    for item in record.contradictions:  # type: ignore[attr-defined]
        prov = item.sor_provenance
        lines.append(
            "| "
            + " | ".join(
                [
                    system_label(prov.system or ""),
                    _cell(_record_id(prov.record_key)),
                    _cell(prov.field or item.key),
                    _cell(_show(item.sor_value)),
                    _cell(prov.quote or ""),
                    _cell(prov.zetaris_request_id or ""),
                ]
            )
            + " |"
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    system_label("trust_portal"),
                    "vendor claim",
                    _cell(item.key),
                    _cell(_show(item.claim_value)),
                    "",
                    "",
                ]
            )
            + " |"
        )
    if len(lines) == 2:
        return "No claim disagreed with a system of record."
    return "\n".join(lines)


def _controls(record: object) -> str:
    lines = []
    for control in record.controls:  # type: ignore[attr-defined]
        title = control_title(control.control_id)
        why = _why(record, control.control_id, control.state)
        lines.append(f"- {title}: {state_word(control.state)}. {why}")
    return "\n".join(lines) or "No controls were evaluated."


def _counterfactuals(record: object) -> str:
    rows = record.counterfactuals  # type: ignore[attr-defined]
    if not rows:
        return "Nothing further would change this decision on the current evidence."
    lines = []
    for item in rows:
        title = control_title(item.control_id)
        questions = []
        for question_id in item.question_ids:
            try:
                questions.append(question_text(question_id))
            except KeyError:
                continue
        asked = " ".join(questions)
        evidence = "; ".join(item.evidence_required)
        lines.append(f"- {title} ({state_word(item.from_state)} to met). {evidence} {asked}".rstrip())
    return "\n".join(lines)


def _drafts(report: object) -> str:
    drafts = getattr(report, "drafts", None) or []
    if not drafts:
        return "No action was drafted."
    blocks = []
    for draft in drafts:
        blocks.append(f"To: {draft.to_role}\nSubject: {draft.subject}\n\n{draft.body}")
    return "\n\n".join(blocks)


def _approvals(bundle: CaseBundle, roles: list[str]) -> str:
    lines = [f"Approvals required: {', '.join(roles) if roles else 'none'}."]
    try:
        contracts = Store().contracts_for(bundle.case_id)
    except Exception:
        contracts = []
    if not contracts:
        lines.append("No execution contract has been issued.")
        return "\n".join(lines)
    for contract in contracts:
        ok, reason = verify(contract, now=contract.issued_at)
        check = "signature valid" if ok else f"signature invalid ({reason})"
        lines.append(f"- {contract.contract_id}: state {contract.state}, intent {contract.intent}, {check}.")
    return "\n".join(lines)


def _precedents(record: object) -> str:
    considered = record.precedents_considered  # type: ignore[attr-defined]
    if not considered:
        return "No precedents were considered."
    lines = []
    for item in considered:
        status = "applied" if item.applied else "not applied"
        failed = ", ".join(_CRITERIA.get(code, code.replace("_", " ")) for code in item.failed_criteria)
        extra = f" Reason: {failed}." if failed else ""
        title = control_title(item.control_id)
        lines.append(f"- {item.precedent_id} on {title}: {status}.{extra}")
    return "\n".join(lines)


def _integrity(bundle: CaseBundle) -> str:
    record = bundle.decision
    models = _models(bundle.log_file)
    served = ", ".join(models) if models else "none (deterministic brief)"
    return "\n".join(
        [
            f"Policy version: {record.policy_version}",
            f"Policy hash: {record.policy_sha256}",
            f"Calibration version: {record.calibration_version}",
            f"Record hash: {record.record_sha256}",
            f"Replay command: python run.py replay {bundle.case_id}",
            f"Trace id: {bundle.run_id}",
            f"Models served: {served}",
        ]
    )


def _html(bundle: CaseBundle, sections: list[tuple[str, str]]) -> str:
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        f"<title>Decision dossier: {html.escape(bundle.legal_name)}</title>",
        "<style>",
        "body { font-family: Georgia, serif; margin: 2rem; color: #222; }",
        "h1, h2 { font-family: sans-serif; }",
        "table { border-collapse: collapse; width: 100%; }",
        "td, th { border: 1px solid #ccc; padding: 0.4rem; vertical-align: top; }",
        "pre { white-space: pre-wrap; font-family: Georgia, serif; }",
        "</style>",
        "</head>",
        "<body>",
        f"<h1>Decision dossier: {html.escape(bundle.legal_name)}</h1>",
    ]
    for title, body in sections:
        parts.append(f"<h2>{html.escape(title)}</h2>")
        parts.append(f"<pre>{html.escape(body)}</pre>")
    parts.append("</body></html>")
    return "\n".join(parts) + "\n"


def _why(record: object, control_id: str, state: str) -> str:
    if state == "TRUE":
        return "The cited evidence meets the control."
    for item in record.counterfactuals:  # type: ignore[attr-defined]
        if item.control_id == control_id and item.evidence_required:
            return "Would need " + "; ".join(item.evidence_required) + "."
    return "The cited evidence does not meet the control."


def _models(log_file: str) -> list[str]:
    path = Path(log_file)
    if not path.is_file():
        return []
    found: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        model = event.get("model")
        if model and model not in found:
            found.append(str(model))
    return found


def _record_id(record_key: str | None) -> str:
    if not record_key:
        return ""
    if "=" in record_key:
        return record_key.split("=", 1)[1]
    return record_key


def _show(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


def _cell(value: str) -> str:
    return value.replace("|", "/")
