"""Map a finished case into the public RunResponse output."""

from __future__ import annotations

from app.schemas.api import (
    RunOutput,
    RunOutputAction,
    RunOutputContradiction,
    RunOutputCounterfactual,
    RunOutputFinding,
    RunOutputVendor,
)
from app.schemas.decision import DecisionRecord
from app.schemas.report import Report
from app.state import CaseState


def _text(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return "" if value is None else str(value)


def build_output(state: CaseState, record: DecisionRecord, report: Report) -> RunOutput:
    submission = state.input.submission
    legal = state.profile.get("legal_name") or (submission.legal_name if submission else state.vendor_ref)
    limitations = list(report.limitations)
    if state.mode.get("llm") == "offline":
        limitations.append("LLM offline: deterministic extraction and reporting used.")
    limitations.extend(state.limitations)
    summary = report.brief.headline if report.brief is not None else report.summary
    return RunOutput(
        case_id=state.case_id,
        vendor=RunOutputVendor(vendor_id=state.input.vendor_id, legal_name=str(legal)),
        decision=record.outcome,
        risk_tier=record.tier,
        residual_risk=record.residual_risk,
        confidence=record.confidence.model_dump(mode="json"),
        summary=summary,
        brief=report.brief,
        drafts=list(report.drafts),
        findings=[RunOutputFinding(text=s.text, citations=list(s.citations)) for s in report.rationale],
        contradictions=[
            RunOutputContradiction(
                key=item.key,
                claim=_text(item.claim_value),
                system_of_record=_text(item.sor_value),
            )
            for item in record.contradictions
        ],
        counterfactuals=[
            RunOutputCounterfactual(
                control_id=item.control_id,
                evidence_required=list(item.evidence_required),
                question_ids=list(item.question_ids),
            )
            for item in record.counterfactuals
        ],
        precedents=[item.model_dump(mode="json") for item in record.precedents_considered],
        recommendations=list(report.recommended_actions),
        actions=[
            RunOutputAction(
                contract_id=contract.contract_id,
                intent=contract.intent,
                state=contract.state,
                capability=contract.tool_plan[0].capability if contract.tool_plan else None,
            )
            for contract in state.contracts
        ],
        artifacts=list(state.artifacts),
        limitations=limitations,
    )
