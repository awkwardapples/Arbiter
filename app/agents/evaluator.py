"""EvaluatorAgent: grounds claims, derives facts, and sends the Planner back for system-of-record checks."""

from __future__ import annotations

import json

from app.agents.base import AgentContext, llm_or_fallback
from app.agents.catalogue import DQ_QUERY, VERIFY_QUERIES, VERIFY_QUERIES_INLINE
from app.agents.llm_schemas import CritiqueOut
from app.facts import derive, tier_profile
from app.grounding import is_grounded
from app.llm import prompts
from app.policy.dsl import evaluate
from app.policy.loader import Control
from app.policy.tiering import tier as assign_tier
from app.schemas.evidence import EvaluationReport, Fact, Gap
from app.state import CaseState

NAME = "EvaluatorAgent"
_CONTRACT_CONTROLS = ("C07", "C08", "C09", "C10")
# Claim key (contradiction key, without `_claimed`) → the SoR fact and the verify query.
# Used only when that control does not apply, so derive() can still see a disagreement.
CLAIM_SOR_VERIFY: tuple[dict[str, str], ...] = (
    {
        "claim_key": "residency.regions",
        "verify_query": "Q_VENDOR_CONTRACT",
        "sor_field": "residency.regions_contract",
    },
)
_REASONS = {
    "C05": "assurance documents not yet read",
    "C06": "the vendor's incident answer is unverified; ITSM is the system of record",
    "C07": "breach-notification terms are claim-only; CLM holds the contract",
    "C08": "DPA status is claim-only; CLM holds the contract",
    "C09": "residency and transfer terms are claim-only; CLM holds the contract",
    "C10": "sub-processor disclosure is claim-only; CLM holds the contract",
    "C11": "watchlist screen not yet run",
    "C12": "declared components not yet checked against CISA KEV",
}


def _ground(state: CaseState) -> None:
    texts = {s.ref: s.text for s in state.segments if s.kind == "answer"}
    for claim in state.claims:
        if claim.grounded is None:
            source = texts.get(claim.provenance.answer_ref or "", "")
            claim.grounded = is_grounded(claim.provenance.quote or "", source)


def _critique(state: CaseState, ctx: AgentContext) -> None:
    """Optional LLM critic. It may only downgrade a TRUE claim to UNKNOWN; anything else is discarded."""
    pending = [
        c for c in state.claims if c.grounded and c.state == "TRUE" and c.claim_id not in state.critiqued
    ]
    if not pending or not ctx.use_model:
        return
    state.critiqued += [c.claim_id for c in pending]
    claims = [
        {
            "claim_id": c.claim_id,
            "key": c.key,
            "value": c.asserted_value,
            "state": c.state,
            "quote": c.provenance.quote,
        }
        for c in pending
    ]

    def from_model() -> list[str]:
        result = ctx.generator(
            prompts.render(
                "critique",
                facts=json.dumps([{"key": f.key, "state": f.state} for f in state.facts], sort_keys=True),
                gaps="[]",
                claims=json.dumps(claims, sort_keys=True, default=str),
            ),
            system=prompts.UNTRUSTED_SENTENCE,
            route="fast",
            response="json",
            schema=CritiqueOut,
            purpose="critique",
            tracer=ctx.tracer,
            agent_name=NAME,
        )
        assert isinstance(result.parsed, CritiqueOut)
        return [d.claim_id for d in result.parsed.downgrades]

    ids, source = llm_or_fallback(ctx, from_model, list, purpose="critique", agent=NAME)
    eligible = {c.claim_id: c for c in pending}
    applied = [i for i in dict.fromkeys(ids) if i in eligible]
    for claim_id in applied:
        eligible[claim_id].state = "UNKNOWN"
    if source == "llm":
        ctx.tracer.event(
            NAME,
            "critique",
            input_summary=f"claims={len(pending)}",
            output_summary=f"downgraded={','.join(applied) or '-'} discarded={len(ids) - len(applied)}",
            status="success",
        )


def _claim_verify(claim_key: str) -> dict[str, str] | None:
    for entry in CLAIM_SOR_VERIFY:
        if entry["claim_key"] == claim_key:
            return entry
    return None


def _contradiction_owner(controls: list[Control], claim_key: str, sor_field: str) -> Control | None:
    for control in controls:
        for check in control.contradiction_checks:
            if check.claim.removesuffix("_claimed") == claim_key and check.sor == sor_field:
                return control
    return None


def _missing_sor_gaps(
    state: CaseState,
    ctx: AgentContext,
    tier: str,
    index: dict[str, Fact],
    *,
    verify: dict[str, tuple[str, ...]],
    contract_known_none: bool,
) -> list[Gap]:
    """Verify queries for a grounded claim whose SoR counterpart was never read.

    Fires only when the control that owns the check does not apply. Applicable
    controls already request their verify queries in the coverage loop.
    """
    applicable = {c.id for c in ctx.policy.controls if _applicable(c, tier, index, ctx)}
    gaps: list[Gap] = []
    requested: set[str] = set()
    for fact in index.values():
        if fact.state == "UNKNOWN" or not fact.derived_from_claims:
            continue
        entry = _claim_verify(fact.key.removesuffix("_claimed"))
        if entry is None:
            continue
        sor = index.get(entry["sor_field"])
        if sor is not None and sor.state != "UNKNOWN":
            continue
        query = entry["verify_query"]
        if query in requested or query in state.executed_queries:
            continue
        owner = _contradiction_owner(ctx.policy.controls, entry["claim_key"], entry["sor_field"])
        if owner is None or owner.id in applicable:
            continue
        if query not in verify.get(owner.id, ()):
            continue
        if owner.id in _CONTRACT_CONTROLS and contract_known_none:
            continue
        requested.add(query)
        gaps.append(
            Gap(
                control_id=owner.id,
                reason=f"{entry['claim_key']} claim has no {entry['sor_field']}",
                suggested_query_ids=[query],
            )
        )
    return gaps


