"""P14-B test support: a fake API client backed by responses recorded from the P14-A API."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from streamlit.testing.v1 import AppTest
from streamlit.testing.v1.element_tree import Block

from tests.unit.ui.conftest import FIXTURES, FakeArbiterClient

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "ui" / "app.py"
FAKE_CREDENTIAL = "example-credential-must-never-render"


def load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def live_trace() -> list[dict[str, Any]]:
    """A live-shaped trace: two model calls served by Nemotron through Nightshift (test double)."""
    base = copy.deepcopy(load("p14a_trace_escalate.json")[0])
    events = []
    for route, served, receipt in (
        ("fast", "nvidia/nemotron-3.5-lightning-30b-a3b", "rcpt-test-0001"),
        ("deep", "nvidia/nemotron-3-super-120b-a12b", "rcpt-test-0002"),
    ):
        event = copy.deepcopy(base)
        event.update(
            {
                "agent_name": "ReporterAgent",
                "action": "model_call",
                "provider": "meterless",
                "route": route,
                "model": served,
                "provider_meta": {
                    "requested_model": f"meterless/{route}",
                    "provider_model": served,
                    "receipt_id": receipt,
                },
            }
        )
        events.append(event)
    return events


def live_health() -> dict[str, Any]:
    health = copy.deepcopy(load("p14a_health_offline.json"))
    health["mode"]["llm"] = "meterless"
    health["provider"] = {
        "provider_resolved": "meterless",
        "llm_provider_setting": "meterless",
        "reason": "LLM_PROVIDER=meterless",
        "meterless": {
            "status": "online",
            "base_url": "http://127.0.0.1:8088/v1",
            "models_seen": ["meterless/fast", "meterless/deep"],
            "fast_model": "meterless/fast",
            "deep_model": "meterless/deep",
            "detail": "ok",
            "token": FAKE_CREDENTIAL,
        },
        "api_key": FAKE_CREDENTIAL,
    }
    return health


class P14Client(FakeArbiterClient):
    """Serves the recorded P14-A responses. `kind` is `escalate` (CASE-0007) or `request_info` (CASE-0022)."""

    def __init__(self, kind: str = "escalate", *, pending: bool = False, live: bool = False) -> None:
        super().__init__()
        self.case_detail = copy.deepcopy(load(f"p14a_case_{kind}.json"))
        self.trace = live_trace() if live else load("p14a_trace_escalate.json")
        self.queue = load("p14a_queue.json")
        self.health_data = live_health() if live else load("p14a_health_offline.json")
        self.question_items = load("p14b_questions.json")
        self.dossier_calls: list[tuple[str, str]] = []
        self.approvals: list[tuple[str, Any]] = []
        self.runs: list[Any] = []
        if pending:
            contract = self.case_detail["contracts"][0]
            contract["state"] = "pending_approval"
            contract["risk"]["approvals_required"] = ["tprm_lead"]

    def questions(self) -> list[dict[str, Any]]:
        return self.question_items

    def dossier(self, case_id: str, fmt: str = "html") -> str:
        self.dossier_calls.append((case_id, fmt))
        return f"<html>dossier {case_id}</html>" if fmt == "html" else f"# Dossier {case_id}"

    def run(self, case: Any, *, options: Any = None) -> dict[str, Any]:
        self.runs.append(case)
        self.run_calls += 1
        return load("p14a_run_escalate.json")

    def approve_contract(self, contract_id: str, body: Any) -> dict[str, Any]:
        self.approvals.append((contract_id, body))
        return {"contract_id": contract_id, "state": "executed", "executed": True}


def open_app(client: P14Client, page_file: str | None = None, *, case_id: str | None = None) -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=30)
    at.session_state["api_client"] = client
    at.run()
    if page_file and page_file != "pages/new_assessment.py":
        at.switch_page(page_file).run()
    if case_id:
        at.query_params["case_id"] = case_id
        at.run()
    return at


def _walk(block: Any, out: list[str], skip_technical: bool) -> None:
    for child in block.children.values():
        if isinstance(child, Block):
            label = str(getattr(child, "label", "") or "")
            if skip_technical and child.type == "expander" and label.lower().startswith("technical details"):
                continue
            out.append(label)
            _walk(child, out, skip_technical)
            continue
        for attr in ("value", "label", "body", "help"):
            value = getattr(child, attr, None)
            if value is None:
                continue
            if hasattr(value, "to_string"):
                value = value.to_string()
            if isinstance(value, (str, int, float)):
                out.append(str(value))
            elif isinstance(value, (list, tuple)):
                out.extend(str(item) for item in value)


def visible_text(at: AppTest, *, skip_technical: bool = True, sidebar: bool = False) -> str:
    """All text a reader sees on the page, excluding `Technical details` expanders."""
    out: list[str] = []
    _walk(at.sidebar if sidebar else at.main, out, skip_technical)
    return "\n".join(out)
