"""P3-T10: integrity. Distinct records, a mutation flips the outcome, random inline input is decided."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import pytest

from app.data.factory import get_backend
from app.orchestrator import Deps, RunOptions, run
from app.schemas.api import RunResponse
from app.schemas.case import Answer, CaseInput, VendorSubmission
from app.store import Store
from tests.e2e.support import EXAMPLE_FILES, load_example, offline_env

pytestmark = pytest.mark.p3
__all__ = ["offline_env"]

QUESTIONS = {
    "Q01": "Is MFA enforced for all administrative and privileged accounts?",
    "Q02": "Is MFA enforced for all remote and employee access to systems processing our data?",
    "Q05": "Is customer data encrypted at rest? Which standard?",
    "Q06": "Is data encrypted in transit (TLS 1.2+)?",
    "Q08": "Have you had any security incidents affecting customer data in the last 24 months?",
    "Q10": "Where will our data be hosted and processed?",
    "Q15": "Will you sign our Data Processing Agreement?",
}
POOL = {
    "Q01": [
        "Yes, MFA is enforced for admins.",
        "Admin MFA is not enforced today.",
        "We follow best practice.",
    ],
    "Q02": ["Every remote login uses MFA.", "Remote MFA planned for Q1."],
    "Q05": ["Yes, data is encrypted at rest with AES-256.", "Customer data at rest is not encrypted."],
    "Q06": ["Yes, all traffic uses TLS 1.2 or higher.", "Connections are secured appropriately."],
    "Q08": ["No security incidents in the last 24 months.", "We had two security incidents last year."],
    "Q10": ["EU only.", "Hosting includes US regions."],
    "Q15": ["We will sign the customer DPA.", "We will not sign the proposed DPA."],
}


def test_p3_t10_distinct_records_and_outcomes(offline_env: Path) -> None:
    shas: list[str] = []
    outcomes: set[str] = set()
    for name in EXAMPLE_FILES:
        resp = run(load_example(name), options=RunOptions())
        bundle = Store().get(resp.output.case_id)
        shas.append(bundle.decision.record_sha256)
        outcomes.add(bundle.decision.outcome)
    assert len(set(shas)) == 6
    assert len(outcomes) >= 4


class RewriteQ01:
    name = "rewrite"

    def __init__(self, inner: Any) -> None:
        self.inner = inner

    def run(self, query_id: str, params: dict[str, object]) -> Any:
        result = self.inner.run(query_id, params)
        if query_id != "Q_SUBMISSION_ANSWERS":
            return result
        rows = [
            {**r, "answer_text": "We do not enforce MFA for admin roles."} if r["question_id"] == "Q01" else r
            for r in result.rows
        ]
        return result.model_copy(update={"rows": rows})


def test_p3_t10_q01_denial_flips_example_1(offline_env: Path) -> None:
    def factory(settings: Any, tracer: Any, submission: Any = None) -> Any:
        return RewriteQ01(get_backend(settings, tracer, submission))

    resp = run(load_example("example_1.json"), options=RunOptions(), deps=Deps(backend_factory=factory))
    bundle = Store().get(resp.output.case_id)
    assert bundle.decision.outcome == "ESCALATE"
    c01 = next(c for c in bundle.decision.controls if c.control_id == "C01")
    assert c01.state == "FALSE"


def test_p3_t10_random_inline_submission(offline_env: Path) -> None:
    rng = random.Random(3110)
    answers = [
        Answer(question_id=qid, question=QUESTIONS[qid], answer_text=rng.choice(options))
        for qid, options in POOL.items()
        if rng.random() < 0.85
    ]
    submission = VendorSubmission(
        legal_name=f"Random Vendor {rng.randint(100, 999)} Ltd",
        category="SaaS",
        requested_service="Random service",
        criticality=rng.choice(["low", "medium", "high"]),
        annual_spend_gbp=float(rng.choice([4000, 60000, 250000])),
        data_categories=rng.sample(["internal", "personal", "payment"], k=rng.randint(1, 2)),
        processing_countries=["GB"],
        answers=answers,
        patch_sla_critical_days=rng.choice([None, 7, 30]),
    )
    resp = run(CaseInput(submission=submission), options=RunOptions())
    RunResponse.model_validate(resp.model_dump(mode="json"))
    assert resp.status in {"success", "partial_success"}
    bundle = Store().get(resp.output.case_id)
    assert bundle.decision.outcome == resp.output.decision
    assert not any(r.startswith("SYSTEM_") for r in bundle.decision.escalation_reasons)
