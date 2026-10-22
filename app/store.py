"""Case store: JSON files under `var/` (P4-B swaps in SQLite behind the same interface)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.errors import NotFound
from app.schemas.case import CaseInput
from app.schemas.contract import ExecutionContract
from app.schemas.decision import DecisionRecord
from app.schemas.report import Report

_RISK_ORDER = {"DECLINE": 0, "ESCALATE": 1, "REQUEST_INFO": 2, "APPROVE_WITH_CONDITIONS": 3, "APPROVE": 4}


class CaseBundle(BaseModel):
    case_id: str
    run_id: str
    created_at: datetime
    status: str
    mode: dict[str, str]
    input: CaseInput
    vendor_ref: str
    legal_name: str
    decision: DecisionRecord
    first_decision: DecisionRecord | None = None
    report: Report
    contract_ids: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    log_file: str
    limitations: list[str] = Field(default_factory=list)


class Store:
    def __init__(self, root: Path | str = "var") -> None:
        self.root = Path(root)

    def _dir(self, name: str) -> Path:
        path = self.root / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _write(path: Path, model: BaseModel | dict[str, Any]) -> None:
        data = model.model_dump(mode="json") if isinstance(model, BaseModel) else model
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(path)

    def save(self, bundle: CaseBundle) -> None:
        self._write(self._dir("cases") / f"{bundle.case_id}.json", bundle)

    def get(self, case_id: str) -> CaseBundle:
        path = self.root / "cases" / f"{case_id}.json"
        if not path.is_file():
            raise NotFound(f"case {case_id} not found")
        return CaseBundle.model_validate_json(path.read_text(encoding="utf-8"))

    def list(self, order: Literal["risk", "recent"] = "risk") -> list[CaseBundle]:
        folder = self.root / "cases"
        bundles = [
            CaseBundle.model_validate_json(p.read_text(encoding="utf-8")) for p in folder.glob("*.json")
        ]
        if order == "recent":
            return sorted(bundles, key=lambda b: b.created_at, reverse=True)
        return sorted(
            bundles,
            key=lambda b: (_RISK_ORDER[b.decision.outcome], -b.decision.residual_risk, b.case_id),
        )

    def put_contract(self, contract: ExecutionContract) -> None:
        self._write(self._dir("contracts") / f"{contract.contract_id}.json", contract)

    def contracts_for(self, case_id: str) -> list[ExecutionContract]:
        folder = self.root / "contracts"
        found = [
            ExecutionContract.model_validate_json(p.read_text(encoding="utf-8"))
            for p in folder.glob("*.json")
        ]
        return sorted((c for c in found if c.case_id == case_id), key=lambda c: (c.issued_at, c.contract_id))

    def put_review(self, review: BaseModel | dict[str, Any]) -> None:
        data = review.model_dump(mode="json") if isinstance(review, BaseModel) else dict(review)
        folder = self._dir("reviews")
        index = len(list(folder.glob(f"{data['case_id']}-*.json"))) + 1
        self._write(folder / f"{data['case_id']}-{index:03d}.json", data)

    def reviews_for(self, case_id: str) -> list[dict[str, Any]]:
        folder = self.root / "reviews"
        return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob(f"{case_id}-*.json"))]

    def put_human_decision(self, record: DecisionRecord) -> None:
        bundle = self.get(record.case_id)
        self.save(bundle.model_copy(update={"decision": record}))
