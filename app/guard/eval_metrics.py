"""Guard evaluation metrics (precision / recall / F1)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GuardMetrics:
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    tn: int
    fn: int


def compute_metrics(*, predicted_positive: list[bool], expected_positive: list[bool]) -> GuardMetrics:
    tp = fp = tn = fn = 0
    for pred, exp in zip(predicted_positive, expected_positive, strict=True):
        if pred and exp:
            tp += 1
        elif pred and not exp:
            fp += 1
        elif not pred and exp:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return GuardMetrics(precision=precision, recall=recall, f1=f1, tp=tp, fp=fp, tn=tn, fn=fn)
