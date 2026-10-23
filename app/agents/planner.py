"""PlannerAgent: chooses registry queries. Model output may pick ids; params are always built in code."""

from __future__ import annotations

import json
import re
from datetime import timedelta
from typing import Any

from app.agents.base import AgentContext, llm_or_fallback
from app.agents.catalogue import INCIDENT_WINDOW_DAYS, SCREEN_QUERIES, SCREEN_QUERIES_INLINE
from app.agents.llm_schemas import PlanOut
from app.data.inline import DELEGATED, INLINE_QUERIES
from app.data.registry import QueryDef, load_registry
from app.errors import ConfigError
from app.llm import prompts
from app.memory.assessments import plan_queries_from_priors
from app.state import CaseState, Plan, PlanStep

NAME = "PlannerAgent"
_NOT_PLANNABLE = frozenset({"Q_VENDOR_LIST", "Q_VENDOR_PROFILE"})


def allowed_queries(state: CaseState) -> list[str]:
    ids = sorted(load_registry())
    if state.is_inline:
        return [q for q in ids if (q in INLINE_QUERIES or q in DELEGATED) and q not in _NOT_PLANNABLE]
    return [
        q for q in ids if q not in _NOT_PLANNABLE and q not in {"Q_KEV_BY_PRODUCTS", "Q_INCIDENTS_BY_NAME"}
    ]


def _names(state: CaseState) -> list[str]:
    names = [state.profile.get("legal_name"), state.profile.get("trading_name")]
    aliases = state.executed_queries.get("Q_VENDOR_ALIASES")
    found = [str(n) for n in names if n] + ([str(r["alias_lower"]) for r in aliases.rows] if aliases else [])
    return sorted({re.sub(r"\s+", " ", n.strip().lower()) for n in found})


def build_params(query_id: str, qdef: QueryDef, state: CaseState) -> dict[str, Any]:
    """Every parameter comes from the case itself, never from model output."""
    params: dict[str, Any] = {}
    for spec in qdef.params:
        name = spec.name
        if name == "vendor_id":
            params[name] = state.vendor_ref
        elif name == "since":
            params[name] = (state.as_of - timedelta(days=INCIDENT_WINDOW_DAYS)).isoformat()
        elif name == "names":
            params[name] = _names(state)
        elif name == "products":
            components = state.executed_queries.get("Q_VENDOR_COMPONENTS")
            params[name] = sorted({str(r["product"]).lower() for r in components.rows}) if components else []
    return params


def required_queries(state: CaseState, memory: object | None = None) -> list[tuple[str, str]]:
    """(query id, reason) the plan must contain: screen set, Evaluator and Challenger requests."""
    if not state.plans:
        screen = SCREEN_QUERIES_INLINE if state.is_inline else SCREEN_QUERIES
        out = [(q, "screen: read what the vendor claims and run the C11 watchlist screen") for q in screen]
        if memory is not None:
            out.extend(plan_queries_from_priors(state.vendor_ref, memory))
        return out
    out: list[tuple[str, str]] = []
    evaluation = state.latest_evaluation()
    if evaluation is not None and not evaluation.sufficient:
        for gap in evaluation.gaps:
            out += [(q, f"verify {gap.control_id}: {gap.reason}") for q in gap.suggested_query_ids]
    if state.challenge is not None and state.challenge.action == "re_plan":
        out += [
            (q, f"challenger: {state.challenge.reason_code}") for q in state.challenge.suggested_query_ids
        ]
    seen: set[str] = set()
    return [(q, r) for q, r in out if not (q in seen or seen.add(q))]  # type: ignore[func-returns-value]


def _targets(state: CaseState) -> list[str]:
    evaluation = state.latest_evaluation()
    if evaluation is None:
        return []
    return sorted({a for gap in evaluation.gaps for a in gap.suggested_answer_ids})


def _query_tables(allowed: list[str], registry: dict[str, QueryDef]) -> str:
    lines: list[str] = []
    for query_id in allowed:
        qdef = registry[query_id]
        found: list[str] = []
        for name in re.findall(r"\{T\.([a-z0-9_]+)\}", qdef.sql or ""):
            if name not in found:
                found.append(name)
        if found:
            lines.append(f"{query_id}: {', '.join(found)}")
        else:
            lines.append(f"{query_id}: {', '.join(qdef.systems) or 'handler'}")
    return "\n".join(lines)


def _catalogue_text() -> tuple[str, str, int] | None:
    """Compact catalogue, sha256, and token estimate. None when the model file is not exported yet."""
    from app.data.usl_model import catalogue_tokens, compact_catalogue, load_model, model_sha256

    try:
        model = load_model()
    except ConfigError:
        return None
    text = compact_catalogue(model)
    return text, model_sha256(model), catalogue_tokens(text)


