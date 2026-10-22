from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.audit.chain import AuditChain
from app.memory import precedents
from app.memory.keeper import shared_hmem
from app.orchestrator import RunOptions, run
from app.schemas.api import ReviewRequest
from app.schemas.case import CaseInput
from app.store import Store


def _reset_var(*, yes: bool) -> None:
    if not yes:
        ans = input("Reset var/hmem, precedents and cases? [y/N] ").strip().lower()
        if ans not in {"y", "yes"}:
            print("Aborted.", file=sys.stderr)
            sys.exit(1)
    root = Path("var")
    for name in ("hmem", "cases", "contracts", "reviews", "outbox"):
        path = root / name
        if path.is_dir():
            shutil.rmtree(path)
    for file in ("precedents.json", "audit.db"):
        p = root / file
        if p.is_file():
            p.unlink()
    logs = Path("logs")
    if logs.is_dir():
        for p in logs.glob("hmem-*"):
            p.unlink(missing_ok=True)


def _review(case_id: str, body: ReviewRequest) -> dict:
    from fastapi.testclient import TestClient

    from app.api.main import app

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(f"/cases/{case_id}/review", json=body.model_dump(mode="json"))
    if resp.status_code >= 400:
        raise RuntimeError(f"review failed {resp.status_code}: {resp.text}")
    return resp.json()


def _run_vendor(vendor_id: str, *, live: bool) -> tuple[str, str]:
    options = RunOptions(sample_mode=not live, llm="auto" if live else "offline")
    resp = run(CaseInput(vendor_id=vendor_id), options=options)
    if resp.output is None:
        raise RuntimeError(f"run failed for {vendor_id}")
    return resp.output.case_id, resp.output.decision


def cmd_demo_session(args: argparse.Namespace) -> int:
    if args.reset:
        _reset_var(yes=args.yes)
    rows: list[tuple[int, str, str, bool]] = []

    # Step 1
    case_id, outcome = _run_vendor("VND-0011", live=args.live)
    ok = outcome == "ESCALATE"
    rows.append((1, "run VND-0011", outcome, ok))

    # Step 2
    review_body = ReviewRequest(
        reviewer="lead.reviewer@example.com",
        role="tprm_lead",
        decision="APPROVE_WITH_CONDITIONS",
        rationale="Bridge letter accepted for SOC gap; conditions documented for audit.",
        mitigations=["bridge_letter"],
        conditions=["annual_attestation"],
        create_precedent=True,
    )
    rev = _review(case_id, review_body)
    ok = rev.get("precedent") is not None
    rows.append((2, "review + precedent", str(rev.get("precedent", {}).get("precedent_id")), ok))

    # Step 3
    case12, outcome = _run_vendor("VND-0012", live=args.live)
    bundle = Store().get(case12)
    exc = bundle.decision.exceptions_applied
    ok = outcome == "APPROVE_WITH_CONDITIONS" and exc
    rows.append((3, "run VND-0012", f"{outcome} {exc}", ok))

    # Step 4
    _reset_var(yes=True)
    _, outcome = _run_vendor("VND-0012", live=args.live)
    ok = outcome == "ESCALATE"
    rows.append((4, "reset + VND-0012", outcome, ok))

    # Step 5 — rebuild precedent path with analyst (ineligible precedent)
    case_id, _ = _run_vendor("VND-0011", live=args.live)
    bad = ReviewRequest(
        reviewer="analyst@example.com",
        role="tprm_analyst",
        decision="APPROVE_WITH_CONDITIONS",
        rationale="Analyst attempt without lead authority on precedent.",
        mitigations=["bridge_letter"],
        create_precedent=True,
    )
    from fastapi.testclient import TestClient

    from app.api.main import app

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(f"/cases/{case_id}/review", json=bad.model_dump(mode="json"))
    ok = resp.status_code == 422
    _, outcome = _run_vendor("VND-0012", live=args.live)
    ok = ok and outcome == "ESCALATE"
    rows.append((5, "analyst precedent blocked", outcome, ok))

    # Step 6 — restore P-0001 path then wrong feedback
    _reset_var(yes=True)
    case_id, _ = _run_vendor("VND-0011", live=args.live)
    _review(case_id, review_body)
    precedents.feedback(
        "P-0001",
        "wrong",
        hmem=shared_hmem(Path("var"), lambda: datetime.now(UTC)),
        audit=AuditChain(Path("var/audit.db")),
        precedents_path=Path("var/precedents.json"),
        case_id=case_id,
    )
    _, outcome = _run_vendor("VND-0012", live=args.live)
    ok = outcome == "ESCALATE"
    rows.append((6, "wrong feedback + VND-0012", outcome, ok))

    print("| Step | Action | Result | OK |")
    print("|---|---|---|---|")
    for step, action, result, passed in rows:
        print(f"| {step} | {action} | {result} | {'yes' if passed else 'NO'} |")
    return 0 if all(r[3] for r in rows) else 1


def _case_for_vendor(vendor_id: str) -> str:
    for bundle in Store().list(order="recent"):
        if bundle.vendor_ref == vendor_id:
            return bundle.case_id
    raise RuntimeError(f"no case for {vendor_id}")


def cmd_review(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    body = ReviewRequest.model_validate(data.get("review", data))
    case_id = args.case if args.case.startswith("CASE-") else _case_for_vendor(args.case)
    out = _review(case_id, body)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    rev = sub.add_parser("review", help="Submit a human review for a case")
    rev.add_argument("case")
    rev.add_argument("--input", required=True)
    rev.set_defaults(_handler=cmd_review)

    demo = sub.add_parser("demo-session", help="Run a guided demo session")
    demo.add_argument("--live", action="store_true")
    demo.add_argument("--reset", action="store_true")
    demo.add_argument("--yes", action="store_true")
    demo.set_defaults(_handler=cmd_demo_session)
