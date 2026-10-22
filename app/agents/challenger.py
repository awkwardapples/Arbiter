"""ChallengerAgent: may accept, ask for one more evidence pass, or escalate. Never upgrades."""

from __future__ import annotations

import json

from app.agents.base import AgentContext, llm_or_fallback
from app.agents.llm_schemas import ChallengeOut
from app.agents.planner import allowed_queries
from app.llm import prompts
from app.policy.engine import force_escalate
from app.schemas.decision import DecisionRecord
from app.state import CaseState, ChallengeResult

NAME = "ChallengerAgent"
_FAVOURABLE = frozenset({"APPROVE", "APPROVE_WITH_CONDITIONS"})


def validate_challenge(
    out: ChallengeOut,
    candidate: DecisionRecord,
    *,
    known_fact_ids: set[str],
    allowed_query_ids: set[str],
    loops_left: int,
) -> ChallengeResult:
    """Drop a challenge that cites unknown facts, misuses `other`, or cannot re-plan."""
    del candidate
    rejected: list[str] = []
    if any(fact_id not in known_fact_ids for fact_id in out.cited_fact_ids):
        rejected.append("unknown_fact_id")
    if out.category == "other" and out.action != "accept":
        rejected.append("other_must_accept")
    queries: list[str] = []
    for query_id in out.suggested_query_ids:
        if query_id in allowed_query_ids and query_id not in queries:
            queries.append(query_id)
    action = out.action
    if action == "re_plan" and (loops_left < 1 or not queries):
        rejected.append("replan_unavailable")
    if rejected:
        action = "accept"
    reason = f"CHALLENGE_{out.category.upper()}" if action != "accept" else None
    return ChallengeResult(
        action=action,
        reason_code=reason,
        suggested_query_ids=queries if action == "re_plan" else [],
        source="llm",
        rejected=rejected,
        cited_fact_ids=list(out.cited_fact_ids),
        rationale=out.rationale,
    )


def apply_challenge(candidate: DecisionRecord, result: ChallengeResult) -> DecisionRecord:
    """Escalation goes through the policy engine. Accept and re-plan leave the record unchanged."""
    if result.action != "escalate":
        return candidate
    return force_escalate(candidate, result.reason_code or "CHALLENGE_ESCALATE")


def _fact(record: DecisionRecord, key: str) -> object:
    found = next((item for item in record.facts if item.key == key), None)
    return None if found is None else found.value


def _c01_answer_only(record: DecisionRecord) -> bool:
    if record.tier != "T1":
        return False
    control = next((c for c in record.controls if c.control_id == "C01" and c.state == "TRUE"), None)
    if control is None:
        return False
    facts = [f for f in record.facts if f.fact_id in control.fact_ids] or [
        f for f in record.facts if f.key.startswith("mfa.")
    ]
    kinds = {prov.kind for fact in facts for prov in fact.provenance}
    return bool(kinds) and kinds <= {"vendor_answer"}


def _deterministic(record: DecisionRecord, *, loops_left: int) -> ChallengeResult | None:
    if any("wrong" in ref.failed_criteria for ref in record.precedents_considered if ref.applied):
        return ChallengeResult(
            action="escalate", reason_code="CHALLENGE_PRECEDENT_DISPUTED", source="deterministic"
        )
    near = _fact(record, "sanctions.near_matches")
    if record.tier == "T1" and isinstance(near, (int, float)) and near >= 1:
        return ChallengeResult(action="escalate", reason_code="CHALLENGE_NEAR_MATCH", source="deterministic")
    if _c01_answer_only(record):
        if loops_left >= 1:
            return ChallengeResult(
                action="re_plan",
                reason_code="CHALLENGE_T1_UNCORROBORATED",
                suggested_query_ids=["Q_SUBMISSION_DOCUMENTS"],
                source="deterministic",
            )
        return ChallengeResult(
            action="escalate", reason_code="CHALLENGE_T1_UNCORROBORATED", source="deterministic"
        )
    return None


def _prompt(state: CaseState, record: DecisionRecord, allowed: list[str]) -> str:
    summary = {
        "outcome": record.outcome,
        "tier": record.tier,
        "confidence": record.confidence.value,
        "controls": [{"id": c.control_id, "state": c.state} for c in record.controls],
        "allowed_query_ids": allowed,
        "loops_left": 1 - state.challenge_loops,
    }
    facts = [
        {
            "fact_id": f.fact_id,
            "key": f.key,
            "state": f.state,
            "value": f.value,
            "kinds": sorted({p.kind for p in f.provenance}),
        }
        for f in record.facts
    ]
    claims = [
        {"claim_id": c.claim_id, "key": c.key, "quote": c.provenance.quote}
        for c in state.claims
        if c.provenance.quote
    ]
    return prompts.render(
        "challenge",
        decision_summary=json.dumps(summary, sort_keys=True, default=str),
        facts=json.dumps(facts, sort_keys=True, default=str),
        claims=json.dumps(claims, sort_keys=True, default=str),
    )


class ChallengerAgent:
    name = NAME
    role = "Stress-tests a favourable decision; can only accept, re-plan or escalate"

    def __call__(self, state: CaseState, ctx: AgentContext) -> CaseState:
        record = state.decision
        if record is None:
            raise RuntimeError("challenger ran before a decision existed")
        loops_left = 1 - state.challenge_loops
        allowed = allowed_queries(state)
        known = {fact.fact_id for fact in record.facts}
        trigger = _deterministic(record, loops_left=loops_left)

        def deterministic() -> ChallengeResult:
            if trigger is not None:
                return trigger
            return ChallengeResult(
                action="accept", source="deterministic", rationale="no deterministic trigger"
            )

        def from_model() -> ChallengeResult:
            result = ctx.generator(
                _prompt(state, record, allowed),
                system=prompts.UNTRUSTED_SENTENCE,
                route="deep",
                response="json",
                schema=ChallengeOut,
                purpose="challenge",
                tracer=ctx.tracer,
                agent_name=NAME,
            )
            parsed = result.parsed
            assert isinstance(parsed, ChallengeOut)
            return validate_challenge(
                parsed,
                record,
                known_fact_ids=known,
                allowed_query_ids=set(allowed),
                loops_left=loops_left,
            )

        if trigger is not None or record.outcome not in _FAVOURABLE or not ctx.use_model:
            result = deterministic()
        else:
            result, _source = llm_or_fallback(ctx, from_model, deterministic, purpose="challenge", agent=NAME)
        if result.action == "escalate":
            state.decision = apply_challenge(record, result)
        state.challenge = result
        if result.action == "re_plan":
            action, status = "request_replan", "success"
        elif result.action == "escalate":
            action, status = "challenge", "escalated"
        else:
            action, status = "challenge", "success"
        ctx.tracer.event(
            NAME,
            action,
            input_summary=f"outcome={record.outcome} loops_left={loops_left}",
            output_summary=f"{result.action} {result.reason_code or 'accepted'} source={result.source}",
            status=status,
            target_agent="PlannerAgent" if result.action == "re_plan" else "ReporterAgent",
        )
        return state
