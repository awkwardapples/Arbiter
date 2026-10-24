"""Case store: SQLite at `{root}/arbiter.db` (WAL), same public methods as the P3 JSON store."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.errors import NotFound
from app.schemas.case import CaseInput
from app.schemas.contract import ExecutionContract
from app.schemas.decision import DecisionRecord
from app.schemas.report import Report

_RISK_ORDER = {"DECLINE": 0, "ESCALATE": 1, "REQUEST_INFO": 2, "APPROVE_WITH_CONDITIONS": 3, "APPROVE": 4}


def _risk_key(bundle: CaseBundle) -> tuple[int, int, str]:
    decision = bundle.decision
    return (_RISK_ORDER[decision.outcome], -decision.residual_risk, bundle.case_id)


class CaseBundle(BaseModel):
    """One persisted case. Unknown keys are kept so a P3 field this model does not declare survives."""

    model_config = ConfigDict(extra="allow")

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


def _dump(model: BaseModel) -> str:
    return json.dumps(model.model_dump(mode="json"))


class Store:
    def __init__(self, root: Path | str = "var") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.root / "arbiter.db"), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create()
        self._import_json()

    def _create(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                vendor_ref TEXT NOT NULL,
                legal_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                outcome TEXT NOT NULL,
                tier TEXT NOT NULL,
                residual_risk INTEGER NOT NULL,
                decision_json TEXT NOT NULL,
                report_json TEXT NOT NULL,
                trace_path TEXT NOT NULL,
                mode_json TEXT NOT NULL,
                bundle_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS contracts (
                contract_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                parent_id TEXT,
                state TEXT NOT NULL,
                json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reviews (
                review_id INTEGER PRIMARY KEY,
                case_id TEXT NOT NULL,
                json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS workloads (
                case_id TEXT PRIMARY KEY,
                json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS human_decisions (
                id INTEGER PRIMARY KEY,
                case_id TEXT NOT NULL,
                json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS machine_decisions (
                case_id TEXT PRIMARY KEY,
                json TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def _import_json(self) -> None:
        if self._count("cases") == 0:
            folder = self.root / "cases"
            if folder.is_dir():
                for path in sorted(folder.glob("*.json")):
                    self.save(CaseBundle.model_validate_json(path.read_text(encoding="utf-8")))
        if self._count("contracts") == 0:
            folder = self.root / "contracts"
            if folder.is_dir():
                for path in sorted(folder.glob("*.json")):
                    self.put_contract(ExecutionContract.model_validate_json(path.read_text(encoding="utf-8")))
        if self._count("reviews") == 0:
            folder = self.root / "reviews"
            if folder.is_dir():
                for path in sorted(folder.glob("*.json")):
                    self.put_review(json.loads(path.read_text(encoding="utf-8")))

    def _count(self, table: str) -> int:
        row = self._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(row[0])

    def save(self, bundle: CaseBundle) -> None:
        data = bundle.model_dump(mode="json")
        decision = bundle.decision
        self._conn.execute(
            """
            INSERT INTO cases (
                case_id, run_id, vendor_ref, legal_name, created_at, status, outcome, tier,
                residual_risk, decision_json, report_json, trace_path, mode_json, bundle_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(case_id) DO UPDATE SET
                run_id = excluded.run_id,
                vendor_ref = excluded.vendor_ref,
                legal_name = excluded.legal_name,
                created_at = excluded.created_at,
                status = excluded.status,
                outcome = excluded.outcome,
                tier = excluded.tier,
                residual_risk = excluded.residual_risk,
                decision_json = excluded.decision_json,
                report_json = excluded.report_json,
                trace_path = excluded.trace_path,
                mode_json = excluded.mode_json,
                bundle_json = excluded.bundle_json
            """,
            (
                bundle.case_id,
                bundle.run_id,
                bundle.vendor_ref,
                bundle.legal_name,
                data["created_at"],
                bundle.status,
                decision.outcome,
                decision.tier,
                decision.residual_risk,
                json.dumps(data["decision"]),
                json.dumps(data["report"]),
                bundle.log_file,
                json.dumps(data["mode"]),
                json.dumps(data),
            ),
        )
        self._conn.commit()

    def get(self, case_id: str) -> CaseBundle:
        row = self._conn.execute("SELECT bundle_json FROM cases WHERE case_id = ?", (case_id,)).fetchone()
        if row is None:
            raise NotFound(f"case {case_id} not found")
        return CaseBundle.model_validate_json(row[0])

    def list(self, order: Literal["risk", "recent"] = "risk") -> list[CaseBundle]:
        rows = self._conn.execute("SELECT bundle_json FROM cases").fetchall()
        bundles = [CaseBundle.model_validate_json(row[0]) for row in rows]
        if order == "recent":
            return sorted(bundles, key=lambda bundle: bundle.created_at, reverse=True)
        return sorted(bundles, key=_risk_key)

    def save_workload(self, case_id: str, workload: BaseModel) -> None:
        """Keep the measured workload of a run so the case page can show it later."""
        self._conn.execute(
            "INSERT OR REPLACE INTO workloads (case_id, json) VALUES (?, ?)", (case_id, _dump(workload))
        )
        self._conn.commit()

    def workload_for(self, case_id: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT json FROM workloads WHERE case_id = ?", (case_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def put_contract(self, contract: ExecutionContract) -> None:
        self._conn.execute(
            """
            INSERT INTO contracts (contract_id, case_id, parent_id, state, json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(contract_id) DO UPDATE SET
                case_id = excluded.case_id,
                parent_id = excluded.parent_id,
                state = excluded.state,
                json = excluded.json
            """,
            (
                contract.contract_id,
                contract.case_id,
                contract.parent_id,
                contract.state,
                _dump(contract),
            ),
        )
        self._conn.commit()

    def get_contract(self, contract_id: str) -> ExecutionContract:
        row = self._conn.execute(
            "SELECT json FROM contracts WHERE contract_id = ?",
            (contract_id,),
        ).fetchone()
        if row is None:
            raise NotFound(f"contract {contract_id} not found")
        return ExecutionContract.model_validate_json(row[0])

    def contracts_for(self, case_id: str) -> list[ExecutionContract]:
        rows = self._conn.execute("SELECT json FROM contracts WHERE case_id = ?", (case_id,)).fetchall()
        found = [ExecutionContract.model_validate_json(row[0]) for row in rows]
        return sorted(found, key=lambda contract: (contract.issued_at, contract.contract_id))

    def put_review(self, review: BaseModel | dict[str, Any]) -> None:
        data = review.model_dump(mode="json") if isinstance(review, BaseModel) else dict(review)
        self._conn.execute(
            "INSERT INTO reviews (case_id, json) VALUES (?, ?)",
            (str(data["case_id"]), json.dumps(data)),
        )
        self._conn.commit()

    def reviews_for(self, case_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT json FROM reviews WHERE case_id = ? ORDER BY review_id",
            (case_id,),
        ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def put_machine_decision(self, record: DecisionRecord) -> None:
        """Keep the machine record a review replaces.

        The review route calls this only when the record it replaces is a machine one, so a second
        review keeps the first machine record, while a fresh run of the case followed by a review
        replaces it.
        """
        self._conn.execute(
            "INSERT OR REPLACE INTO machine_decisions (case_id, json) VALUES (?, ?)",
            (record.case_id, _dump(record)),
        )
        self._conn.commit()

    def machine_decision_for(self, case_id: str) -> DecisionRecord | None:
        row = self._conn.execute(
            "SELECT json FROM machine_decisions WHERE case_id = ?", (case_id,)
        ).fetchone()
        return DecisionRecord.model_validate_json(row[0]) if row else None

    def put_human_decision(self, record: DecisionRecord) -> None:
        self._conn.execute(
            "INSERT INTO human_decisions (case_id, json) VALUES (?, ?)",
            (record.case_id, _dump(record)),
        )
        self._conn.commit()
        bundle = self.get(record.case_id)
        self.save(bundle.model_copy(update={"decision": record}))
