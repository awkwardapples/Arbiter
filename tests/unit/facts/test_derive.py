"""P3-T4: fact derivation per 02 §4: SoR precedence, contradictions, DQ downgrade, contract-stage path."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

import pytest

from app.data.backend import QueryResult
from app.facts import derive
from app.policy.engine import decide
from app.policy.loader import load_default
from app.schemas.case import CaseInput
from app.schemas.common import Provenance
from app.schemas.decision import ConfidenceBreakdown, PolicyInputs, TierProfile
from app.schemas.evidence import Claim, DQFlag, Fact
from app.state import new_state

pytestmark = pytest.mark.p3

AS_OF = date(2026, 10, 26)
PROFILE = {
    "vendor_id": "VND-0900",
    "legal_name": "Test Vendor Ltd",
    "trading_name": "Test Vendor",
    "category": "SaaS",
    "requested_service": "x",
    "business_owner": "x",
    "annual_spend_gbp": 45000,
    "criticality": "low",
    "data_categories": "personal",
    "processing_countries": "GB",
    "clm_supplier_ref": "SUP-1",
    "onboarding_status": "in_review",
    "requested_at": "2026-09-26",
}
CONTRACT = {
    "vendor_id": "VND-0900",
    "contract_id": "CTR-1",
    "supplier_ref": "SUP-1",
    "status": "signed",
    "dpa_signed": True,
    "dpa_signed_date": "2026-03-01",
    "hosting_region_clause": "EU",
    "transfer_mechanism": "SCCs",
    "breach_notification_hours": 72,
    "subprocessor_list_attached": True,
    "renewal_date": "2027-05-14",
}
INCIDENT = {
    "incident_number": "INC1",
    "opened_at": "2026-06-28",
    "vendor_name_raw": "TEST VENDOR LTD",
    "severity": "P1",
    "category": "third_party_breach",
    "root_cause_tag": "missing_mfa",
    "status": "open",
    "rca_completed": False,
    "closed_at": None,
}

_n = 0


def _claim(
    key: str, value: Any, control: str, qid: str, *, state: str = "TRUE", grounded: bool = True
) -> Claim:
    global _n
    _n += 1
    return Claim(
        claim_id=f"CL-{_n}",
        control_id=control,
        key=key,
        asserted_value=value,
        state=state,  # type: ignore[arg-type]
        provenance=Provenance(kind="vendor_answer", system="trust_portal", quote="q", answer_ref=qid),
        extractor="deterministic:v1",
        grounded=grounded,
    )


def _result(qid: str, rows: list[dict[str, Any]]) -> QueryResult:
    return QueryResult(
        query_id=qid, rows=rows, columns=list(rows[0]) if rows else [], backend="duckdb", latency_ms=1
    )


def _state(
    *,
    claims: tuple[Claim, ...] = (),
    results: dict[str, list[dict[str, Any]]] | None = None,
    dq: tuple[DQFlag, ...] = (),
) -> Any:
    st = new_state(
        CaseInput(vendor_id="VND-0900"), run_id="r", as_of=AS_OF, mode={}, budget_deadline=float("inf")
    )
    st.profile = dict(PROFILE)
    for qid, rows in (results or {}).items():
        st.executed_queries[qid] = _result(qid, rows)
        st.query_counts[qid] = 1
    st.claims = list(claims)
    st.dq_flags = list(dq)
    return st


def _facts(st: Any) -> tuple[dict[str, Fact], list[Any]]:
    policy, _ = load_default()
    facts, contradictions = derive(st, policy)
    return {f.key: f for f in facts}, contradictions


def test_p3_t4_sor_beats_claim_and_material_residency_contradiction() -> None:
    claim = _claim("residency.regions_claimed", ["EU"], "C09", "Q10")
    contract = {**CONTRACT, "hosting_region_clause": "US", "transfer_mechanism": "NONE"}
    facts, contradictions = _facts(_state(claims=(claim,), results={"Q_VENDOR_CONTRACT": [contract]}))
    regions = facts["residency.regions"]
    assert regions.value == ["US"]
    assert regions.provenance[0].kind == "system_of_record"
    assert regions.provenance[0].query_id == "Q_VENDOR_CONTRACT"
    assert regions.provenance[0].record_key == "contract_id=CTR-1"
    assert facts["transfer.mechanism"].value == "NONE"
    [c] = [c for c in contradictions if c.key == "residency.regions"]
    assert (c.control_id, c.claim_id, c.severity, c.resolved) == ("C09", claim.claim_id, "material", False)


def test_p3_t4_claim_zero_but_itsm_positive_is_material() -> None:
    claim = _claim("incidents.vendor_reported_24m", 0, "C06", "Q08")
    outage = {**INCIDENT, "incident_number": "INC2", "category": "outage"}
    facts, contradictions = _facts(
        _state(claims=(claim,), results={"Q_VENDOR_INCIDENTS": [INCIDENT, outage]})
    )
    assert facts["incidents.itsm_vendor_related_24m"].value == 1
    assert facts["incidents.material_unremediated_24m"].value == 1
    [c] = [c for c in contradictions if c.key == "incidents.vendor_reported_24m"]
    assert c.severity == "material" and c.control_id == "C06"


def test_p3_t4_outage_only_does_not_contradict() -> None:
    claim = _claim("incidents.vendor_reported_24m", 0, "C06", "Q08")
    outage = {**INCIDENT, "category": "outage"}
    facts, contradictions = _facts(_state(claims=(claim,), results={"Q_VENDOR_INCIDENTS": [outage]}))
    assert facts["incidents.material_unremediated_24m"].value == 0
    assert not contradictions


def test_p3_t4_breach_hours_mismatch_is_minor() -> None:
    claim = _claim("breach.notify_hours_claimed", 48, "C07", "Q09")
    facts, contradictions = _facts(_state(claims=(claim,), results={"Q_VENDOR_CONTRACT": [CONTRACT]}))
    assert facts["breach.notify_hours"].value == 72
    [c] = [c for c in contradictions if c.key == "breach.notify_hours"]
    assert c.severity == "minor"


def test_p3_t4_dq_flag_downgrades_to_unknown() -> None:
    contract = {**CONTRACT, "dpa_signed_date": None}
    flag = DQFlag(rule="dq_contract_dpa_date", table="contract", record_key="contract_id=CTR-1")
    facts, _ = _facts(_state(results={"Q_VENDOR_CONTRACT": [contract]}, dq=(flag,)))
    assert facts["dpa.signed"].state == "UNKNOWN"
    assert "dq_contract_dpa_date" in facts["dpa.signed"].dq_flags
    assert facts["subprocessors.disclosed"].state == "TRUE"


def test_p3_t4_no_contract_uses_claims_and_contract_stage_path() -> None:
    claims = (
        _claim("residency.regions_claimed", ["EU"], "C09", "Q10"),
        _claim("dpa.vendor_commits", True, "C08", "Q15"),
        _claim("breach.notify_hours_claimed", 72, "C07", "Q09"),
    )
    st = _state(claims=claims, results={"Q_VENDOR_CONTRACT": []})
    facts, contradictions = _facts(st)
    assert facts["contract.status"].value == "none"
    assert facts["residency.regions"].value == ["EU"]
    assert facts["residency.regions"].provenance[0].kind == "vendor_answer"
    assert facts["dpa.signed"].state == "UNKNOWN"
    assert facts["breach.notify_hours"].state == "UNKNOWN"
    assert not contradictions

    policy, calibration = load_default()
    record = decide(
        PolicyInputs(
            case_id="c",
            run_id="r",
            as_of=AS_OF,
            profile=TierProfile(
                data_categories=["personal"],
                criticality="low",
                annual_spend_gbp=45000,
                contract_status="none",
            ),
            facts=list(facts.values()),
            contradictions=[],
            guard_flags=[],
            confidence=ConfidenceBreakdown(value=1.0, gate=0.0, abstained=False, signals={}),
        ),
        policy,
        calibration,
    )
    c08 = next(c for c in record.controls if c.control_id == "C08")
    assert c08.state == "TRUE" and c08.conditional


def test_p3_t4_submission_patch_sla_beats_claim() -> None:
    claim = _claim("vuln.patch_sla_critical_days", 30, "C12", "Q13")
    submission = {
        "submission_id": "S",
        "vendor_id": "VND-0900",
        "submitted_at": "2026-10-16",
        "patch_sla_critical_days": 14,
        "contact_role": "security",
    }
    facts, _ = _facts(_state(claims=(claim,), results={"Q_SUBMISSION": [submission]}))
    assert facts["vuln.patch_sla_critical_days"].value == 14
    assert facts["vuln.patch_sla_critical_days"].provenance[0].kind == "system_of_record"


def test_p3_t4_kev_matches_depend_on_components_and_query() -> None:
    component = {
        "component_id": "CMP-1",
        "vendor_id": "VND-0900",
        "vendor_project": "Fortinet",
        "product": "FortiOS",
        "version": "7",
    }
    none, _ = _facts(_state(results={"Q_VENDOR_COMPONENTS": []}))
    assert none["vuln.components_declared"].value == 0
    assert none["vuln.kev_matches"].value == 0 and none["vuln.kev_matches"].state == "TRUE"

    pending, _ = _facts(_state(results={"Q_VENDOR_COMPONENTS": [component]}))
    assert pending["vuln.kev_matches"].state == "UNKNOWN"

    kev_rows = [
        {
            "component_id": "CMP-1",
            "vendor_id": "VND-0900",
            "cve_id": cve,
            "vendor_project": "Fortinet",
            "product": "FortiOS",
            "vulnerability_name": "v",
            "date_added": "2024-01-01",
            "due_date": "2024-02-01",
            "ransomware_use": "Unknown",
        }
        for cve in ("CVE-1", "CVE-2", "CVE-2")
    ]
    matched, _ = _facts(_state(results={"Q_VENDOR_COMPONENTS": [component], "Q_COMPONENT_KEV": kev_rows}))
    assert matched["vuln.kev_matches"].value == 2
    assert matched["vuln.kev_matches"].provenance[0].kind == "public_feed"


def test_p3_t4_ungrounded_claim_gives_unknown() -> None:
    claims = (
        _claim("mfa.admin_enforced", True, "C01", "Q01", grounded=False),
        _claim("mfa.remote_enforced", True, "C01", "Q02"),
    )
    facts, _ = _facts(_state(claims=claims))
    assert facts["mfa.admin_enforced"].state == "UNKNOWN"
    assert facts["mfa.remote_enforced"].state == "TRUE"
    assert facts["mfa.remote_enforced"].derived_from_claims == [claims[1].claim_id]


def test_p3_t4_watchlist_exact_matches_from_screen() -> None:
    entry = {
        "entry_id": "WL-1",
        "entity_name": "test vendor ltd",
        "list_name": "L",
        "country": "GB",
        "added_on": "2025-01-01",
        "reason": "r",
    }
    facts, _ = _facts(_state(results={"Q_WATCHLIST_SCREEN": [entry]}))
    assert facts["sanctions.watchlist_matches"].value == 1


def test_p3_t4_fact_and_evidence_ids() -> None:
    claim = _claim("residency.regions_claimed", ["EU"], "C09", "Q10")
    st = _state(claims=(claim,), results={"Q_VENDOR_CONTRACT": [CONTRACT], "Q_VENDOR_COMPONENTS": []})
    facts, _ = _facts(st)
    for f in facts.values():
        assert re.fullmatch(r"F-[A-Z0-9]+-\d+", f.fact_id), f.fact_id
        assert f.provenance
    assert facts["residency.regions"].fact_id.startswith("F-C09-")
    assert facts["vendor.data_categories"].value == ["personal"]
