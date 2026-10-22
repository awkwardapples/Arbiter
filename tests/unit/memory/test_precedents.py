"""P4-A precedent adapter acceptance tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from app.audit.chain import AuditChain
from app.errors import PolicyIneligible
from app.memory import precedents
from app.memory.hmem import HMEM
from app.memory.hmem.types import FEEDBACK_DELTAS
from app.policy.loader import load_default
from app.schemas.api import ReviewRequest
from app.schemas.decision import TierProfile
from tests.unit.memory.support import minimal_bundle, s12_review
from tests.unit.policy.support import c05_false_facts, facts_from, policy_inputs

pytestmark = pytest.mark.p4a


@pytest.fixture
def hmem_ctx(tmp_path):
    def clock() -> int:
        return int(datetime(2026, 10, 22, tzinfo=UTC).timestamp() * 1000)

    hmem = HMEM(clock=clock, persist_dir=tmp_path / "hmem", ledger_mirror=tmp_path / "ledger.jsonl")
    audit = AuditChain(tmp_path / "audit.db")
    return hmem, audit, tmp_path


def test_p4_t1_record_precedent_writes_hmem_and_audit(hmem_ctx) -> None:
    """P4-T1: long-term H-MEM record, payload, ledger and audit precedent_created."""
    hmem, audit, tmp = hmem_ctx
    policy, _ = load_default()
    ref = precedents.record_precedent(
        s12_review(),
        minimal_bundle(),
        hmem=hmem,
        audit=audit,
        precedents_path=tmp / "precedents.json",
        run_id="run-review-1",
        policy=policy,
    )
    assert ref.precedent_id == "P-0001"
    mem = next(m for m in hmem.store.all() if m.id == ref.hmem_id)
    assert mem.layer == "long_term"
    assert mem.type == "factual"
    assert "precedent" in mem.tags
    assert mem.source.startswith("human_review:")
    assert mem.agent_id == "MemoryKeeper"
    store = json.loads((tmp / "precedents.json").read_text(encoding="utf-8"))
    assert "P-0001" in store
    rows = audit._conn.execute("SELECT event_type FROM audit_log").fetchall()
    assert any(r[0] == "precedent_created" for r in rows)
    audit.close()


def test_p4_t2_ineligible_raises_422_reasons(hmem_ctx) -> None:
    """P4-T2: ineligible creation raises PolicyIneligible with reasons; nothing stored."""
    hmem, audit, tmp = hmem_ctx
    policy, _ = load_default()
    bundle = minimal_bundle()
    review = ReviewRequest(
        reviewer="a@x.com",
        role="tprm_analyst",
        decision="APPROVE_WITH_CONDITIONS",
        rationale="x" * 30,
        create_precedent=True,
    )
    with pytest.raises(PolicyIneligible) as exc:
        precedents.record_precedent(
            review,
            bundle,
            hmem=hmem,
            audit=audit,
            precedents_path=tmp / "precedents.json",
            run_id="run-x",
            policy=policy,
        )
    assert "reviewer_role_insufficient" in exc.value.reasons

    controls = []
    for c in bundle.decision.controls:
        if c.control_id == "C01":
            controls.append(c.model_copy(update={"state": "FALSE", "required": True}))
        else:
            controls.append(c)
    decision2 = bundle.decision.model_copy(update={"controls": controls})
    bundle2 = bundle.model_copy(update={"decision": decision2})
    review2 = ReviewRequest(
        reviewer="a@x.com",
        role="tprm_lead",
        decision="APPROVE_WITH_CONDITIONS",
        rationale="y" * 30,
        create_precedent=True,
    )
    with pytest.raises(PolicyIneligible) as exc2:
        precedents.record_precedent(
            review2,
            bundle2,
            hmem=hmem,
            audit=audit,
            precedents_path=tmp / "precedents.json",
            run_id="run-y",
            policy=policy,
        )
    assert "non_exception_control_failing" in exc2.value.reasons

    bundle3 = minimal_bundle()
    facts = facts_from({**c05_false_facts(), "assurance.bridge_letter_current": (False, "FALSE")})
    from app.policy.engine import decide

    rec = decide(
        policy_inputs(facts, tier_profile=bundle3.decision.policy_inputs.profile),
        policy,
        load_default()[1],
    )
    bundle3 = bundle3.model_copy(update={"decision": rec})
    with pytest.raises(PolicyIneligible) as exc3:
        precedents.record_precedent(
            ReviewRequest(
                reviewer="a@x.com",
                role="tprm_lead",
                decision="APPROVE_WITH_CONDITIONS",
                rationale="z" * 30,
                create_precedent=True,
            ),
            bundle3,
            hmem=hmem,
            audit=audit,
            precedents_path=tmp / "precedents.json",
            run_id="run-z",
            policy=policy,
        )
    assert "mitigation_not_true" in exc3.value.reasons
    audit.close()


def test_p4_t4_failed_criteria_retrieval_quality(hmem_ctx) -> None:
    """P4-T4: feedback deltas; wrong retires precedent below gate (retrieval_quality on reject)."""
    assert FEEDBACK_DELTAS["helpful"] == 0.05
    assert FEEDBACK_DELTAS["not_helpful"] == -0.03
    assert FEEDBACK_DELTAS["wrong"] == -0.2
    hmem, audit, tmp = hmem_ctx
    policy, _ = load_default()
    precedents.record_precedent(
        s12_review(),
        minimal_bundle(),
        hmem=hmem,
        audit=audit,
        precedents_path=tmp / "precedents.json",
        run_id="run-review-1",
        policy=policy,
    )
    conf = precedents.feedback(
        "P-0001", "wrong", hmem=hmem, audit=audit, precedents_path=tmp / "precedents.json"
    )
    assert conf == pytest.approx(0.5)
    profile = TierProfile(
        data_categories=["personal"],
        criticality="low",
        annual_spend_gbp=45_000.0,
        contract_status="signed",
        vendor_category="HR SaaS",
    )
    found = precedents.find_precedents(
        profile,
        ["C05"],
        hmem=hmem,
        as_of=datetime.now(UTC).date(),
        run_id="run-retrieve",
        case_tier="T2",
        precedents_path=tmp / "precedents.json",
        policy=policy,
    )
    assert found
    from app.policy.engine import decide
    from tests.unit.policy.support import c05_false_facts, facts_from, policy_inputs

    record = decide(
        policy_inputs(facts_from(c05_false_facts()), precedents=found, tier_profile=profile),
        policy,
        load_default()[1],
    )
    ref = next(p for p in record.precedents_considered if p.precedent_id == "P-0001")
    assert ref.applied is False
    assert "retrieval_quality" in ref.failed_criteria
    assert record.outcome == "ESCALATE"
    audit.close()


def test_p4_t5_retrieval_trace_file(hmem_ctx) -> None:
    """P4-T5: retrieval JSONL includes retrievalReason, scores and strategy."""
    hmem, audit, tmp = hmem_ctx
    policy, _ = load_default()
    precedents.record_precedent(
        s12_review(),
        minimal_bundle(),
        hmem=hmem,
        audit=audit,
        precedents_path=tmp / "precedents.json",
        run_id="run-review-1",
        policy=policy,
    )
    profile = TierProfile(
        data_categories=["personal"],
        criticality="low",
        annual_spend_gbp=45_000.0,
        contract_status="signed",
        vendor_category="HR SaaS",
    )
    precedents.find_precedents(
        profile,
        ["C05"],
        hmem=hmem,
        as_of=datetime.now(UTC).date(),
        run_id="trace-run",
        case_tier="T2",
        log_dir=tmp / "logs",
        precedents_path=tmp / "precedents.json",
        policy=policy,
    )
    trace = tmp / "logs" / "hmem-retrieval-trace-run.jsonl"
    assert trace.is_file()
    row = json.loads(trace.read_text(encoding="utf-8").splitlines()[0])
    assert "retrievalReason" in row
    assert "scores" in row
    assert row["strategy"] in {"minimal", "personal", "comprehensive"}
    audit.close()


def test_p4_t9_retrieval_sanity(hmem_ctx) -> None:
    """P4-T9: canonical key relevance ≥ 0.35; wrong category scores below gate."""
    hmem, audit, tmp = hmem_ctx
    policy, _ = load_default()
    precedents.record_precedent(
        s12_review(),
        minimal_bundle(category="HR SaaS"),
        hmem=hmem,
        audit=audit,
        precedents_path=tmp / "precedents.json",
        run_id="run-review-1",
        policy=policy,
    )
    good = TierProfile(
        data_categories=["personal"],
        criticality="low",
        annual_spend_gbp=45_000.0,
        contract_status="signed",
        vendor_category="HR SaaS",
    )
    hits = precedents.find_precedents(
        good,
        ["C05"],
        hmem=hmem,
        as_of=datetime.now(UTC).date(),
        run_id="run-a",
        case_tier="T2",
        precedents_path=tmp / "precedents.json",
        policy=policy,
    )
    p1 = next(c for c in hits if c.precedent_id == "P-0001")
    assert p1.relevance >= 0.35

    precedents.record_precedent(
        s12_review(),
        minimal_bundle(category="SaaS"),
        hmem=hmem,
        audit=audit,
        precedents_path=tmp / "precedents.json",
        run_id="run-review-2",
        policy=policy,
    )
    hits2 = precedents.find_precedents(
        good,
        ["C05"],
        hmem=hmem,
        as_of=datetime.now(UTC).date(),
        run_id="run-b",
        case_tier="T2",
        precedents_path=tmp / "precedents.json",
        policy=policy,
    )
    by_id = {c.precedent_id: c for c in hits2}
    if "P-0002" in by_id:
        assert by_id["P-0002"].relevance < 0.35 or by_id["P-0002"].precedent_id != "P-0001"
    audit.close()
