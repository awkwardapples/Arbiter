"""Load eval splits, labels and case inputs. This package is outside `app/`, so label reads stay here."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.policy.dsl import referenced_keys
from app.policy.loader import load_default
from app.schemas.case import CaseInput, VendorSubmission

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "data" / "evals"


def split_document() -> dict[str, Any]:
    payload = json.loads((EVALS / "splits.json").read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("splits.json is not an object")
    return payload


def labels() -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for line in (EVALS / "labels.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        found[str(item["case_ref"])] = item
    return found


def truth_facts() -> dict[str, dict[str, dict[str, Any]]]:
    """case_ref → fact key → {state, value, control_id}."""
    policy, _ = load_default()
    owner: dict[str, str] = {}
    for control in policy.controls:
        for key in referenced_keys(control.rule):
            owner.setdefault(key, control.id)
    found: dict[str, dict[str, dict[str, Any]]] = {}
    for line in (EVALS / "truth_facts.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        facts: dict[str, dict[str, Any]] = {}
        for key, spec in (item.get("facts") or {}).items():
            facts[str(key)] = {
                "state": spec.get("state"),
                "value": spec.get("value"),
                "control_id": owner.get(str(key), ""),
            }
        found[str(item["case_ref"])] = facts
    return found


def case_input(case_ref: str) -> CaseInput:
    path = EVALS / "inline" / f"{case_ref}.json"
    if path.is_file():
        submission = VendorSubmission.model_validate(json.loads(path.read_text(encoding="utf-8")))
        return CaseInput(submission=submission)
    return CaseInput(vendor_id=case_ref)


def cases_for(split_names: list[str]) -> list[str]:
    document = split_document()
    refs: list[str] = []
    for name in split_names:
        if name not in document or not isinstance(document[name], list):
            raise ValueError(f"unknown split: {name}")
        refs.extend(str(item) for item in document[name])
    return refs
