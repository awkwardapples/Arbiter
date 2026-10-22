"""P5-T1: pure metric functions, including empty input, full abstention, and INVALID."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.p5b

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


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    z2 = z * z
    centre = (k + z2 / 2) / (n + z2)
    margin = z * ((k * (n - k) / n + z2 / 4) ** 0.5) / (n + z2)
    return centre - margin, centre + margin


def _row(**overrides: object) -> dict:
    base: dict = {
        "case_ref": "C1",
        "expected_outcome": "APPROVE",
        "predicted_outcome": "APPROVE",
        "reasons": [],
        "expected_failing_controls": [],
        "predicted_failing_controls": [],
        "expected_contradiction_keys": [],
        "predicted_contradiction_keys": [],
        "injection": False,
        "guard_block": False,
        "repeat": 0,
        "tokens_in": 0,
        "tokens_out": 0,
        "model_calls": 0,
        "queries": 0,
        "latency_ms": 0,
        "trace_steps": 0,
        "fallback_steps": 0,
        "facts": [],
        "claims_extracted": 0,
        "claims_grounded": 0,
        "cited_fields": [],
        "evidence_fields": [],
    }
    base.update(overrides)
    return base


def _score(rows: list[dict], **kwargs: object) -> dict:
    from eval.metrics import score_rows

    return score_rows(rows, **kwargs)  # type: ignore[arg-type]


def test_p5_t1_keys_empty_and_wilson() -> None:
    """P5-T1: empty input yields null rates, and the Wilson interval matches the closed form."""
    from eval.metrics import wilson_interval

    empty = _score([])
    assert set(METRIC_KEYS) <= set(empty)
    assert empty["accuracy"] == {"correct": 0, "n": 0, "rate": None, "wilson_95": None}
    assert empty["macro_f1"]["score"] is None
    assert empty["abstention_rate"]["rate"] is None
    assert empty["selective_accuracy"]["rate"] is None
    assert wilson_interval(0, 0) is None

    scored = _score(
        [
            _row(predicted_outcome="APPROVE"),
            _row(case_ref="C2", predicted_outcome="ESCALATE"),
        ]
    )
    assert scored["accuracy"]["correct"] == 1
    assert scored["accuracy"]["n"] == 2
    assert scored["accuracy"]["rate"] == pytest.approx(0.5)
    lo, hi = _wilson(1, 2)
    assert scored["accuracy"]["wilson_95"] == pytest.approx((lo, hi))
    assert wilson_interval(1, 2) == pytest.approx((lo, hi))


def test_p5_t1_abstain_invalid_and_direction() -> None:
    """P5-T1: all-abstain selective accuracy is null; INVALID is wrong; unsafe and over-escalation counts."""
    abstained = _score(
        [
            _row(predicted_outcome="ESCALATE", reasons=["LOW_CONFIDENCE_ABSTAIN"]),
            _row(
                case_ref="C2",
                expected_outcome="ESCALATE",
                predicted_outcome="ESCALATE",
                reasons=["OTHER", "LOW_CONFIDENCE_ABSTAIN"],
            ),
        ]
    )
    assert abstained["abstention_rate"] == {"count": 2, "n": 2, "rate": 1.0}
    assert abstained["selective_accuracy"] == {"correct": 0, "n": 0, "rate": None}
    assert abstained["accuracy"]["correct"] == 1
    assert abstained["accuracy"]["n"] == 2

    invalid = _score(
        [_row(expected_outcome="APPROVE", predicted_outcome="INVALID")],
        system="baseline",
    )
    assert invalid["invalid_rate"] == {"count": 1, "n": 1, "rate": 1.0}
    assert invalid["accuracy"]["correct"] == 0
    assert invalid["macro_f1"]["score"] == pytest.approx(0.0)
    parsed = _score(
        [_row(expected_outcome="APPROVE", predicted_outcome="APPROVE")],
        system="baseline",
    )
    assert parsed["invalid_rate"] == {"count": 0, "n": 1, "rate": 0.0}

    arbiter = _score([_row(predicted_outcome="INVALID")])
    assert arbiter["invalid_rate"]["rate"] is None

    direction = _score(
        [
            _row(case_ref="U", expected_outcome="ESCALATE", predicted_outcome="APPROVE"),
            _row(case_ref="W", expected_outcome="REQUEST_INFO", predicted_outcome="APPROVE_WITH_CONDITIONS"),
            _row(case_ref="O", expected_outcome="APPROVE", predicted_outcome="DECLINE"),
            _row(case_ref="R", expected_outcome="REQUEST_INFO", predicted_outcome="ESCALATE"),
            _row(case_ref="N", expected_outcome="DECLINE", predicted_outcome="ESCALATE"),
            _row(case_ref="K", expected_outcome="APPROVE", predicted_outcome="APPROVE"),
        ]
    )
    assert direction["unsafe_approvals"] == {"count": 2, "n": 6}
    assert direction["over_escalations"] == {"count": 2, "n": 6}


def test_p5_t1_controls_contradictions_injection_facts() -> None:
    """P5-T1: recall, precision, injection rates, fact match (list order ignored), and baseline fact null."""
    controls = _score(
        [
            _row(
                expected_failing_controls=["C01", "C02"],
                predicted_failing_controls=["C01", "C09"],
                expected_contradiction_keys=["a", "b"],
                predicted_contradiction_keys=["b", "c"],
            ),
            _row(case_ref="C2"),
        ]
    )
    assert controls["failing_control_recall"] == {"found": 1, "expected": 2, "rate": 0.5}
    assert controls["contradiction_recall"] == {"found": 1, "expected": 2, "rate": 0.5}
    assert controls["contradiction_precision"] == {"true_positives": 1, "predicted": 2, "rate": 0.5}

    none = _score([_row()])
    assert none["failing_control_recall"]["rate"] is None
    assert none["contradiction_recall"]["rate"] is None
    assert none["contradiction_precision"]["rate"] is None

    injection = _score(
        [
            _row(
                case_ref="I1",
                injection=True,
                guard_block=True,
                reasons=["UNTRUSTED_CONTENT_TAMPERING"],
            ),
            _row(case_ref="I2", injection=True, guard_block=True, reasons=["OTHER"]),
            _row(case_ref="C1", injection=False, guard_block=True),
            _row(case_ref="C2", injection=False, guard_block=False),
        ]
    )
    assert injection["injection_detection"] == {"detected": 1, "n": 2, "rate": 0.5}
    assert injection["injection_false_positive_rate"] == {"flagged": 1, "n": 2, "rate": 0.5}

    truth = {
        "C1": {
            "mfa.admin_enforced": {"state": "TRUE", "value": True, "control_id": "C01"},
            "residency.regions": {"state": "TRUE", "value": ["EU", "US"], "control_id": "C03"},
            "dpa.signed": {"state": "TRUE", "value": False, "control_id": "C02"},
        }
    }
    facts = _score(
        [
            _row(
                facts=[
                    {"key": "mfa.admin_enforced", "state": "TRUE", "value": True, "control_id": "C01"},
                    {"key": "residency.regions", "state": "TRUE", "value": ["US", "EU"], "control_id": "C03"},
                    {"key": "dpa.signed", "state": "FALSE", "value": False, "control_id": "C02"},
                ]
            )
        ],
        truth_facts=truth,
    )
    assert facts["fact_accuracy"]["correct"] == 2
    assert facts["fact_accuracy"]["n"] == 3
    assert facts["fact_accuracy"]["rate"] == pytest.approx(2 / 3)
    assert facts["fact_accuracy"]["per_control"]["C01"] == {"correct": 1, "n": 1, "rate": 1.0}
    assert facts["fact_accuracy"]["per_control"]["C02"]["correct"] == 0

    baseline_facts = _score([_row(facts=facts_row())], system="baseline", truth_facts=truth)
    assert baseline_facts["fact_accuracy"]["rate"] is None


def facts_row() -> list[dict]:
    return [{"key": "mfa.admin_enforced", "state": "TRUE", "value": True, "control_id": "C01"}]


def test_p5_t1_grounding_consistency_cost_f1() -> None:
    """P5-T1: grounding, consistency, cost percentiles, fallback share, and macro F1."""
    grounded = _score([_row(claims_extracted=4, claims_grounded=1)])
    assert grounded["grounding_rate"] == {"grounded": 1, "n": 4, "rate": 0.25}
    assert _score([_row()])["grounding_rate"]["rate"] is None

    cited = _score(
        [_row(cited_fields=["kept", "missing"], evidence_fields=["kept", "other"])],
        system="baseline",
    )
    assert cited["grounding_rate"] == {"grounded": 1, "n": 2, "rate": 0.5}
    assert _score([_row(cited_fields=[])], system="baseline")["grounding_rate"]["rate"] is None

    same = [{"key": "a", "state": "TRUE", "value": 1, "control_id": "C01"}]
    other = [{"key": "a", "state": "FALSE", "value": 1, "control_id": "C01"}]
    consistent = _score(
        [
            _row(case_ref="C1", repeat=0, facts=same),
            _row(case_ref="C1", repeat=1, facts=same),
            _row(case_ref="C2", repeat=0, predicted_outcome="APPROVE", facts=same),
            _row(case_ref="C2", repeat=1, predicted_outcome="APPROVE", facts=other),
            _row(case_ref="C3", repeat=0, predicted_outcome="APPROVE"),
            _row(case_ref="C3", repeat=1, predicted_outcome="ESCALATE"),
        ]
    )
    assert consistent["consistency"]["stable"] == 2
    assert consistent["consistency"]["n"] == 3
    assert consistent["consistency"]["rate"] == pytest.approx(2 / 3)
    assert consistent["consistency"]["facts_hash_stable"] == 1
    assert _score([_row(case_ref="C1"), _row(case_ref="C2")])["consistency"]["rate"] is None

    cost = _score(
        [
            _row(
                case_ref="A",
                latency_ms=10,
                model_calls=2,
                tokens_in=10,
                tokens_out=20,
                queries=1,
                trace_steps=3,
                fallback_steps=1,
            ),
            _row(
                case_ref="B",
                latency_ms=30,
                model_calls=4,
                tokens_in=30,
                tokens_out=40,
                queries=3,
                trace_steps=1,
                fallback_steps=0,
            ),
        ]
    )
    assert cost["cost"]["model_calls_per_case"] == pytest.approx(3)
    assert cost["cost"]["tokens_in_per_case"] == pytest.approx(20)
    assert cost["cost"]["tokens_out_per_case"] == pytest.approx(30)
    assert cost["cost"]["queries_per_case"] == pytest.approx(2)
    assert cost["cost"]["latency_p50_ms"] == pytest.approx(20)
    assert cost["cost"]["latency_p95_ms"] == pytest.approx(30)
    assert cost["fallback_rate"] == {"count": 1, "n": 4, "rate": 0.25}
    assert _score([])["cost"]["latency_p50_ms"] is None

    # APPROVE support is a miss (F1 0). ESCALATE precision 1/2, recall 1, F1 2/3.
    # Classes with neither support nor predictions are left out. Macro is the mean of those two.
    f1 = _score(
        [
            _row(case_ref="A", expected_outcome="APPROVE", predicted_outcome="ESCALATE"),
            _row(case_ref="B", expected_outcome="ESCALATE", predicted_outcome="ESCALATE"),
        ]
    )
    assert f1["macro_f1"]["score"] == pytest.approx(1 / 3)
