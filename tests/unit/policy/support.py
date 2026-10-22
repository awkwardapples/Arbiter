"""Shared fixtures for policy acceptance tests. No engine imports."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.schemas.common import Provenance
from app.schemas.decision import (
    ConfidenceBreakdown,
    PolicyInputs,
    PrecedentCandidate,
    TierProfile,
)
from app.schemas.evidence import Contradiction, Fact, GuardFlag

AS_OF = date(2026, 10, 22)
ROOT_SIGNALS = {
    "coverage": 1.0,
    "grounding": 1.0,
    "source_health": 1.0,
    "contradiction_free": 1.0,
    "precedent_alignment": 1.0,
}


def provenance(key: str, *, kind: str = "system_of_record") -> Provenance:
    return Provenance(
        kind=kind,  # type: ignore[arg-type]
        system="clm",
        query_id="Q_TEST",
        record_key="record=1",
        field=key,
        backend="duckdb",
    )


def make_fact(
    key: str,
    value: Any,
    state: str = "TRUE",
    *,
    fact_id: str | None = None,
    control_id: str = "C00",
    claim_ids: list[str] | None = None,
    kind: str = "system_of_record",
) -> Fact:
    return Fact(
        fact_id=fact_id or f"F-{key}",
        control_id=control_id,
        key=key,
        value=value,
        state=state,  # type: ignore[arg-type]
        provenance=[provenance(key, kind=kind)],
        derived_from_claims=claim_ids or [],
    )


def fact_map(facts: list[Fact]) -> dict[str, Fact]:
    return {fact.key: fact for fact in facts}


# Value, state. Omitted keys are absent.
TRUE_FACTS: dict[str, tuple[Any, str]] = {
    "vendor.data_categories": (["personal"], "TRUE"),
    "mfa.admin_enforced": (True, "TRUE"),
    "mfa.remote_enforced": (True, "TRUE"),
    "creds.vaulted": (True, "TRUE"),
    "creds.rotation_days": (90, "TRUE"),
    "access.review_interval_days": (90, "TRUE"),
    "crypto.at_rest": (True, "TRUE"),
    "crypto.in_transit_tls12": (True, "TRUE"),
    "assurance.soc2_type2_current": (True, "TRUE"),
    "assurance.iso27001_current": (False, "FALSE"),
    "incidents.material_unremediated_24m": (0, "TRUE"),
    "breach.notify_hours": (72, "TRUE"),
    "dpa.signed": (True, "TRUE"),
    "residency.regions": (["UK"], "TRUE"),
    "subprocessors.disclosed": (True, "TRUE"),
    "sanctions.watchlist_matches": (0, "TRUE"),
    "vuln.kev_matches": (0, "TRUE"),
}


def facts_from(spec: dict[str, tuple[Any, str] | None]) -> list[Fact]:
    """Build facts. A None value removes the key from the all-true base."""
    merged: dict[str, tuple[Any, str] | None] = dict(TRUE_FACTS)
    merged.update(spec)
    built: list[Fact] = []
    for key, item in merged.items():
        if item is None:
            continue
        value, state = item
        built.append(make_fact(key, value, state))
    return built


def profile(
    *,
    categories: list[str] | None = None,
    criticality: str = "low",
    spend: float = 20_000.0,
    contract_status: str = "signed",
) -> TierProfile:
    return TierProfile(
        data_categories=categories if categories is not None else ["personal"],
        criticality=criticality,  # type: ignore[arg-type]
        annual_spend_gbp=spend,
        contract_status=contract_status,
    )


def confidence(value: float) -> ConfidenceBreakdown:
    return ConfidenceBreakdown(value=value, gate=0.0, abstained=False, signals=dict(ROOT_SIGNALS))


def policy_inputs(
    facts: list[Fact],
    *,
    tier_profile: TierProfile | None = None,
    confidence_value: float = 0.95,
    contradictions: list[Contradiction] | None = None,
    guard_flags: list[GuardFlag] | None = None,
    precedents: list[PrecedentCandidate] | None = None,
    as_of: date = AS_OF,
) -> PolicyInputs:
    return PolicyInputs(
        case_id="case-test",
        run_id="run-test",
        as_of=as_of,
        profile=tier_profile or profile(),
        facts=facts,
        contradictions=contradictions or [],
        guard_flags=guard_flags or [],
        precedents=precedents or [],
        confidence=confidence(confidence_value),
    )


def contradiction(
    key: str,
    *,
    severity: str = "material",
    resolved: bool = False,
    control_id: str = "C09",
    claim_id: str = "CL-1",
) -> Contradiction:
    return Contradiction(
        key=key,
        control_id=control_id,
        claim_id=claim_id,
        claim_value="claim",
        sor_value="sor",
        sor_provenance=provenance(key),
        severity=severity,  # type: ignore[arg-type]
        resolved=resolved,
    )


def block_flag() -> GuardFlag:
    return GuardFlag(kind="injection", score=0.99, level="block", segment_id="seg-1")


def precedent(**overrides: Any) -> PrecedentCandidate:
    base: dict[str, Any] = {
        "precedent_id": "P-0001",
        "hmem_id": "mem-1",
        "control_id": "C05",
        "mitigation": "assurance.bridge_letter_current",
        "reviewer_role": "tprm_lead",
        "decision": "APPROVE_WITH_CONDITIONS",
        "created_as_of": AS_OF - timedelta(days=100),
        "tier": "T2",
        "hmem_confidence": 0.70,
        "relevance": 0.35,
    }
    base.update(overrides)
    return PrecedentCandidate(**base)


def c05_false_facts() -> dict[str, tuple[Any, str] | None]:
    """SOC 2 and ISO both known-false, bridge letter current."""
    return {
        "assurance.soc2_type2_current": (False, "FALSE"),
        "assurance.iso27001_current": (False, "FALSE"),
        "assurance.bridge_letter_current": (True, "TRUE"),
    }
