"""EvidenceAgent: runs the plan's registry queries, guards vendor text, extracts claims."""

from __future__ import annotations

from app.agents.base import AgentContext, llm_or_fallback
from app.agents.catalogue import DQ_QUERY, QUERY_SYSTEM, QUESTION_KEYS, control_for_key, record_key
from app.agents.llm_schemas import ClaimListOut, ExtractedClaim
from app.data.backend import QueryResult
from app.data.dq import load_dq_rules
from app.errors import BudgetExceeded
from app.extract.deterministic import EXTRACTOR_ID, extract
from app.guard import scout_guard
from app.llm import prompts
from app.schemas.common import Provenance
from app.schemas.evidence import Claim, DQFlag
from app.state import CaseState, PlanStep, Segment

NAME = "EvidenceAgent"
_VALUE_TYPES = {
    "creds.rotation_days": "number (days)",
    "access.review_interval_days": "number (days)",
    "assurance.claimed": "list of 'SOC 2 Type II' / 'ISO 27001'",
    "incidents.vendor_reported_24m": "number (count)",
    "breach.notify_hours_claimed": "number (hours)",
    "residency.regions_claimed": "list of EU / UK / US",
    "transfer.mechanism_claimed": "SCCs | IDTA | NONE",
    "vuln.patch_sla_critical_days": "number (days)",
    "pentest.interval_months": "number (months)",
}


def run_query(
    ctx: AgentContext, state: CaseState, step: PlanStep, *, agent: str = NAME
) -> QueryResult | None:
    """One backend call, one `query_run` trace event (also on failure)."""
    try:
        result = ctx.backend.run(step.query_id, dict(step.params))
    except BudgetExceeded:
        raise
    except Exception as exc:
        ctx.tracer.event(
            agent,
            "query_run",
            input_summary=f"query_id={step.query_id}",
            output_summary=f"{type(exc).__name__}: query failed",
            status="error",
            query_id=step.query_id,
            source_system=QUERY_SYSTEM.get(step.query_id),
        )
        state.limitations.append(
            f"Query {step.query_id} failed ({type(exc).__name__}); its facts stay UNKNOWN."
        )
        return None
    state.executed_queries[step.query_id] = result
    state.query_counts[step.query_id] = state.query_counts.get(step.query_id, 0) + 1
    system = QUERY_SYSTEM.get(step.query_id, "unknown")
    for row in result.rows:
        key = record_key(step.query_id, row)
        if key is not None:
            state.evidence_index[f"E-{system}-{key.split('=', 1)[1]}"] = Provenance(
                kind="public_feed" if system == "cisa_kev" else "system_of_record",
                system=system,
                query_id=step.query_id,
                record_key=key,
                backend=result.backend,
            )
    request = f" zetaris_request_id={result.request_id}" if result.backend == "zetaris" else ""
    fallback = f" fallback_from={result.fallback_from}" if result.fallback_from else ""
    ctx.tracer.event(
        agent,
        "query_run",
        input_summary=f"query_id={step.query_id} params={sorted(step.params)}",
        output_summary=f"rows={len(result.rows)} backend={result.backend}{request}{fallback}",
        status="fallback" if result.fallback_from else "success",
        query_id=step.query_id,
        rows=len(result.rows),
        backend=result.backend,
        source_system=system,
        latency_ms=result.latency_ms,
        iteration=len(state.plans),
    )
    return result


def _guard_rows(ctx: AgentContext, state: CaseState, result: QueryResult) -> list[Segment]:
    seen = {s.segment_id for s in state.segments}
    fresh: list[Segment] = []
    is_answer = result.query_id == "Q_SUBMISSION_ANSWERS"
    for row in result.rows:
        ref = str(row.get("question_id") if is_answer else row.get("doc_id"))
        segment_id = f"{'ans' if is_answer else 'doc'}-{ref}"
        if segment_id in seen:
            continue
        text = str(row.get("answer_text" if is_answer else "text") or "")
        verdict = scout_guard.guard(
            text,
            surface="vendor_answer" if is_answer else "vendor_document",
            capabilities=set(),
            segment_id=segment_id,
            tracer=ctx.tracer,
            use_model=ctx.use_model,
        )
        segment = Segment(
            segment_id=segment_id,
            kind="answer" if is_answer else "document",
            ref=ref,
            query_id=result.query_id,
            record_key=record_key(result.query_id, row) or segment_id,
            text="" if verdict.level == "block" else verdict.redacted_text,
            guard=verdict.model_copy(
                update={"redacted_text": "" if verdict.level == "block" else verdict.redacted_text}
            ),
        )
        state.segments.append(segment)
        state.guard_flags.extend(verdict.flags)
        fresh.append(segment)
    return fresh


