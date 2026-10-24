"""Record the API payloads the P18-C console tests read (lane 18c).

Runs the real API in-process in sample mode (DuckDB mirror, offline fallback) in a temporary working
directory, assesses every file in input_examples/ (never expected.json), then records:

- p18c_queue.json            GET /cases
- p18c_case_pending.json     GET /cases/{id} for the first case with a contract in pending_approval
- p18c_approve_result.json   POST /contracts/{id}/approve on that contract
- p18c_case_approved.json    GET /cases/{id} afterwards (approvals, outbox state)
- p18c_case_contradiction.json  GET /cases/{id} for the first case whose brief has a claim and a record
- p18c_trace_contradiction.json GET /cases/{id}/trace for that case
- p18c_replay_match.json     POST /cases/{id}/replay on that case
- p18c_review_result.json    POST /cases/{id}/review by the TPRM lead
- p18c_replay_override.json  POST /cases/{id}/replay after the review (P19 human_override shape)

Usage: python scripts/record_p18c_fixtures.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "input_examples"
OUT = ROOT / "tests" / "fixtures" / "ui"
LEAD_RATIONALE = "Residency confirmed with the vendor's DPO in writing; hosting moves to the EU region."
APPROVER_RATIONALE = "Reviewed the decline memo; the hard gate failure is confirmed in the record."


def _write(name: str, payload: Any) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    (OUT / name).write_text(text, encoding="utf-8")
    print(f"wrote tests/fixtures/ui/{name}")


def _ok(response: Any) -> Any:
    if response.status_code >= 400:
        request = response.request
        raise SystemExit(f"{request.method} {request.url}: {response.status_code} {response.text}")
    return response.json()


def _has_pair(detail: dict[str, Any]) -> bool:
    brief = (detail.get("report") or {}).get("brief") or {}
    return any(point.get("claim") and point.get("record") for point in brief.get("why") or [])


def main() -> int:
    sys.path.insert(0, str(ROOT))
    os.environ.update({"SAMPLE_MODE": "true", "LLM_PROVIDER": "offline", "ARBITER_MEMORY": "off"})
    examples = sorted(p for p in EXAMPLES.glob("example_*.json"))
    with tempfile.TemporaryDirectory(prefix="p18c-") as tmp:
        os.chdir(tmp)
        from fastapi.testclient import TestClient

        from app.api.main import app
        from app.llm.resolve import reset_cache

        reset_cache()
        client = TestClient(app)
        for path in examples:
            _ok(client.post("/run", json=json.loads(path.read_text(encoding="utf-8"))))

        queue = _ok(client.get("/cases"))
        _write("p18c_queue.json", queue)
        details = {item["case_id"]: _ok(client.get(f"/cases/{item['case_id']}")) for item in queue}

        pending = next(
            (d for d in details.values() if any(c["state"] == "pending_approval" for c in d["contracts"])),
            None,
        )
        if pending is None:
            raise SystemExit("no case has a contract in pending_approval")
        _write("p18c_case_pending.json", pending)
        contract = next(c for c in pending["contracts"] if c["state"] == "pending_approval")
        role = str(contract["risk"]["approvals_required"][0]["role"])
        approval = {"by": "Dana Reviewer", "role": role, "decision": "approve"}
        approval["rationale"] = APPROVER_RATIONALE
        approved = client.post(f"/contracts/{contract['contract_id']}/approve", json=approval)
        _write("p18c_approve_result.json", _ok(approved))
        _write("p18c_case_approved.json", _ok(client.get(f"/cases/{pending['case_id']}")))

        pair = next((d for d in details.values() if _has_pair(d)), None)
        if pair is None:
            raise SystemExit("no case has a claim-versus-record brief point")
        case_id = pair["case_id"]
        _write("p18c_case_contradiction.json", pair)
        _write("p18c_trace_contradiction.json", _ok(client.get(f"/cases/{case_id}/trace")))
        _write("p18c_replay_match.json", _ok(client.post(f"/cases/{case_id}/replay")))
        review = {
            "reviewer": "Sam Lead",
            "role": "tprm_lead",
            "decision": "APPROVE_WITH_CONDITIONS",
            "rationale": LEAD_RATIONALE,
            "conditions": ["Hosting moves to the EU region within 30 days."],
        }
        _write("p18c_review_result.json", _ok(client.post(f"/cases/{case_id}/review", json=review)))
        _write("p18c_replay_override.json", _ok(client.post(f"/cases/{case_id}/replay")))
        os.chdir(ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
