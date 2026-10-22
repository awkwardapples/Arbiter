"""Shared helpers for P3 agent tests: a real DuckDB backend, the real policy, injected generators."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from app.agents.base import AgentContext
from app.agents.evaluator import EvaluatorAgent
from app.agents.evidence import EvidenceAgent
from app.agents.memory_port import NullMemory
from app.agents.planner import PlannerAgent
from app.config import Settings
from app.data.factory import get_backend
from app.errors import OfflineProvider
from app.orchestrator import intake
from app.policy.engine import decide
from app.policy.loader import load_default
from app.schemas.case import CaseInput
from app.schemas.common import Provenance
from app.schemas.decision import ConfidenceBreakdown, DecisionRecord, PolicyInputs, TierProfile
from app.schemas.evidence import Fact
from app.state import CaseState, new_state
from app.tracing import Tracer

AS_OF = date(2026, 10, 26)


def offline_generator(*_args: Any, **_kwargs: Any) -> Any:
    raise OfflineProvider("offline in test")


def make_ctx(
    tmp_path: Path,
    *,
    generator: Callable[..., Any] = offline_generator,
    submission: Any = None,
) -> AgentContext:
    settings = Settings(SAMPLE_MODE=True, LLM_PROVIDER="offline", ARBITER_MEMORY="off")
    tracer = Tracer("test-run", mode={"data": "duckdb", "llm": "offline"}, log_dir=str(tmp_path / "logs"))
    policy, calibration = load_default()
    return AgentContext(
        tracer=tracer,
        backend=get_backend(settings, tracer, submission),
        generator=generator,
        policy=policy,
        calibration=calibration,
        memory=NullMemory(),
        settings=settings,
        clock=lambda: datetime(2026, 10, 26, 9, 0, tzinfo=UTC),
    )


def start(ctx: AgentContext, case_input: CaseInput) -> CaseState:
    state = new_state(
        case_input,
        run_id="test-run",
        as_of=AS_OF,
        mode={"data": "duckdb", "llm": "offline"},
        budget_deadline=float("inf"),
    )
    return intake(state, ctx)


def iterate(state: CaseState, ctx: AgentContext) -> CaseState:
    for agent in (PlannerAgent(), EvidenceAgent(), EvaluatorAgent()):
        state = agent(state, ctx)
    return state


def events(ctx: AgentContext) -> list[dict[str, Any]]:
    path = Path(ctx.tracer._path)  # noqa: SLF001
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def fact(fact_id: str, key: str, value: Any, state: str = "TRUE", kind: str = "system_of_record") -> Fact:
    control = fact_id.split("-")[1]
    return Fact(
        fact_id=fact_id,
        control_id=control,
        key=key,
        value=value,
        state=state,  # type: ignore[arg-type]
        provenance=[Provenance(kind=kind)],  # type: ignore[arg-type]
    )


def baseline_facts() -> list[Fact]:
    """A T3 internal-data vendor that meets every required control."""
    return [
        fact("F-TIER-1", "vendor.data_categories", ["internal"]),
        fact("F-C01-1", "mfa.admin_enforced", True, kind="vendor_answer"),
        fact("F-C01-2", "mfa.remote_enforced", True, kind="vendor_answer"),
        fact("F-C04-1", "crypto.at_rest", True, kind="vendor_answer"),
        fact("F-C04-2", "crypto.in_transit_tls12", True, kind="vendor_answer"),
        fact("F-C06-1", "incidents.material_unremediated_24m", 0),
        fact("F-C11-1", "sanctions.watchlist_matches", 0),
        fact("F-C12-1", "vuln.kev_matches", 0),
    ]


def record_for(facts: list[Fact]) -> DecisionRecord:
    policy, calibration = load_default()
    inputs = PolicyInputs(
        case_id="CASE-TEST",
        run_id="test-run",
        as_of=AS_OF,
        profile=TierProfile(
            data_categories=["internal"], criticality="low", annual_spend_gbp=5000, contract_status="signed"
        ),
        facts=facts,
        contradictions=[],
        guard_flags=[],
        confidence=ConfidenceBreakdown(value=1.0, gate=0.0, abstained=False, signals={}),
    )
    return decide(inputs, policy, calibration)
