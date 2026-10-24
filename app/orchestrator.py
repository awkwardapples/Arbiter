"""Explicit bounded state machine for one vendor assessment."""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.actions.contracts import issue
from app.actions.executor import execute
from app.agents.base import AgentContext, offline_generate
from app.agents.challenger import ChallengerAgent
from app.agents.evaluator import EvaluatorAgent
from app.agents.evidence import EvidenceAgent, run_query
from app.agents.planner import PlannerAgent
from app.agents.reporter import ReporterAgent, template_report
from app.agents.response import build_output
from app.confidence import compute
from app.config import Settings
from app.data.factory import get_backend
from app.data.registry import load_registry
from app.errors import BudgetExceeded
from app.facts import tier_profile
from app.labels import system_label
from app.llm.generator import generate
from app.memory.keeper import HMemMemory, build_memory
from app.policy.engine import decide, force_escalate
from app.policy.loader import load_default, policy_sha256
from app.policy.tiering import tier as assign_tier
from app.schemas.api import AgentInfo, RunResponse, Workload
from app.schemas.case import CaseInput
from app.schemas.decision import DecisionRecord, PolicyInputs
from app.state import CaseState, PlanStep, new_state
from app.store import CaseBundle, Store
from app.tracing import Tracer

MAX_EVAL_LOOPS = 2
MAX_CHALLENGE_LOOPS = 1
_CAPABILITIES = {
    "APPROVE": ["procurement.approval.record"],
    "APPROVE_WITH_CONDITIONS": ["procurement.approval.record"],
    "REQUEST_INFO": ["outbox.email.draft"],
    "ESCALATE": ["itsm.ticket.create"],
    "DECLINE": ["procurement.decline.record"],
}


class State(StrEnum):
    INTAKE = "INTAKE"
    PLAN = "PLAN"
    GATHER = "GATHER"
    EVALUATE = "EVALUATE"
    DECIDE_1 = "DECIDE_1"
    MEMORY_CHECK = "MEMORY_CHECK"
    DECIDE_2 = "DECIDE_2"
    CHALLENGE = "CHALLENGE"
    REPORT = "REPORT"
    CONTRACT = "CONTRACT"
    EXECUTE = "EXECUTE"
    SAFE_ESCALATE = "SAFE_ESCALATE"
    DONE = "DONE"


class RunOptions(BaseModel):
    sample_mode: bool | None = None
    llm: Literal["auto", "meterless", "nvidia", "offline"] | None = None


