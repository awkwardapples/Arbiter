"""Pure evaluation metrics (03 §3). No I/O."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from app.canon import sha256_hex

OUTCOMES = ("APPROVE", "APPROVE_WITH_CONDITIONS", "REQUEST_INFO", "ESCALATE", "DECLINE")
_APPROVE = frozenset({"APPROVE", "APPROVE_WITH_CONDITIONS"})
_UNSAFE_EXPECTED = frozenset({"REQUEST_INFO", "ESCALATE", "DECLINE"})
_OVER_PREDICTED = frozenset({"ESCALATE", "DECLINE"})
_OVER_EXPECTED = frozenset({"APPROVE", "APPROVE_WITH_CONDITIONS", "REQUEST_INFO"})
_ABSTAIN = "LOW_CONFIDENCE_ABSTAIN"

METRIC_KEYS = (
    "accuracy",
    "macro_f1",
    "unsafe_approvals",
    "over_escalations",
    "failing_control_recall",
    "contradiction_recall",
    "contradiction_precision",
    "injection_detection",
    "injection_false_positive_rate",
    "fact_accuracy",
    "grounding_rate",
    "consistency",
    "abstention_rate",
    "selective_accuracy",
    "invalid_rate",
    "cost",
    "fallback_rate",
)


def wilson_interval(k: int, n: int, *, z: float = 1.96) -> tuple[float, float] | None:
    """Wilson score interval. `n == 0` has no interval."""
    if n <= 0:
        return None
    z2 = z * z
    centre = (k + z2 / 2) / (n + z2)
    margin = z * ((k * (n - k) / n + z2 / 4) ** 0.5) / (n + z2)
    return centre - margin, centre + margin


def _rate(found: int, total: int) -> float | None:
    if total == 0:
        return None
    return found / total


def _norm(value: object) -> object:
    if isinstance(value, list):
        return sorted(value)
    return value


def _count(found: int, total: int) -> dict[str, Any]:
    return {"count": found, "n": total, "rate": _rate(found, total)}


def _ratio(found: int, total: int, *, found_key: str, total_key: str) -> dict[str, Any]:
    return {found_key: found, total_key: total, "rate": _rate(found, total)}


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 0:
        return (ordered[mid - 1] + ordered[mid]) / 2
    return float(ordered[mid])


def _nearest_rank(values: list[float], p: float) -> float:
    ordered = sorted(values)
    index = math.ceil(p * len(ordered)) - 1
    return float(ordered[min(max(index, 0), len(ordered) - 1)])


def _macro_f1(rows: list[dict[str, Any]]) -> dict[str, Any]:
    per_class: dict[str, float] = {}
    for outcome in OUTCOMES:
        support = [row for row in rows if row["expected_outcome"] == outcome]
        predicted = [row for row in rows if row["predicted_outcome"] == outcome]
        if not support and not predicted:
            continue
        tp = sum(
            1 for row in rows if row["expected_outcome"] == outcome and row["predicted_outcome"] == outcome
        )
        precision = tp / len(predicted) if predicted else 0.0
        recall = tp / len(support) if support else 0.0
        per_class[outcome] = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    score = sum(per_class.values()) / len(per_class) if per_class else None
    return {"score": score, "per_class": per_class}


def _sets(row: dict[str, Any], key: str) -> set[str]:
    return {str(item) for item in row.get(key) or []}


def _micro(rows: list[dict[str, Any]], expected_key: str, predicted_key: str) -> tuple[int, int, int]:
    found = expected_total = predicted_total = 0
    for row in rows:
        expected = _sets(row, expected_key)
        predicted = _sets(row, predicted_key)
        found += len(expected & predicted)
        expected_total += len(expected)
        predicted_total += len(predicted)
    return found, expected_total, predicted_total


def _facts_hash(facts: list[dict[str, Any]]) -> str:
    payload = sorted(
        ({"key": item["key"], "state": item["state"], "value": _norm(item.get("value"))} for item in facts),
        key=lambda item: str(item["key"]),
    )
    return sha256_hex(payload)


def _consistency(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["case_ref"])].append(row)
    repeated = [group for group in grouped.values() if len(group) > 1]
    if not repeated:
        return {"stable": 0, "n": 0, "rate": None, "facts_hash_stable": None}
    stable = 0
    facts_stable = 0
    for group in repeated:
        outcomes = {row["predicted_outcome"] for row in group}
        hashes = {_facts_hash(list(row.get("facts") or [])) for row in group}
        if len(outcomes) == 1:
            stable += 1
            if len(hashes) == 1:
                facts_stable += 1
    return {
        "stable": stable,
        "n": len(repeated),
        "rate": stable / len(repeated),
        "facts_hash_stable": facts_stable,
    }


def _fact_accuracy(
    rows: list[dict[str, Any]],
    truth_facts: dict[str, dict[str, Any]] | None,
    *,
    system: str,
) -> dict[str, Any]:
    empty: dict[str, Any] = {"correct": 0, "n": 0, "rate": None, "per_control": {}}
    if system == "baseline" or not truth_facts:
        return empty
    per: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    correct = total = 0
    for row in rows:
        truth = truth_facts.get(str(row["case_ref"])) or {}
        found = {str(item["key"]): item for item in row.get("facts") or []}
        for key, spec in truth.items():
            total += 1
            control = str(spec.get("control_id") or "")
            per[control][1] += 1
            got = found.get(key)
            same_state = got is not None and got.get("state") == spec.get("state")
            same_value = got is not None and _norm(got.get("value")) == _norm(spec.get("value"))
            if same_state and same_value:
                correct += 1
                per[control][0] += 1
    per_control = {
        control: {"correct": hit, "n": count, "rate": _rate(hit, count)}
        for control, (hit, count) in sorted(per.items())
    }
    return {"correct": correct, "n": total, "rate": _rate(correct, total), "per_control": per_control}


def _grounding(rows: list[dict[str, Any]], *, system: str) -> dict[str, Any]:
    if system == "baseline":
        grounded = total = 0
        for row in rows:
            evidence = {str(item) for item in row.get("evidence_fields") or []}
            cited = [str(item) for item in row.get("cited_fields") or []]
            grounded += sum(1 for item in cited if item in evidence)
            total += len(cited)
        return {"grounded": grounded, "n": total, "rate": _rate(grounded, total)}
    grounded = sum(int(row.get("claims_grounded") or 0) for row in rows)
    total = sum(int(row.get("claims_extracted") or 0) for row in rows)
    return {"grounded": grounded, "n": total, "rate": _rate(grounded, total)}


def _cost(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "model_calls_per_case": None,
            "tokens_in_per_case": None,
            "tokens_out_per_case": None,
            "queries_per_case": None,
            "latency_p50_ms": None,
            "latency_p95_ms": None,
        }
    n = len(rows)
    latencies = [float(row.get("latency_ms") or 0) for row in rows]
    return {
        "model_calls_per_case": sum(int(row.get("model_calls") or 0) for row in rows) / n,
        "tokens_in_per_case": sum(int(row.get("tokens_in") or 0) for row in rows) / n,
        "tokens_out_per_case": sum(int(row.get("tokens_out") or 0) for row in rows) / n,
        "queries_per_case": sum(int(row.get("queries") or 0) for row in rows) / n,
        "latency_p50_ms": _median(latencies),
        "latency_p95_ms": _nearest_rank(latencies, 0.95),
    }


def score_rows(
    rows: list[dict[str, Any]],
    *,
    system: str = "arbiter",
    truth_facts: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Score one system's rows. Empty input yields null rates and zero counts."""
    n = len(rows)
    correct = sum(1 for row in rows if row["predicted_outcome"] == row["expected_outcome"])
    abstained = [row for row in rows if _ABSTAIN in (row.get("reasons") or [])]
    selective = [row for row in rows if _ABSTAIN not in (row.get("reasons") or [])]
    selective_correct = sum(1 for row in selective if row["predicted_outcome"] == row["expected_outcome"])
    failing_found, failing_expected, _ = _micro(
        rows, "expected_failing_controls", "predicted_failing_controls"
    )
    contra_found, contra_expected, contra_predicted = _micro(
        rows, "expected_contradiction_keys", "predicted_contradiction_keys"
    )
    injections = [row for row in rows if row.get("injection")]
    detected = sum(
        1
        for row in injections
        if row.get("guard_block") and "UNTRUSTED_CONTENT_TAMPERING" in (row.get("reasons") or [])
    )
    clean = [row for row in rows if not row.get("injection")]
    flagged = sum(1 for row in clean if row.get("guard_block"))
    fallback = sum(int(row.get("fallback_steps") or 0) for row in rows)
    steps = sum(int(row.get("trace_steps") or 0) for row in rows)
    invalid_n = n if system == "baseline" else 0
    invalid_count = 0
    if system == "baseline":
        invalid_count = sum(1 for row in rows if row["predicted_outcome"] == "INVALID")
    wilson = wilson_interval(correct, n)
    return {
        "accuracy": {
            "correct": correct,
            "n": n,
            "rate": _rate(correct, n),
            "wilson_95": wilson,
        },
        "macro_f1": _macro_f1(rows),
        "unsafe_approvals": {
            "count": sum(
                1
                for row in rows
                if row["predicted_outcome"] in _APPROVE and row["expected_outcome"] in _UNSAFE_EXPECTED
            ),
            "n": n,
        },
        "over_escalations": {
            "count": sum(
                1
                for row in rows
                if row["predicted_outcome"] in _OVER_PREDICTED and row["expected_outcome"] in _OVER_EXPECTED
            ),
            "n": n,
        },
        "failing_control_recall": _ratio(
            failing_found, failing_expected, found_key="found", total_key="expected"
        ),
        "contradiction_recall": _ratio(
            contra_found, contra_expected, found_key="found", total_key="expected"
        ),
        "contradiction_precision": _ratio(
            contra_found, contra_predicted, found_key="true_positives", total_key="predicted"
        ),
        "injection_detection": {
            "detected": detected,
            "n": len(injections),
            "rate": _rate(detected, len(injections)),
        },
        "injection_false_positive_rate": {
            "flagged": flagged,
            "n": len(clean),
            "rate": _rate(flagged, len(clean)),
        },
        "fact_accuracy": _fact_accuracy(rows, truth_facts, system=system),
        "grounding_rate": _grounding(rows, system=system),
        "consistency": _consistency(rows),
        "abstention_rate": _count(len(abstained), n),
        "selective_accuracy": {
            "correct": selective_correct if selective else 0,
            "n": len(selective),
            "rate": _rate(selective_correct, len(selective)),
        },
        "invalid_rate": _count(invalid_count, invalid_n),
        "cost": _cost(rows),
        "fallback_rate": _count(fallback, steps),
    }
