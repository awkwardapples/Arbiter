"""Tune tier gates on the calibration split. Weights stay fixed. The test split is not read."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.policy.engine import decide
from app.policy.loader import Calibration, load_default
from app.schemas.decision import PolicyInputs
from eval.corpus import split_document
from eval.harness import force_offline, run

_GATES = (0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95)
_APPROVE = frozenset({"APPROVE", "APPROVE_WITH_CONDITIONS"})
_HOLD = frozenset({"REQUEST_INFO", "ESCALATE", "DECLINE"})
_OBJECTIVE = (
    "maximise accuracy subject to zero unsafe approvals; "
    "ties take the higher gate; weights are fixed a priori"
)


@dataclass(frozen=True)
class CalibrationRun:
    path: Path
    split: str
    unsafe_approvals: int
    split_sha256: str


def calibrate_split(*, out_dir: Path, active_path: Path | None = None) -> CalibrationRun:
    """Recompute `decide` on stored calibration-split inputs. Does not call a model."""
    settings = force_offline()
    document = split_document()
    sha = str(document["sha256"]["calibration"])
    with tempfile.TemporaryDirectory(prefix="arbiter-cal-") as tmp:
        results = run(["arbiter_offline"], ["calibration"], results_root=Path(tmp))
        records = [
            json.loads(line)
            for line in (results / "decisions.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    policy, current = load_default()
    chosen, results_body = _search(
        records,
        policy=policy,
        weights=dict(current.weights),
        base=dict(current.gates),
    )
    version = f"cal-{settings.ARBITER_AS_OF.isoformat()}-{sha[:8]}"
    payload = {
        "version": version,
        "gates": chosen,
        "weights": dict(current.weights),
        "split_sha256": sha,
        "objective": _OBJECTIVE,
        "calibration_results": results_body,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{version}.json"
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") != text:
        raise FileExistsError(f"refusing to overwrite a different calibration file: {path.name}")
    path.write_text(text, encoding="utf-8")
    if active_path is not None:
        active_path.write_text(version + "\n", encoding="utf-8")
    return CalibrationRun(
        path=path,
        split="calibration",
        unsafe_approvals=int(results_body["unsafe_approvals"]),
        split_sha256=sha,
    )


def _search(
    records: list[dict[str, Any]],
    *,
    policy: Any,
    weights: dict[str, float],
    base: dict[str, float],
) -> tuple[dict[str, float], dict[str, Any]]:
    chosen = dict(base)
    per_tier: dict[str, dict[str, Any]] = {}
    for tier in ("T1", "T2", "T3"):
        group = [row for row in records if row["tier"] == tier]
        if not group:
            per_tier[tier] = {"gate": chosen.get(tier), "n": 0, "correct": 0}
            continue
        best_gate = _GATES[-1]
        best_correct = -1
        for gate in _GATES:
            trial = dict(chosen)
            trial[tier] = gate
            correct, unsafe = _tally(group, gates=trial, policy=policy, weights=weights)
            if unsafe != 0:
                continue
            if correct > best_correct or (correct == best_correct and gate > best_gate):
                best_correct = correct
                best_gate = gate
        chosen[tier] = best_gate
        correct, _unsafe = _tally(group, gates=chosen, policy=policy, weights=weights)
        per_tier[tier] = {"gate": best_gate, "n": len(group), "correct": correct}
    correct, unsafe = _tally(records, gates=chosen, policy=policy, weights=weights)
    body = {
        "unsafe_approvals": unsafe,
        "n": len(records),
        "correct": correct,
        "per_tier": per_tier,
    }
    return chosen, body


def _tally(
    records: list[dict[str, Any]],
    *,
    gates: dict[str, float],
    policy: Any,
    weights: dict[str, float],
) -> tuple[int, int]:
    calibration = Calibration(version="candidate", gates=gates, weights=weights)
    correct = unsafe = 0
    for row in records:
        outcome = decide(PolicyInputs.model_validate(row["policy_inputs"]), policy, calibration).outcome
        expected = row["expected_outcome"]
        if outcome == expected:
            correct += 1
        if outcome in _APPROVE and expected in _HOLD:
            unsafe += 1
    return correct, unsafe
