"""Fixtures for P5-A UI tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ui.client import ArbiterAPIError

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "ui"
ROOT = Path(__file__).resolve().parents[3]


def _load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def published_eval() -> dict[str, Any]:
    """The /eval/latest payload built from the committed results, as the API builds it."""
    from app.api.routes_meta import _latest_summary

    live, live_markdown = _latest_summary(ROOT / "eval" / "results_live")
    offline, offline_markdown = _latest_summary(ROOT / "eval" / "results")
    return {
        "live": live,
        "offline": offline,
        "live_markdown": live_markdown,
        "offline_markdown": offline_markdown,
    }


class FakeArbiterClient:
    """In-memory API stand-in for Streamlit AppTest."""

    eval_latest_404: bool = False
    run_calls: int = 0

    def __init__(self) -> None:
        self.health_data = _load("health.json")
        self.queue = _load("queue.json")
        self.case_detail = _load("case_detail.json")
        self.vendors = _load("vendors.json")
        self.precedents = _load("precedents.json")
        self.trace = _load("example_2_trace.json")

    def health(self) -> dict[str, Any]:
        return self.health_data

    def list_vendors(self) -> list[dict[str, object]]:
        return self.vendors

    def run(self, case: Any, *, options: Any = None) -> dict[str, Any]:
        self.run_calls += 1
        raise AssertionError("run should not be called in this test")

    def list_cases(self) -> list[dict[str, Any]]:
        return self.queue

    def get_case(self, case_id: str) -> dict[str, Any]:
        return self.case_detail

    def get_trace(self, case_id: str) -> list[dict[str, Any]]:
        return self.trace

    def replay(self, case_id: str) -> dict[str, Any]:
        return {"match": True, "diff": [], "checks": {}}

    def submit_review(self, case_id: str, body: Any, *, dry_run: bool = False) -> dict[str, Any]:
        return {"eligible": True, "reasons": []}

    def list_precedents(self) -> list[dict[str, Any]]:
        return self.precedents

    def audit_verify(self) -> dict[str, Any]:
        return {"ok": True, "first_bad_seq": None}

    def approve_contract(self, contract_id: str, body: Any) -> dict[str, Any]:
        return {"contract_id": contract_id, "state": "executed", "executed": True}

    def questions(self) -> list[dict[str, Any]]:
        return _load("p14b_questions.json")

    def dossier(self, case_id: str, fmt: str = "html") -> str:
        return f"dossier {case_id} {fmt}"

    def eval_latest(self) -> dict[str, Any]:
        if self.eval_latest_404:
            raise ArbiterAPIError("Evaluation not published.", status_code=404)
        return published_eval()


@pytest.fixture
def fake_client() -> FakeArbiterClient:
    return FakeArbiterClient()
