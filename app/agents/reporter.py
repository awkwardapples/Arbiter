"""ReporterAgent: a cited explanation of the decision, or the deterministic template."""

from __future__ import annotations

import json

from app.agents.base import AgentContext, llm_or_fallback
from app.agents.catalogue import QUESTION_TEXTS
from app.agents.llm_schemas import ReportOut
from app.errors import ParseFailure
from app.llm import prompts
from app.schemas.decision import DecisionRecord
from app.schemas.report import CitedSentence, Draft, Report
from app.state import CaseState

NAME = "ReporterAgent"
_OUTCOMES = ("APPROVE_WITH_CONDITIONS", "REQUEST_INFO", "ESCALATE", "DECLINE", "APPROVE")

__all__ = ["QUESTION_TEXTS", "template_report", "validate_report", "ReporterAgent"]


def _stated_outcome(summary: str) -> str | None:
    upper = summary.upper()
    for outcome in _OUTCOMES:
        if outcome in upper:
            return outcome
    return None


def validate_report(
    out: ReportOut, record: DecisionRecord, *, known_ids: set[str], generator: str
) -> Report | None:
    """Keep cited sentences. A summary that names a different outcome is rejected."""
    stated = _stated_outcome(out.summary)
    if stated is not None and stated != record.outcome:
        return None
    rationale = [
        sentence
        for sentence in out.rationale
        if sentence.citations and all(cite in known_ids for cite in sentence.citations)
    ]
    email = out.clarification_email if record.outcome == "REQUEST_INFO" else None
    return Report(
        summary=out.summary,
        rationale=rationale,
        recommended_actions=list(out.recommended_actions),
        clarification_email=email,
        limitations=list(out.limitations),
        generator=generator,
    )


def template_report(record: DecisionRecord) -> Report:
    """Deterministic report labelled template:v1, built only from the decision record."""
    failing = [control for control in record.controls if control.state != "TRUE"]
    rationale: list[CitedSentence] = []
    for control in failing:
        cites = [f"R-{control.control_id}", *control.fact_ids[:1]]
        rationale.append(
            CitedSentence(
                text=f"{control.control_id} ({control.title}) is {control.state}.",
                citations=cites,
            )
        )
    for item in record.counterfactuals:
        questions = ", ".join(item.question_ids) or "further evidence"
        rationale.append(
            CitedSentence(
                text=f"{item.control_id} would reach TRUE with {questions}.",
                citations=[f"R-{item.control_id}"],
            )
        )
    if not rationale:
        cite = record.facts[0].fact_id if record.facts else "R-POLICY"
        rationale.append(
            CitedSentence(
                text=f"No required control failed for outcome {record.outcome}.",
                citations=[cite],
            )
        )
    reasons = ", ".join(record.outcome_reasons) or "policy"
    controls = ", ".join(control.control_id for control in failing)
    summary = f"Outcome {record.outcome}: {reasons}."
    if controls:
        summary = f"{summary} Failing controls: {controls}."
    email = None
    if record.outcome == "REQUEST_INFO":
        lines = []
        seen: set[str] = set()
        for item in record.counterfactuals:
            for question_id in item.question_ids:
                if question_id in seen or question_id not in QUESTION_TEXTS:
                    continue
                seen.add(question_id)
                lines.append(f"{question_id}: {QUESTION_TEXTS[question_id]}")
        email = Draft(
            to_role="vendor",
            subject=f"Information requested ({record.case_id})",
            body="Please reply to the following:\n" + "\n".join(lines),
        )
    action = {
        "APPROVE": "Record the approval once required approvers sign the contract.",
        "APPROVE_WITH_CONDITIONS": "Record the conditional approval and track the conditions.",
        "REQUEST_INFO": "Send the clarification email and wait for the vendor's reply.",
        "ESCALATE": "Open a ticket for the TPRM lead.",
        "DECLINE": "Record the decline and notify the business owner.",
    }[record.outcome]
    return Report(
        summary=summary,
        rationale=rationale,
        recommended_actions=[action],
        clarification_email=email,
        limitations=["template:v1 deterministic report from the decision record."],
        generator="template:v1",
    )


def _known_ids(state: CaseState, record: DecisionRecord) -> set[str]:
    ids = {fact.fact_id for fact in record.facts}
    ids |= {f"R-{control.control_id}" for control in record.controls}
    ids |= {ref.precedent_id for ref in record.precedents_considered}
    ids |= set(state.evidence_index)
    return ids


def _prompt(record: DecisionRecord, known: set[str]) -> str:
    decision = {
        "outcome": record.outcome,
        "reasons": record.outcome_reasons,
        "tier": record.tier,
        "controls": [{"id": c.control_id, "state": c.state, "title": c.title} for c in record.controls],
        "counterfactuals": [c.model_dump() for c in record.counterfactuals],
        "questions": {
            qid: QUESTION_TEXTS[qid]
            for item in record.counterfactuals
            for qid in item.question_ids
            if qid in QUESTION_TEXTS
        },
    }
    facts = [
        {
            "fact_id": f.fact_id,
            "key": f.key,
            "state": f.state,
            "kinds": sorted({p.kind for p in f.provenance}),
        }
        for f in record.facts
    ]
    return prompts.render(
        "report",
        decision=json.dumps(decision, sort_keys=True, default=str),
        facts=json.dumps(facts, sort_keys=True, default=str),
        citations=json.dumps(sorted(known)),
    )


class ReporterAgent:
    name = NAME
    role = "Writes a cited report of the policy decision, or the deterministic template"

    def __call__(self, state: CaseState, ctx: AgentContext) -> CaseState:
        record = state.decision
        if record is None:
            raise RuntimeError("reporter ran before a decision existed")
        if any(item.startswith("SYSTEM_") for item in state.errors) and state.report is not None:
            return state
        known = _known_ids(state, record)

        def deterministic() -> Report:
            return template_report(record)

        def from_model() -> Report:
            result = ctx.generator(
                _prompt(record, known),
                system=prompts.UNTRUSTED_SENTENCE,
                route="deep",
                response="json",
                schema=ReportOut,
                purpose="report",
                tracer=ctx.tracer,
                agent_name=NAME,
            )
            parsed = result.parsed
            assert isinstance(parsed, ReportOut)
            label = f"{result.provider}/{result.route}:{result.model or result.route}"
            report = validate_report(parsed, record, known_ids=known, generator=label)
            if report is None:
                raise ParseFailure("report summary names a different outcome")
            return report

        if ctx.use_model:
            report, source = llm_or_fallback(ctx, from_model, deterministic, purpose="report", agent=NAME)
        else:
            report, source = deterministic(), "deterministic"
        state.report = report
        ctx.tracer.event(
            NAME,
            "report",
            input_summary=f"outcome={record.outcome}",
            output_summary=f"generator={report.generator} sentences={len(report.rationale)}",
            status="fallback" if source == "deterministic" and ctx.use_model else "success",
            provider="offline" if report.generator == "template:v1" else None,
            target_agent="ActionExecutor",
        )
        return state
