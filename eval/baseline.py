"""Single-call baseline. Same registry evidence as Arbiter; no deterministic verdict."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.agents.planner import allowed_queries, build_params
from app.config import Settings
from app.data.factory import get_backend
from app.data.registry import load_registry
from app.errors import ArbiterError, ParseFailure
from app.guard.pii import redact
from app.llm.generator import generate
from app.policy.loader import Policy, load_default
from app.schemas.case import CaseInput
from app.state import new_state
from app.tracing import Tracer

_PROMPT = Path(__file__).resolve().parent / "prompts" / "baseline.md"
_TEXT_FIELDS = frozenset({"answer_text", "text", "question", "title"})


class BaselineVerdict(BaseModel):
    model_config = ConfigDict(extra="ignore")

    outcome: str
    reasons: list[str] = []
    failing_controls: list[str] = []
    cited_fields: list[str] = []


@dataclass
class BaselineResult:
    outcome: str
    reasons: list[str] = field(default_factory=list)
    failing_controls: list[str] = field(default_factory=list)
    cited_fields: list[str] = field(default_factory=list)
    evidence_fields: list[str] = field(default_factory=list)
    queries: int = 0


def run_baseline(case_input: CaseInput, *, settings: Settings, tracer: Tracer) -> BaselineResult:
    """One deep-route call. Offline, timeout, or a failed repair scores INVALID."""
    evidence: dict[str, Any] = {}
    queries = 0
    try:
        evidence, queries = _evidence(case_input, settings=settings, tracer=tracer)
        policy, _calibration = load_default()
        prompt = _PROMPT.read_text(encoding="utf-8")
        prompt = prompt.replace("<<POLICY>>", _policy_text(policy)).replace(
            "<<EVIDENCE>>", json.dumps(evidence, sort_keys=True, default=str)
        )
        result = generate(
            prompt,
            route="deep",
            response="json",
            schema=BaselineVerdict,
            purpose="baseline",
            tracer=tracer,
            agent_name="Baseline",
        )
        parsed = result.parsed
        if not isinstance(parsed, BaselineVerdict):
            raise ParseFailure("baseline JSON did not match BaselineVerdict")
        if parsed.outcome not in {
            "APPROVE",
            "APPROVE_WITH_CONDITIONS",
            "REQUEST_INFO",
            "ESCALATE",
            "DECLINE",
        }:
            raise ParseFailure(f"unknown outcome {parsed.outcome}")
        return BaselineResult(
            outcome=parsed.outcome,
            reasons=list(parsed.reasons),
            failing_controls=list(parsed.failing_controls),
            cited_fields=list(parsed.cited_fields),
            evidence_fields=sorted(_keys(evidence)),
            queries=queries,
        )
    except (ArbiterError, ParseFailure):
        return BaselineResult(outcome="INVALID", evidence_fields=sorted(_keys(evidence)), queries=queries)


def _evidence(case_input: CaseInput, *, settings: Settings, tracer: Tracer) -> tuple[dict[str, Any], int]:
    state = new_state(
        case_input,
        run_id=tracer.run_id,
        as_of=settings.ARBITER_AS_OF,
        mode=settings.mode(),
        budget_deadline=0,
    )
    backend = get_backend(settings, tracer, case_input.submission)
    registry = load_registry()
    order = ["Q_VENDOR_PROFILE"]
    allowed = allowed_queries(state)
    for query_id in ("Q_VENDOR_ALIASES", "Q_VENDOR_COMPONENTS"):
        if query_id in allowed:
            order.append(query_id)
    order.extend(query_id for query_id in allowed if query_id not in order)
    evidence: dict[str, Any] = {}
    for query_id in order:
        params = build_params(query_id, registry[query_id], state)
        result = backend.run(query_id, params)
        state.executed_queries[query_id] = result
        if query_id == "Q_VENDOR_PROFILE" and result.rows:
            state.profile = {key: _plain(value) for key, value in result.rows[0].items()}
        rows = _redact_rows(result.rows)
        evidence[query_id] = rows
        tracer.event(
            "Baseline",
            "query",
            input_summary=query_id,
            output_summary=f"rows={len(rows)}",
            query_id=query_id,
            rows=len(rows),
            backend=result.backend,
            status="fallback" if result.fallback_from else "success",
        )
    return evidence, len(order)


def _policy_text(policy: Policy) -> str:
    lines = [
        f"{policy.policy_id} version {policy.version}",
        "Controls:",
    ]
    for control in policy.controls:
        lines.append(
            f"- {control.id} {control.title}; required_for={','.join(control.required_for)}; "
            f"hard_gate={control.hard_gate or 'none'}"
        )
        lines.append(f"  rule={json.dumps(control.rule, sort_keys=True)}")
    lines.append("Outcome rules in order, first match wins:")
    for rule in policy.outcome_rules:
        lines.append(f"- {rule.id} when {rule.when} -> {rule.outcome} ({rule.reason})")
    return "\n".join(lines)


def _redact_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    redacted: list[dict[str, Any]] = []
    for row in rows:
        copy: dict[str, Any] = {}
        for key, value in row.items():
            if key in _TEXT_FIELDS and isinstance(value, str):
                copy[key] = redact(value)[0]
            else:
                copy[key] = _plain(value)
        redacted.append(copy)
    return redacted


def _plain(value: object) -> object:
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return value.isoformat()  # type: ignore[no-any-return]
    return value


def _keys(value: object) -> set[str]:
    found: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                found.add(str(key))
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    return found