def _catalogue(segments: list[Segment]) -> str:
    lines = []
    for segment in segments:
        for key in QUESTION_KEYS.get(segment.ref, ()):
            lines.append(f"{segment.ref}: {key} ({_VALUE_TYPES.get(key, 'true/false')})")
    return "\n".join(lines)


def _valid(claim: ExtractedClaim, refs: set[str]) -> bool:
    return (
        claim.question_id in refs
        and claim.key in QUESTION_KEYS.get(claim.question_id, ())
        and bool(claim.quote.strip())
    )


def extract_claims(
    ctx: AgentContext, state: CaseState, segments: list[Segment], *, force_rules: bool = False
) -> None:
    answers = [s for s in segments if s.kind == "answer" and s.usable and QUESTION_KEYS.get(s.ref)]
    if not answers:
        return
    refs = {s.ref for s in answers}

    def deterministic() -> tuple[list[ExtractedClaim], str]:
        return [c for s in answers for c in extract(s.ref, s.text)], EXTRACTOR_ID

    def from_model() -> tuple[list[ExtractedClaim], str]:
        text = "\n".join(f"{s.ref}: {s.text}" for s in answers)
        result = ctx.generator(
            prompts.render("extract", control_catalogue=_catalogue(answers), vendor_text=text),
            system=prompts.UNTRUSTED_SENTENCE,
            route="fast",
            response="json",
            schema=ClaimListOut,
            purpose="extract",
            tracer=ctx.tracer,
            agent_name=NAME,
        )
        parsed = result.parsed
        assert isinstance(parsed, ClaimListOut)
        return [
            c for c in parsed.claims if _valid(c, refs)
        ], f"llm:{result.provider}:{result.model or result.route}"

    if force_rules or not ctx.use_model:
        (claims, extractor), source = deterministic(), "deterministic"
    else:
        (claims, extractor), source = llm_or_fallback(
            ctx, from_model, deterministic, purpose="extract", agent=NAME
        )
    by_ref = {s.ref: s for s in answers}
    for n, item in enumerate(claims, start=len(state.claims) + 1):
        segment = by_ref[item.question_id]
        state.claims.append(
            Claim(
                claim_id=f"CL-{item.question_id}-{n}",
                control_id=control_for_key(item.key),
                key=item.key,
                asserted_value=item.value,
                state=item.state,
                provenance=Provenance(
                    kind="vendor_answer",
                    system="trust_portal",
                    query_id=segment.query_id,
                    record_key=segment.record_key,
                    quote=item.quote,
                    answer_ref=item.question_id,
                ),
                extractor=extractor,
            )
        )
    if extractor not in state.extractors:
        state.extractors.append(extractor)
    ctx.tracer.event(
        NAME,
        "extract_claims",
        input_summary=f"answers={len(answers)} source={source}",
        output_summary=f"{len(claims)} claims from {len(refs)} answers ({extractor})",
        status="success",
        provider="offline" if source == "deterministic" else None,
        target_agent="EvaluatorAgent",
    )


def _dq_flags(state: CaseState, result: QueryResult) -> None:
    pk = {rule.id: rule.pk for rule in load_dq_rules()}
    known = {(f.rule, f.record_key) for f in state.dq_flags}
    for row in result.rows:
        rule = str(row.get("rule_id"))
        key = f"{pk.get(rule, 'id')}={row.get('record_key')}"
        if (rule, key) not in known:
            state.dq_flags.append(DQFlag(rule=rule, table=str(row.get("table_name")), record_key=key))
            known.add((rule, key))


class EvidenceAgent:
    name = NAME
    role = "Runs registry queries via the data layer, guards vendor text, extracts quoted claims"

    def __call__(self, state: CaseState, ctx: AgentContext) -> CaseState:
        plan = state.plans[-1]
        fresh: list[Segment] = []
        for step in plan.steps:
            ctx.check_budget()
            result = run_query(ctx, state, step)
            if result is None:
                continue
            if result.query_id in {"Q_SUBMISSION_ANSWERS", "Q_SUBMISSION_DOCUMENTS"}:
                fresh += _guard_rows(ctx, state, result)
            if result.query_id == DQ_QUERY:
                _dq_flags(state, result)
        extract_claims(ctx, state, fresh)
        targets = set(plan.extraction_targets)
        if targets:
            stale = {c.provenance.answer_ref for c in state.claims if c.grounded is False}
            redo = [s for s in state.segments if s.kind == "answer" and s.ref in targets & stale]
            state.claims = [c for c in state.claims if c.provenance.answer_ref not in {s.ref for s in redo}]
            extract_claims(ctx, state, redo, force_rules=True)
        return state
