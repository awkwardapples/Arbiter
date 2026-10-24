"""Reader-facing wording built from API fields (lane P14-B). No codes outside technical details."""

from __future__ import annotations

from collections import Counter
from typing import Any

# The API returns the outcome code; these mirror app/labels.py (a test keeps them in step).
OUTCOME_WORDS: dict[str, tuple[str, str]] = {
    "APPROVE": ("Approve", "Every required control passed, so the vendor can be onboarded."),
    "APPROVE_WITH_CONDITIONS": (
        "Approve with conditions",
        "Approval stands only if the stated conditions are met.",
    ),
    "REQUEST_INFO": (
        "Request information",
        "Required evidence is missing, so the vendor must reply before a decision.",
    ),
    "ESCALATE": ("Escalate", "A person must decide; the policy will not approve this case as it stands."),
    "DECLINE": ("Decline", "A hard gate failed. Do not onboard this vendor."),
}
STATE_WORDS = {"TRUE": "Met", "FALSE": "Not met", "UNKNOWN": "Unverified"}


def outcome_label(outcome: str) -> str:
    return OUTCOME_WORDS.get(outcome, (outcome.replace("_", " ").capitalize(), ""))[0]


def outcome_meaning(outcome: str) -> str:
    return OUTCOME_WORDS.get(outcome, ("", ""))[1]


def _count(n: int, noun: str, plural: str | None = None) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {plural or noun + 's'}"


def workload_sentence(workload: dict[str, Any]) -> str:
    """One sentence from the measured workload fields and nothing else."""
    systems = len(workload.get("systems_queried") or [])
    contradictions = int(workload.get("contradictions") or 0)
    found = (
        "no contradictions found"
        if contradictions == 0
        else f"{_count(contradictions, 'contradiction')} found"
    )
    calls = int(workload.get("model_calls") or 0)
    models = [str(m) for m in workload.get("models") or []]
    if calls == 0:
        model_part = "no model calls (offline fallback)"
    else:
        family = "Nemotron" if any("nemotron" in m.lower() for m in models) else "model"
        model_part = _count(calls, f"{family} call")
    seconds = round(float(workload.get("elapsed_seconds") or 0))
    return (
        f"Checked {_count(systems, 'system')}, "
        f"{_count(int(workload.get('queries') or 0), 'query', 'queries')}, "
        f"{_count(int(workload.get('answers_read') or 0), 'answer')}, "
        f"{_count(int(workload.get('documents_read') or 0), 'document')}, "
        f"{found}, in {seconds} s with {model_part}"
    )


def confidence_sentence(confidence: dict[str, Any], controls: list[dict[str, Any]]) -> str:
    """'Confidence 62%: 2 controls unverified: C01 MFA, C04 encryption' instead of a bare percentage."""
    pct = int(round(float(confidence.get("value") or 0) * 100))
    titles = {str(c.get("control_id")): str(c.get("title") or "") for c in controls}
    unknown = [str(c) for c in confidence.get("unknown_controls") or []]
    if not unknown:
        return f"Confidence {pct}%: every required control is verified"
    named = ", ".join(f"{cid} {titles.get(cid, '')}".strip() for cid in unknown)
    return f"Confidence {pct}%: {_count(len(unknown), 'control')} unverified: {named}"


def portfolio_metrics(queue: list[dict[str, Any]]) -> dict[str, Any]:
    by_outcome = Counter(str(item.get("outcome")) for item in queue if item.get("outcome"))
    return {"total": len(queue), "by_outcome": dict(by_outcome)}


_STEP_WORDS: dict[tuple[str, str], str] = {
    ("PlannerAgent", "plan"): "Planned which queries to run",
    ("EvidenceAgent", "query_run"): "Queried the systems of record",
    ("Orchestrator", "query_run"): "Queried the systems of record",
    ("EvidenceAgent", "extract_claims"): "Read the vendor's answers and documents",
    ("ScoutGuard", "guard_segment"): "Screened vendor text for tampering",
    ("EvaluatorAgent", "evaluate"): "Checked the evidence was sufficient",
    ("ChallengerAgent", "challenge"): "Challenged the draft decision",
    ("ChallengerAgent", "request_replan"): "Asked for more evidence",
    ("MemoryKeeper", "retrieve_precedents"): "Looked up governed precedents",
    ("Orchestrator", "memory_check"): "Checked precedent eligibility",
    ("Orchestrator", "redecide"): "Re-ran the policy on the new facts",
    ("ReporterAgent", "report"): "Wrote the brief and the drafts",
    ("ActionExecutor", "execute_action"): "Issued the signed action",
}
_SKIPPED_STEPS = {
    ("Orchestrator", "transition"),
    ("Orchestrator", "start_run"),
    ("Orchestrator", "complete_run"),
}
_RESULT_WORDS = {
    "success": "done",
    "needs_revision": "asked for more evidence",
    "escalated": "escalated",
    "fallback": "used the offline fallback",
}


def stage_rows(trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per kind of step, in order of first appearance, described in words."""
    order: list[tuple[str, str]] = []
    counts: Counter[tuple[str, str]] = Counter()
    last: dict[tuple[str, str], str] = {}
    for event in trace:
        key = (str(event.get("agent_name")), str(event.get("action")))
        if key in _SKIPPED_STEPS:
            continue
        if key not in counts:
            order.append(key)
        counts[key] += 1
        last[key] = str(event.get("status") or "")
    rows = []
    for key in order:
        words = _STEP_WORDS.get(key) or f"{key[0]} {key[1]}".replace("_", " ")
        status = last[key]
        rows.append(
            {
                "Step": words,
                "Times": counts[key],
                "Result": _RESULT_WORDS.get(status, status.replace("_", " ")),
            }
        )
    return rows


def control_rows(controls: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows = []
    for control in controls:
        gate = control.get("hard_gate")
        rows.append(
            {
                "Control": f"{control.get('control_id')} · {control.get('title')}",
                "Status": STATE_WORDS.get(str(control.get("state")), "Unverified"),
                "Required": "yes" if control.get("required") else "no",
                "If it fails": f"{outcome_label(str(gate))} (hard gate)" if gate else "Lowers confidence",
            }
        )
    return rows