def _applicable(control: Control, tier: str, index: dict[str, Fact], ctx: AgentContext) -> bool:
    if tier not in control.required_for:
        return False
    return (
        control.applies_when is None
        or evaluate(ctx.policy.conditions[control.applies_when], index) != "FALSE"
    )


def _gaps(state: CaseState, ctx: AgentContext, tier: str) -> list[Gap]:
    index = {f.key: f for f in state.facts}
    ran = state.executed_queries
    verify = VERIFY_QUERIES_INLINE if state.is_inline else VERIFY_QUERIES
    contract_known_none = (
        "Q_VENDOR_CONTRACT" not in ran and getattr(index.get("contract.status"), "value", None) == "none"
    )
    contract_rows = bool(ran.get("Q_VENDOR_CONTRACT") and ran["Q_VENDOR_CONTRACT"].rows)
    dq_suggested = False
    gaps: list[Gap] = []
    for control in ctx.policy.controls:
        if not _applicable(control, tier, index, ctx):
            continue
        cid = control.id
        suggested: list[str] = []
        if cid in _CONTRACT_CONTROLS and contract_known_none:
            pass
        elif cid == "C12":
            components = index.get("vuln.components_declared")
            if components is not None and components.value and float(components.value) >= 1:
                suggested = [q for q in verify.get(cid, ()) if q not in ran]
        else:
            suggested = [q for q in verify.get(cid, ()) if q not in ran]
        if cid in _CONTRACT_CONTROLS and contract_rows and DQ_QUERY not in ran and not dq_suggested:
            suggested.append(DQ_QUERY)
            dq_suggested = True
        state_now = evaluate(control.rule, index)
        if suggested or state_now != "TRUE":
            reason = _REASONS.get(cid, "verify") if suggested else f"{control.title}: {state_now}"
            if DQ_QUERY in suggested and not [q for q in suggested if q != DQ_QUERY]:
                reason = "contract rows found; check them against the data-quality rules"
            gaps.append(Gap(control_id=cid, reason=reason, suggested_query_ids=suggested))
    for item in state.contradictions:
        query = item.sor_provenance.query_id
        if (
            item.severity == "material"
            and not item.resolved
            and query
            and state.query_counts.get(query, 0) == 1
        ):
            gaps.append(
                Gap(
                    control_id=item.control_id,
                    reason=(
                        f"material contradiction on {item.key}: confirm the system-of-record row is current"
                    ),
                    suggested_query_ids=[query],
                )
            )
    gaps.extend(
        _missing_sor_gaps(state, ctx, tier, index, verify=verify, contract_known_none=contract_known_none)
    )
    retargeted = {q for plan in state.plans for q in plan.extraction_targets}
    required = {c.id for c in ctx.policy.controls if _applicable(c, tier, index, ctx)}
    for claim in state.claims:
        ref = claim.provenance.answer_ref or ""
        if claim.grounded is False and claim.control_id in required and ref not in retargeted:
            gaps.append(
                Gap(
                    control_id=claim.control_id,
                    reason=f"quote for {claim.key} not found in {ref}; re-extract",
                    suggested_answer_ids=[ref],
                )
            )
    return gaps


class EvaluatorAgent:
    name = NAME
    role = "Grounds claims, derives facts, critiques coverage and requests verification"

    def __call__(self, state: CaseState, ctx: AgentContext) -> CaseState:
        _ground(state)
        _critique(state, ctx)
        state.facts, state.contradictions = derive(state, ctx.policy)
        case_tier, _ = assign_tier(tier_profile(state, state.facts), ctx.policy)
        state.tier_hint = case_tier
        gaps = _gaps(state, ctx, case_tier)
        sufficient = not any(g.suggested_query_ids or g.suggested_answer_ids for g in gaps)
        asks = [g for g in gaps if g.suggested_query_ids or g.suggested_answer_ids]
        report = EvaluationReport(
            sufficient=sufficient,
            gaps=gaps,
            contradictions=list(state.contradictions),
            ungrounded_claim_ids=[c.claim_id for c in state.claims if c.grounded is False],
            dq_flags=list(state.dq_flags),
            injection_flags=[f for f in state.guard_flags if f.level == "block"],
            revision_request=None
            if sufficient
            else "; ".join(
                f"{g.control_id}→{','.join(g.suggested_query_ids + g.suggested_answer_ids)}" for g in asks
            ),
        )
        state.evaluations.append(report)
        if sufficient:
            ctx.tracer.event(
                NAME,
                "evaluate",
                input_summary=f"claims={len(state.claims)} queries={len(state.executed_queries)}",
                output_summary=(
                    f"sufficient: {len(state.facts)} facts, "
                    f"{len(state.contradictions)} contradictions, tier {case_tier}"
                ),
                status="success",
                target_agent="PolicyEngine",
                iteration=len(state.evaluations),
            )
        else:
            ctx.tracer.event(
                NAME,
                "evaluate",
                input_summary=f"claims={len(state.claims)} queries={len(state.executed_queries)}",
                output_summary=f"gaps: {report.revision_request}",
                status="needs_revision",
                target_agent="PlannerAgent",
                iteration=len(state.evaluations),
            )
        return state