def _prompt(state: CaseState, allowed: list[str], registry: dict[str, QueryDef], usl_text: str) -> str:
    evaluation = state.latest_evaluation()
    gaps = [] if evaluation is None else [g.model_dump() for g in evaluation.gaps]
    summary = {
        "case_id": state.case_id,
        "kind": "inline submission" if state.is_inline else "registered vendor",
        "category": state.profile.get("category"),
        "criticality": state.profile.get("criticality"),
        "data_categories": state.profile.get("data_categories"),
        "tier_hint": state.tier_hint,
        "iteration": len(state.plans) + 1,
        "already_run": sorted(state.executed_queries),
        "challenge_request": None if state.challenge is None else state.challenge.model_dump(),
    }
    catalogue = [
        {"query_id": q, "description": registry[q].description, "control_ids": registry[q].control_ids}
        for q in allowed
    ]
    return prompts.render(
        "plan",
        case_summary=json.dumps(summary, sort_keys=True, default=str),
        registry=json.dumps(catalogue, sort_keys=True),
        gaps=json.dumps(gaps, sort_keys=True),
        usl_catalogue=usl_text,
        query_tables=_query_tables(allowed, registry),
    )


class PlannerAgent:
    name = NAME
    role = "Chooses registry queries and extraction targets; revises the plan from feedback"

    def __call__(self, state: CaseState, ctx: AgentContext) -> CaseState:
        registry = load_registry()
        allowed = allowed_queries(state)
        required = [(q, r) for q, r in required_queries(state, ctx.memory) if q in allowed]

        def deterministic() -> tuple[list[tuple[str, str]], str]:
            return list(required), ""

        def from_model() -> tuple[list[tuple[str, str]], str]:
            loaded = _catalogue_text()
            usl_text = "" if loaded is None else loaded[0]
            if loaded is not None:
                ctx.tracer.event(
                    NAME,
                    "usl_catalogue",
                    input_summary=f"usl_model_sha256={loaded[1]}",
                    output_summary=f"tokens={loaded[2]}",
                    status="success",
                    purpose="plan",
                )
            result = ctx.generator(
                _prompt(state, allowed, registry, usl_text),
                system=prompts.UNTRUSTED_SENTENCE,
                route="deep",
                response="json",
                schema=PlanOut,
                purpose="plan",
                tracer=ctx.tracer,
                agent_name=NAME,
            )
            plan = result.parsed
            assert isinstance(plan, PlanOut)
            return [(p.query_id, p.reason) for p in plan.queries], plan.rationale

        (proposed, rationale), source = (
            llm_or_fallback(ctx, from_model, deterministic, purpose="plan", agent=NAME)
            if ctx.use_model
            else (deterministic(), "deterministic")
        )
        steps, dropped, added = self._validate(proposed, required, allowed, state)
        if source == "llm" and (dropped or added):
            ctx.tracer.event(
                NAME,
                "plan_corrected",
                input_summary=f"model proposed {len(proposed)} queries",
                output_summary=f"dropped={','.join(dropped) or '-'} re-added={','.join(added) or '-'}",
                status="success",
                iteration=len(state.plans) + 1,
            )
        plan = Plan(
            iteration=len(state.plans) + 1,
            steps=[
                PlanStep(query_id=q, params=build_params(q, registry[q], state), reason=r) for q, r in steps
            ],
            source=source,
            rationale=rationale or "screen, then verify the claims a system of record can check",
            extraction_targets=_targets(state),
        )
        state.plans.append(plan)
        ctx.tracer.event(
            NAME,
            "plan",
            input_summary=f"iteration={plan.iteration} required={len(required)}",
            output_summary=f"{len(plan.steps)} queries: {','.join(s.query_id for s in plan.steps) or '-'}",
            status="success",
            target_agent="EvidenceAgent",
            iteration=plan.iteration,
            provider=None if source == "llm" else "offline",
        )
        return state

    @staticmethod
    def _validate(
        proposed: list[tuple[str, str]],
        required: list[tuple[str, str]],
        allowed: list[str],
        state: CaseState,
    ) -> tuple[list[tuple[str, str]], list[str], list[str]]:
        rerun_ok = {q for q, _ in required}
        steps: list[tuple[str, str]] = []
        dropped: list[str] = []
        for query_id, reason in proposed:
            known = query_id in allowed
            fresh = query_id not in state.executed_queries or query_id in rerun_ok
            if not known or not fresh or any(query_id == s for s, _ in steps):
                dropped.append(query_id)
                continue
            steps.append((query_id, reason))
        added = [q for q, _ in required if all(q != s for s, _ in steps)]
        steps += [(q, r) for q, r in required if q in added]
        return steps, dropped, added
