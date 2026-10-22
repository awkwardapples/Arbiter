"""P3-T1: explicit state machine with fake agents; loop bounds, SAFE_ESCALATE, traced transitions."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from app.orchestrator import MAX_CHALLENGE_LOOPS, MAX_EVAL_LOOPS, Deps, RunOptions, State, run, transition
from app.schemas.case import CaseInput
from app.schemas.evidence import EvaluationReport, Gap
from app.schemas.report import Report
from app.state import ChallengeResult, Plan, new_state
from app.store import Store

pytestmark = pytest.mark.p3


@pytest.fixture(autouse=True)
def _offline_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SAMPLE_MODE", "true")
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    monkeypatch.setenv("ARBITER_MEMORY", "off")


class FakePlanner:
    name = "PlannerAgent"
    role = "fake planner"

    def __call__(self, state: Any, ctx: Any) -> Any:
        state.plans.append(
            Plan(iteration=len(state.plans) + 1, steps=[], source="deterministic", rationale="t")
        )
        return state


class FakeEvidence:
    name = "EvidenceAgent"
    role = "fake evidence"

    def __init__(self, *, explode: bool = False) -> None:
        self.explode = explode

    def __call__(self, state: Any, ctx: Any) -> Any:
        if self.explode:
            raise RuntimeError("boom")
        return state


class FakeEvaluator:
    name = "EvaluatorAgent"
    role = "fake evaluator"

    def __init__(self, *, always_revise: bool) -> None:
        self.always_revise = always_revise

    def __call__(self, state: Any, ctx: Any) -> Any:
        gaps = [Gap(control_id="C06", reason="t", suggested_query_ids=["Q_VENDOR_INCIDENTS"])]
        state.evaluations.append(
            EvaluationReport(
                sufficient=not self.always_revise,
                gaps=gaps if self.always_revise else [],
                contradictions=[],
                ungrounded_claim_ids=[],
                dq_flags=[],
                injection_flags=[],
            )
        )
        return state


class FakeChallenger:
    name = "ChallengerAgent"
    role = "fake challenger"

    def __init__(self, action: str) -> None:
        self.action = action

    def __call__(self, state: Any, ctx: Any) -> Any:
        state.challenge = ChallengeResult(
            action=self.action,  # type: ignore[arg-type]
            reason_code="CHALLENGE_TEST",
            suggested_query_ids=["Q_SUBMISSION_DOCUMENTS"],
            source="deterministic",
        )
        return state


class FakeReporter:
    name = "ReporterAgent"
    role = "fake reporter"

    def __call__(self, state: Any, ctx: Any) -> Any:
        state.report = Report(
            summary="fake", rationale=[], recommended_actions=[], limitations=[], generator="fake"
        )
        return state


def _agents(*, revise: bool = False, challenge: str = "accept", explode: bool = False) -> dict[str, Any]:
    return {
        "planner": FakePlanner(),
        "evidence": FakeEvidence(explode=explode),
        "evaluator": FakeEvaluator(always_revise=revise),
        "challenger": FakeChallenger(challenge),
        "reporter": FakeReporter(),
    }


def _transitions(log_file: str) -> list[str]:
    rows = [json.loads(x) for x in Path(log_file).read_text(encoding="utf-8").splitlines() if x.strip()]
    assert rows[0]["action"] == "start_run" and rows[-1]["action"] == "complete_run"
    return [
        r["output_summary"].split(" ")[0]
        for r in rows
        if r["agent_name"] == "Orchestrator" and r["action"] == "transition"
    ]


def _run(**kwargs: Any) -> Any:
    case = CaseInput(vendor_id="VND-0003")
    return run(case, options=RunOptions(), deps=Deps(agents=_agents(**kwargs)))


HAPPY = [
    "INTAKE→PLAN",
    "PLAN→GATHER",
    "GATHER→EVALUATE",
    "EVALUATE→DECIDE_1",
    "DECIDE_1→MEMORY_CHECK",
    "MEMORY_CHECK→DECIDE_2",
    "DECIDE_2→CHALLENGE",
    "CHALLENGE→REPORT",
    "REPORT→CONTRACT",
    "CONTRACT→EXECUTE",
    "EXECUTE→DONE",
]


def test_p3_t1_happy_path_order() -> None:
    resp = _run()
    assert resp.status == "success"
    assert _transitions(resp.log_file) == HAPPY


def test_p3_t1_evaluator_loops_capped() -> None:
    resp = _run(revise=True)
    seq = _transitions(resp.log_file)
    assert MAX_EVAL_LOOPS == 2
    assert seq.count("EVALUATE→PLAN") == MAX_EVAL_LOOPS
    assert seq.count("EVALUATE→DECIDE_1") == 1
    assert resp.status == "partial_success"


def test_p3_t1_challenger_replan_capped() -> None:
    resp = _run(challenge="re_plan")
    seq = _transitions(resp.log_file)
    assert MAX_CHALLENGE_LOOPS == 1
    assert seq.count("CHALLENGE→PLAN") == MAX_CHALLENGE_LOOPS
    assert seq[-4:] == ["CHALLENGE→REPORT", "REPORT→CONTRACT", "CONTRACT→EXECUTE", "EXECUTE→DONE"]
    bundle = Store().get(resp.output.case_id)
    assert bundle.decision.outcome in {"ESCALATE", "DECLINE"}


def test_p3_t1_exception_goes_to_safe_escalate() -> None:
    resp = _run(explode=True)
    seq = _transitions(resp.log_file)
    assert "GATHER→SAFE_ESCALATE" in seq
    assert seq[-4:] == ["SAFE_ESCALATE→REPORT", "REPORT→CONTRACT", "CONTRACT→EXECUTE", "EXECUTE→DONE"]
    assert resp.status == "escalated"
    bundle = Store().get(resp.output.case_id)
    assert bundle.decision.outcome == "ESCALATE"
    assert "SYSTEM_RuntimeError" in bundle.decision.escalation_reasons
    assert bundle.report.generator == "template:v1"
    assert resp.output.actions and resp.output.actions[0].intent == "vendor.onboarding.escalate"


def test_p3_t1_every_state_change_traced() -> None:
    resp = _run(revise=True, challenge="re_plan")
    rows = [json.loads(x) for x in Path(resp.log_file).read_text(encoding="utf-8").splitlines() if x.strip()]
    seq = _transitions(resp.log_file)
    for before, after in zip(seq, seq[1:], strict=False):
        assert before.split("→")[1] == after.split("→")[0]
    assert all(r["run_id"] == resp.run_id for r in rows)


def _state(**updates: Any) -> Any:
    st = new_state(
        CaseInput(vendor_id="VND-0003"),
        run_id="r",
        as_of=date(2026, 10, 26),
        mode={},
        budget_deadline=float("inf"),
    )
    for key, value in updates.items():
        setattr(st, key, value)
    return st


def _evaluation(sufficient: bool) -> EvaluationReport:
    return EvaluationReport(
        sufficient=sufficient,
        gaps=[],
        contradictions=[],
        ungrounded_claim_ids=[],
        dq_flags=[],
        injection_flags=[],
    )


def _challenge(action: str) -> ChallengeResult:
    return ChallengeResult(action=action, source="deterministic")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("state", "updates", "expected"),
    [
        (State.INTAKE, {}, State.PLAN),
        (State.PLAN, {}, State.GATHER),
        (State.GATHER, {}, State.EVALUATE),
        (State.EVALUATE, {"evaluations": [_evaluation(False)], "eval_loops": 0}, State.PLAN),
        (State.EVALUATE, {"evaluations": [_evaluation(False)], "eval_loops": 1}, State.PLAN),
        (State.EVALUATE, {"evaluations": [_evaluation(False)], "eval_loops": 2}, State.DECIDE_1),
        (State.EVALUATE, {"evaluations": [_evaluation(True)], "eval_loops": 0}, State.DECIDE_1),
        (State.DECIDE_1, {}, State.MEMORY_CHECK),
        (State.MEMORY_CHECK, {}, State.DECIDE_2),
        (State.DECIDE_2, {}, State.CHALLENGE),
        (State.CHALLENGE, {"challenge": _challenge("re_plan"), "challenge_loops": 0}, State.PLAN),
        (State.CHALLENGE, {"challenge": _challenge("re_plan"), "challenge_loops": 1}, State.REPORT),
        (State.CHALLENGE, {"challenge": _challenge("escalate")}, State.REPORT),
        (State.CHALLENGE, {"challenge": _challenge("accept")}, State.REPORT),
        (State.SAFE_ESCALATE, {}, State.REPORT),
        (State.REPORT, {}, State.CONTRACT),
        (State.CONTRACT, {}, State.EXECUTE),
        (State.EXECUTE, {}, State.DONE),
    ],
)
def test_p3_t1_transition_table(state: State, updates: dict[str, Any], expected: State) -> None:
    assert transition(state, _state(**updates)) == expected
