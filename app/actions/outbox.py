"""Outbox: the only place an executed contract leaves a side effect (a JSON file per action)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.canon import canonical_json
from app.schemas.contract import ExecutionContract

_SYSTEM_BY_PREFIX = {"procurement.": "procurement", "outbox.email.": "email", "itsm.": "itsm"}


def system_for(capability: str) -> str:
    for prefix, system in _SYSTEM_BY_PREFIX.items():
        if capability.startswith(prefix):
            return system
    raise ValueError(f"no outbox system for capability {capability!r}")


def write(contract: ExecutionContract, payload: dict[str, Any], *, root: Path) -> Path:
    system = system_for(contract.tool_plan[0].capability)
    folder = root / system
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{contract.contract_id}.json"
    body = {
        "contract_id": contract.contract_id,
        "case_id": contract.case_id,
        "intent": contract.intent,
        **payload,
    }
    path.write_text(json.dumps(json.loads(canonical_json(body)), indent=2) + "\n", encoding="utf-8")
    return path