class Deps(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    backend_factory: Callable[..., Any] | None = None
    generator: Callable[..., Any] | None = None
    memory: Any = None
    sink: Any = None
    clock: Callable[[], datetime] | None = None
    monotonic: Callable[[], float] | None = None
    tracer_factory: Callable[..., Tracer] | None = None
    var_dir: Path = Path("var")
    agents: dict[str, Any] | None = None


def transition(state: State, st: CaseState) -> State:
    """Pure next-state table. Loop counters are read, not updated."""
    if state is State.INTAKE:
        return State.PLAN
    if state is State.PLAN:
        return State.GATHER
    if state is State.GATHER:
        return State.EVALUATE
    if state is State.EVALUATE:
        evaluation = st.latest_evaluation()
        needs_more = evaluation is not None and not evaluation.sufficient and st.eval_loops < MAX_EVAL_LOOPS
        return State.PLAN if needs_more else State.DECIDE_1
    if state is State.DECIDE_1:
        return State.MEMORY_CHECK
    if state is State.MEMORY_CHECK:
        return State.DECIDE_2
    if state is State.DECIDE_2:
        return State.CHALLENGE
    if state is State.CHALLENGE:
        challenge = st.challenge
        if (
            challenge is not None
            and challenge.action == "re_plan"
            and st.challenge_loops < MAX_CHALLENGE_LOOPS
        ):
            return State.PLAN
        return State.REPORT
    if state is State.SAFE_ESCALATE:
        return State.REPORT
    if state is State.REPORT:
        return State.CONTRACT
    if state is State.CONTRACT:
        return State.EXECUTE
    return State.DONE


def intake(state: CaseState, ctx: AgentContext) -> CaseState:
    """Load the vendor profile (or the inline submission) before any planning."""
    result = run_query(
        ctx,
        state,
        PlanStep(query_id="Q_VENDOR_PROFILE", params={"vendor_id": state.vendor_ref}, reason="profile"),
        agent="Orchestrator",
    )
    row = result.rows[0] if result is not None and result.rows else {}
    state.profile = {key: _plain(value) for key, value in row.items()}
    if "criticality" not in state.profile:
        submission = state.input.submission
        state.profile.setdefault("criticality", submission.criticality if submission else "high")
        state.profile.setdefault("data_categories", "internal")
        state.profile.setdefault("annual_spend_gbp", 0)
        if submission is not None:
            state.profile["legal_name"] = submission.legal_name
    return state


def _plain(value: object) -> object:
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return value.isoformat()  # type: ignore[no-any-return]
    return value


def _settings(options: RunOptions) -> Settings:
    updates: dict[str, Any] = {}
    if options.sample_mode is not None:
        updates["SAMPLE_MODE"] = options.sample_mode
    if options.llm is not None:
        updates["LLM_PROVIDER"] = options.llm
    return Settings().model_copy(update=updates) if updates else Settings()


def _decide(
    state: CaseState,
    ctx: AgentContext,
    *,
    precedents: list[Any] | None = None,
    precedent_alignment: float | None = None,
) -> DecisionRecord:
    profile = tier_profile(state, state.facts)
    case_tier, _score = assign_tier(profile, ctx.policy)
    alignment = 1.0 if precedent_alignment is None else precedent_alignment
    confidence = compute(state, ctx.policy, ctx.calibration, tier=case_tier, precedent_alignment=alignment)
    inputs = PolicyInputs(
        case_id=state.case_id,
        run_id=state.run_id,
        as_of=state.as_of,
        profile=profile,
        facts=list(state.facts),
        contradictions=list(state.contradictions),
        guard_flags=list(state.guard_flags),
        precedents=list(precedents or []),
        confidence=confidence,
    )
    return decide(inputs, ctx.policy, ctx.calibration)


def _trace_decide(ctx: AgentContext, state: CaseState, record: DecisionRecord, *, precedents: int) -> None:
    failing = ",".join(c.control_id for c in record.controls if c.state == "FALSE")
    unknown = ",".join(c.control_id for c in record.controls if c.state == "UNKNOWN")
    ctx.tracer.event(
        "PolicyEngine",
        "decide",
        input_summary=(
            f"facts={len(state.facts)} contradictions={len(state.contradictions)} precedents={precedents}"
        ),
        output_summary=f"outcome={record.outcome} tier={record.tier} failing={failing} unknown={unknown}",
        status="success",
    )


def _safe_record(state: CaseState, ctx: AgentContext, reason: str) -> DecisionRecord:
    try:
        return force_escalate(_decide(state, ctx), reason)
    except Exception:
        return DecisionRecord.safe_escalation(
            case_id=state.case_id,
            run_id=state.run_id,
            as_of=state.as_of,
            reason=reason,
            policy_version=ctx.policy.version,
            policy_sha256=policy_sha256(ctx.policy),
            calibration_version=ctx.calibration.version,
        )


def run(case_input: CaseInput, *, options: RunOptions, deps: Deps | None = None) -> RunResponse:
    deps = deps or Deps()
    settings = _settings(options)
    started = time.perf_counter()
    mono = deps.monotonic or time.monotonic
    deadline = mono() + settings.RUN_BUDGET_SECONDS
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    mode = settings.mode()
    tracer = (
        deps.tracer_factory(run_id, mode)
        if deps.tracer_factory is not None
        else Tracer(run_id, mode=mode, log_dir="logs")
    )
    policy, calibration = load_default()
    submission = case_input.submission
    factory = deps.backend_factory or get_backend
    backend = factory(settings, tracer, submission)
    clock = deps.clock or (lambda: datetime.now(UTC))

    def check_budget() -> None:
        if mono() >= deadline:
            raise BudgetExceeded(f"run budget of {settings.RUN_BUDGET_SECONDS}s exceeded")

    memory = (
        deps.memory
        if deps.memory is not None
        else build_memory(settings, var_dir=deps.var_dir, clock=clock, tracer=tracer)
    )
    ctx = AgentContext(
        tracer=tracer,
        backend=backend,
        generator=deps.generator or (offline_generate if settings.LLM_PROVIDER == "offline" else generate),
        policy=policy,
        calibration=calibration,
        memory=memory,
        settings=settings,
        clock=clock,
        offline=settings.LLM_PROVIDER == "offline",
        check_budget=check_budget,
    )
    agents = deps.agents or {
        "planner": PlannerAgent(),
        "evidence": EvidenceAgent(),
        "evaluator": EvaluatorAgent(),
        "challenger": ChallengerAgent(),
        "reporter": ReporterAgent(),
    }
    state = new_state(
        case_input,
        run_id=run_id,
        as_of=settings.ARBITER_AS_OF,
        mode=mode,
        budget_deadline=deadline,
    )
    if isinstance(memory, HMemMemory):
        memory.set_run_context(run_id=run_id, case_tier="T2", failing=[], vendor_ref=state.vendor_ref)
    tracer.event(
        "Orchestrator",
        "start_run",
        input_summary=f"case_id={state.case_id}",
        output_summary=f"budget={settings.RUN_BUDGET_SECONDS}s data={mode['data']} llm={mode['llm']}",
        status="success",
    )
    phase = State.INTAKE
    run_status = "success"
    safe = False
    for _step in range(40):
        if phase is State.DONE:
            break
        if not safe:
            try:
                check_budget()
                _act(phase, state, ctx, agents)
            except Exception as exc:
                _jump_safe(phase, state, ctx, exc)
                phase = State.SAFE_ESCALATE
                safe = True
                run_status = "escalated"
                continue
        else:
            _act(phase, state, ctx, agents)
        nxt = transition(phase, state)
        run_status = _cross(phase, nxt, state, ctx, run_status)
        _trace_edge(ctx, phase, nxt, state, run_status)
        phase = nxt
    sink = deps.sink or Store(deps.var_dir)
    record = state.decision or _safe_record(state, ctx, "SYSTEM_NoDecision")
    report = state.report or template_report(record, state)
    state.decision = record
    state.report = report
    _finish(state, ctx, sink, tracer, run_status, started)
    log_file = f"logs/trace-{run_id}.jsonl"
    elapsed = max(time.perf_counter() - started, 1e-6)
    output = build_output(state, record, report)
    workload = _workload(state, log_file, elapsed)
    output = output.model_copy(update={"workload": workload})
    if hasattr(sink, "save_workload"):
        sink.save_workload(state.case_id, workload)
    return RunResponse(
        run_id=run_id,
        status=run_status,  # type: ignore[arg-type]
        output=output,
        agents=[AgentInfo(name=agent.name, role=agent.role) for agent in agents.values()],
        trace_id=tracer.trace_id,
        log_file=log_file,
        execution_time_seconds=elapsed,
        mode=mode,
    )


def _act(phase: State, state: CaseState, ctx: AgentContext, agents: dict[str, Any]) -> None:
    if phase is State.INTAKE:
        intake(state, ctx)
    elif phase is State.PLAN:
        agents["planner"](state, ctx)
    elif phase is State.GATHER:
        agents["evidence"](state, ctx)
    elif phase is State.EVALUATE:
        agents["evaluator"](state, ctx)
    elif phase is State.DECIDE_1:
        state.first_decision = _decide(state, ctx)
        state.decision = state.first_decision
        _trace_decide(ctx, state, state.first_decision, precedents=0)
    elif phase is State.MEMORY_CHECK:
        _memory(state, ctx)
    elif phase is State.DECIDE_2:
        alignment = 1.0
        if isinstance(ctx.memory, HMemMemory):
            alignment = ctx.memory.precedent_alignment(state.precedents)
        state.decision = _decide(state, ctx, precedents=state.precedents, precedent_alignment=alignment)
        if isinstance(ctx.memory, HMemMemory):
            ctx.memory.trace_precedent_outcomes(state.decision)
        _trace_decide(ctx, state, state.decision, precedents=len(state.precedents))
        ctx.tracer.event(
            "Orchestrator",
            "redecide",
            input_summary=f"precedents={len(state.precedents)}",
            output_summary=f"outcome={state.decision.outcome}",
            status="success",
            target_agent="ChallengerAgent",
        )
    elif phase is State.CHALLENGE:
        agents["challenger"](state, ctx)
    elif phase is State.REPORT:
        if any(item.startswith("SYSTEM_") for item in state.errors) and state.report is not None:
            return
        agents["reporter"](state, ctx)
    elif phase is State.CONTRACT:
        _contract(state, ctx)
    elif phase is State.EXECUTE:
        _execute(state, ctx)
    elif phase is State.SAFE_ESCALATE:
        return


def _memory(state: CaseState, ctx: AgentContext) -> None:
    record = state.decision
    if record is None:
        return
    eligible = {
        control.id
        for control in ctx.policy.controls
        if control.precedent_exception is not None and control.precedent_exception.allowed
    }
    failing = [
        control.control_id
        for control in record.controls
        if control.control_id in eligible and control.state != "TRUE"
    ]
    if isinstance(ctx.memory, HMemMemory):
        ctx.memory.set_run_context(
            run_id=record.run_id,
            case_tier=record.tier,
            failing=failing,
            vendor_ref=state.vendor_ref,
        )
    state.precedents = list(ctx.memory.find_precedents(record.policy_inputs.profile, failing))
    ctx.tracer.event(
        "Orchestrator",
        "memory_check",
        input_summary=f"failing={','.join(failing) or '-'}",
        output_summary=f"candidates={len(state.precedents)}",
        status="success",
    )


def _contract(state: CaseState, ctx: AgentContext) -> None:
    record = state.decision
    report = state.report or template_report(record)  # type: ignore[arg-type]
    state.report = report
    contract = issue(
        record,  # type: ignore[arg-type]
        report,
        capabilities_map=_CAPABILITIES,
        policy=ctx.policy,
        trace_id=state.run_id,
        registry_version=1,
        now=ctx.clock(),
    )
    state.contracts.append(contract)


def _execute(state: CaseState, ctx: AgentContext) -> None:
    contract = state.contracts[-1]
    report = state.report
    payload: dict[str, Any] = {"summary": report.summary if report else ""}
    if report is not None and report.clarification_email is not None:
        payload["clarification_email"] = report.clarification_email.model_dump()
    result = execute(
        contract,
        now=ctx.clock(),
        policy=ctx.policy,
        outbox_dir=Path("var") / "outbox",
        payload=payload,
        tracer=ctx.tracer,
    )
    state.contracts[-1] = result.contract
    if result.artifact:
        state.artifacts.append(result.artifact)


def _cross(phase: State, nxt: State, state: CaseState, ctx: AgentContext, run_status: str) -> str:
    if phase is State.EVALUATE and nxt is State.PLAN:
        state.eval_loops += 1
    if phase is State.CHALLENGE and nxt is State.PLAN:
        state.challenge_loops += 1
    if (
        phase is State.CHALLENGE
        and nxt is State.REPORT
        and state.challenge is not None
        and state.challenge.action == "re_plan"
        and state.decision is not None
    ):
        state.decision = force_escalate(state.decision, "CHALLENGE_REPLAN_EXHAUSTED")
        ctx.tracer.event(
            "Orchestrator",
            "challenge_capped",
            input_summary="re_plan with no loop left",
            output_summary="CHALLENGE_REPLAN_EXHAUSTED",
            status="escalated",
        )
    evaluation = state.latest_evaluation()
    if (
        phase is State.EVALUATE
        and nxt is State.DECIDE_1
        and evaluation is not None
        and not evaluation.sufficient
        and run_status == "success"
    ):
        return "partial_success"
    return run_status


def _trace_edge(ctx: AgentContext, phase: State, nxt: State, state: CaseState, run_status: str) -> None:
    detail = ""
    status = "success"
    if phase is State.PLAN and state.plans:
        detail = f" ({len(state.plans[-1].steps)} queries)"
    if phase is State.EVALUATE and nxt is State.PLAN:
        evaluation = state.latest_evaluation()
        gaps = [] if evaluation is None else [gap.control_id for gap in evaluation.gaps]
        detail = f" (gaps: {','.join(gaps)})"
        status = "needs_revision"
    if phase is State.EVALUATE and nxt is State.DECIDE_1 and run_status == "partial_success":
        status = "partial_success"
    escalated = (
        phase is State.CHALLENGE
        and nxt is State.REPORT
        and state.challenge is not None
        and state.challenge.action == "escalate"
    )
    if escalated:
        status = "escalated"
    ctx.tracer.event(
        "Orchestrator",
        "transition",
        input_summary=f"from={phase.value}",
        output_summary=f"{phase.value}→{nxt.value}{detail}",
        status=status,
    )


def _jump_safe(phase: State, state: CaseState, ctx: AgentContext, exc: Exception) -> None:
    ctx.tracer.event(
        "Orchestrator",
        "transition",
        input_summary=f"from={phase.value} error={type(exc).__name__}",
        output_summary=f"{phase.value}→SAFE_ESCALATE",
        status="error",
    )
    reason = f"SYSTEM_{type(exc).__name__}"
    state.errors.append(reason)
    state.decision = _safe_record(state, ctx, reason)
    state.first_decision = state.first_decision or state.decision
    state.report = template_report(state.decision)
    ctx.tracer.event(
        "Orchestrator",
        "safe_escalate",
        input_summary=reason,
        output_summary=f"outcome={state.decision.outcome}",
        status="escalated",
    )


def _finish(
    state: CaseState,
    ctx: AgentContext,
    sink: Store,
    tracer: Tracer,
    run_status: str,
    started: float,
) -> None:
    record = state.decision
    report = state.report
    assert record is not None and report is not None
    for contract in state.contracts:
        sink.put_contract(contract)
    try:
        ctx.memory.record_assessment(record)
    except Exception:
        state.limitations.append("memory.record_assessment failed; the decision was still stored")
    legal = str(state.profile.get("legal_name") or state.vendor_ref)
    sink.save(
        CaseBundle(
            case_id=state.case_id,
            run_id=state.run_id,
            created_at=ctx.clock(),
            status=run_status,
            mode=state.mode,
            input=state.input,
            vendor_ref=state.vendor_ref,
            legal_name=legal,
            decision=record,
            first_decision=state.first_decision,
            report=report,
            contract_ids=[c.contract_id for c in state.contracts],
            artifacts=list(state.artifacts),
            log_file=f"logs/trace-{state.run_id}.jsonl",
            limitations=list(report.limitations) + list(state.limitations),
        )
    )
    tracer.event(
        "Orchestrator",
        "complete_run",
        input_summary=f"case_id={state.case_id}",
        output_summary=f"{record.outcome} in {time.perf_counter() - started:.3f}s",
        status=run_status,
    )


def _workload(state: CaseState, log_file: str, elapsed: float) -> Workload:
    """Counts from the trace and the executed case. Nothing here is estimated."""
    events: list[dict[str, Any]] = []
    path = Path(log_file)
    if path.is_file():
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    model_ids = sorted(
        {
            str(event["model"])
            for event in events
            if event.get("action") == "model_call" and event.get("model")
        }
    )
    registry = load_registry()
    labels: list[str] = []
    for query_id in sorted(state.executed_queries):
        spec = registry.get(query_id)
        if spec is None:
            continue
        for system in spec.systems:
            label = system_label(system)
            if label not in labels:
                labels.append(label)
    return Workload(
        systems_queried=labels,
        queries=sum(1 for event in events if event.get("action") == "query_run"),
        rows_read=sum(len(result.rows) for result in state.executed_queries.values()),
        documents_read=sum(1 for segment in state.segments if segment.kind == "document"),
        answers_read=sum(1 for segment in state.segments if segment.kind == "answer"),
        claims_extracted=len(state.claims),
        claims_grounded=sum(1 for claim in state.claims if claim.grounded),
        contradictions=len(state.contradictions),
        dq_flags=len(state.dq_flags),
        guard_blocks=sum(1 for flag in state.guard_flags if flag.level == "block"),
        model_calls=sum(1 for event in events if event.get("action") == "model_call"),
        models=model_ids,
        elapsed_seconds=elapsed,
    )
