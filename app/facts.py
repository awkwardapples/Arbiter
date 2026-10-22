"""Derive policy facts from executed queries and grounded claims (02 §4). Pure: no I/O, no model.

System-of-record values beat claims; a disagreement becomes a `Contradiction` and the SoR value stays.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from app.agents.catalogue import (
    INCIDENT_WINDOW_DAYS,
    QUERY_SYSTEM,
    QUESTION_KEYS,
    control_for_key,
    record_key,
)
from app.data.backend import QueryResult
from app.extract.documents import assurance_facts, mfa_corroboration
from app.policy.dsl import referenced_keys
from app.policy.loader import Policy
from app.schemas.common import Provenance, TriState
from app.schemas.decision import TierProfile
from app.schemas.evidence import Claim, Contradiction, Fact
from app.state import CaseState

MATERIAL_CATEGORIES = frozenset({"third_party_breach", "data_exposure"})
REGION_CLAUSE: dict[str, list[str]] = {
    "EU": ["EU"],
    "UK": ["UK"],
    "US": ["US"],
    "GLOBAL": ["US", "EU", "UK", "OTHER"],
}
NEAR_MATCH_RATIO = 0.92
# DQ rule -> fact keys it makes UNKNOWN on the flagged record.
DQ_AFFECTS: dict[str, tuple[str, ...]] = {
    "dq_contract_dpa_date": ("dpa.signed",),
    "dq_contract_breach_hours": ("breach.notify_hours", "breach.notify_hours_contract"),
}
_CLAIM_KEYS = frozenset(k for keys in QUESTION_KEYS.values() for k in keys)


@dataclass
class _Entry:
    value: Any
    state: TriState
    provenance: list[Provenance]
    claims: list[str] = field(default_factory=list)
    dq: list[str] = field(default_factory=list)


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", str(name).strip().lower())


class _Facts:
    def __init__(self) -> None:
        self.entries: dict[str, _Entry] = {}

    def set(self, key: str, value: Any, state: TriState, provenance: list[Provenance], **kw: Any) -> None:
        self.entries[key] = _Entry(value if state != "UNKNOWN" else None, state, provenance, **kw)

    def known(self, key: str, value: Any, provenance: list[Provenance], **kw: Any) -> None:
        self.set(key, value, "TRUE", provenance, **kw)

    def boolean(self, key: str, flag: bool, provenance: list[Provenance], **kw: Any) -> None:
        self.set(key, bool(flag), "TRUE" if flag else "FALSE", provenance, **kw)

    def unknown(self, key: str, provenance: list[Provenance], **kw: Any) -> None:
        self.set(key, None, "UNKNOWN", provenance, **kw)

    def copy(self, key: str, source: str) -> None:
        src = self.entries[source]
        self.entries[key] = _Entry(src.value, src.state, list(src.provenance), list(src.claims), list(src.dq))

    def build(self) -> list[Fact]:
        counters: dict[str, int] = {}
        facts: list[Fact] = []
        for key in sorted(self.entries):
            entry = self.entries[key]
            control = control_for_key(key)
            counters[control] = counters.get(control, 0) + 1
            facts.append(
                Fact(
                    fact_id=f"F-{control}-{counters[control]}",
                    control_id=control,
                    key=key,
                    value=entry.value,
                    state=entry.state,
                    provenance=entry.provenance or [Provenance(kind="derived", field=key)],
                    derived_from_claims=entry.claims,
                    dq_flags=entry.dq,
                )
            )
        return facts


def _sor(result: QueryResult, row: dict[str, Any] | None, column: str | None) -> Provenance:
    return Provenance(
        kind="public_feed" if QUERY_SYSTEM.get(result.query_id) == "cisa_kev" else "system_of_record",
        system=QUERY_SYSTEM.get(result.query_id),
        query_id=result.query_id,
        record_key=None if row is None else record_key(result.query_id, row),
        field=column,
        backend=result.backend,
        zetaris_request_id=result.request_id if result.backend == "zetaris" else None,
    )


def _date(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10]) if value not in (None, "") else None
    except ValueError:
        return None


def derive(state: CaseState, policy: Policy) -> tuple[list[Fact], list[Contradiction]]:
    q = state.executed_queries
    f = _Facts()
    hard_gated = {c.id for c in policy.controls if c.hard_gate}
    warned = {s.ref for s in state.segments if s.kind == "answer" and s.guard.level == "warn"}
    blocked_docs = {s.ref for s in state.segments if s.kind == "document" and s.guard.level == "block"}
    dq_by_record: dict[str, list[str]] = {}
    for flag in state.dq_flags:
        dq_by_record.setdefault(flag.record_key, []).append(flag.rule)

    _claims(f, state.claims, warned, hard_gated)
    _profile(f, state, q)
    signed = _contract(f, q, dq_by_record, state.profile)
    _incidents(f, q, state.as_of)
    _watchlist(f, state, q)
    _vulnerabilities(f, q)
    _assurance(f, q, blocked_docs, dq_by_record, state.as_of)

    for key, claimed in (
        ("residency.regions", "residency.regions_claimed"),
        ("transfer.mechanism", "transfer.mechanism_claimed"),
        ("subprocessors.disclosed", "subprocessors.disclosed_claimed"),
    ):
        if not signed and claimed in f.entries:
            f.copy(key, claimed)
    for control in policy.controls:
        keys = list(referenced_keys(control.rule))
        if control.contract_stage_condition is not None:
            keys.append(control.contract_stage_condition.claim_fact)
        for key in keys:
            if key not in f.entries:
                f.unknown(key, [Provenance(kind="derived", field=key)])
    facts = f.build()
    return facts, _contradictions(facts, policy)


def tier_profile(state: CaseState, facts: list[Fact]) -> TierProfile:
    """The tiering inputs: procurement (or inline) profile plus the derived contract status."""
    index = {f.key: f for f in facts}
    categories = index.get("vendor.data_categories")
    raw = state.profile.get("data_categories")
    listed = raw if isinstance(raw, list) else [c.strip() for c in str(raw or "").split(",") if c.strip()]
    contract = index.get("contract.status")
    return TierProfile(
        data_categories=list(categories.value)
        if categories and isinstance(categories.value, list)
        else listed,
        criticality=state.profile["criticality"],
        annual_spend_gbp=float(state.profile.get("annual_spend_gbp") or 0.0),
        contract_status=str(contract.value)
        if contract is not None and contract.value is not None
        else "unknown",
        vendor_category=str(state.profile.get("category") or "") or None,
    )


def _claims(f: _Facts, claims: list[Claim], warned: set[str], hard_gated: set[str]) -> None:
    latest: dict[str, Claim] = {}
    for claim in claims:
        current = latest.get(claim.key)
        if current is None or claim.grounded or not current.grounded:
            latest[claim.key] = claim
    for key, claim in latest.items():
        if key not in _CLAIM_KEYS:
            continue
        guarded = claim.provenance.answer_ref in warned and claim.control_id in hard_gated
        usable = claim.grounded is True and claim.state != "UNKNOWN" and not guarded
        state: TriState = claim.state if usable else "UNKNOWN"
        f.set(key, claim.asserted_value, state, [claim.provenance], claims=[claim.claim_id])


def _profile(f: _Facts, state: CaseState, q: dict[str, QueryResult]) -> None:
    result = q.get("Q_VENDOR_PROFILE")
    row = state.profile or (result.rows[0] if result and result.rows else {})
    raw = row.get("data_categories")
    categories = raw if isinstance(raw, list) else [c.strip() for c in str(raw or "").split(",") if c.strip()]
    if result is not None and result.backend != "inline":
        prov = [_sor(result, row, "data_categories")]
    else:
        prov = [Provenance(kind="derived", system="trust_portal", field="data_categories", backend="inline")]
    if categories:
        f.known("vendor.data_categories", categories, prov)
    else:
        f.unknown("vendor.data_categories", prov)


def _contract(
    f: _Facts, q: dict[str, QueryResult], dq: dict[str, list[str]], profile: dict[str, Any]
) -> bool:
    result = q.get("Q_VENDOR_CONTRACT")
    if result is None:
        if "clm_supplier_ref" in profile and profile.get("clm_supplier_ref") is None:
            source = q.get("Q_VENDOR_PROFILE")
            prov = [_sor(source, profile, "clm_supplier_ref")] if source is not None else []
            f.known("contract.status", "none", prov or [Provenance(kind="derived", field="clm_supplier_ref")])
        else:
            f.unknown("contract.status", [Provenance(kind="derived", field="contract.status")])
        return False
    rows = sorted(result.rows, key=lambda r: (r.get("status") != "signed", str(r.get("contract_id"))))
    if not rows:
        f.known("contract.status", "none", [_sor(result, None, "status")])
        return False
    row = rows[0]
    f.known("contract.status", row.get("status"), [_sor(result, row, "status")])
    if row.get("status") != "signed":
        return False
    flags = dq.get(record_key("Q_VENDOR_CONTRACT", row) or "", [])

    def put(key: str, column: str, value: Any, *, boolean: bool = False) -> None:
        prov = [_sor(result, row, column)]
        hit = [rule for rule in flags if key in DQ_AFFECTS.get(rule, ())]
        if hit or value is None:
            f.unknown(key, prov, dq=hit)
        elif boolean:
            f.boolean(key, bool(value), prov)
        else:
            f.known(key, value, prov)

    hours = row.get("breach_notification_hours")
    put("breach.notify_hours_contract", "breach_notification_hours", hours)
    put("breach.notify_hours", "breach_notification_hours", hours)
    put("dpa.signed", "dpa_signed", row.get("dpa_signed"), boolean=True)
    regions = REGION_CLAUSE.get(str(row.get("hosting_region_clause") or "").upper())
    put("residency.regions_contract", "hosting_region_clause", regions)
    put("residency.regions", "hosting_region_clause", regions)
    put("transfer.mechanism", "transfer_mechanism", row.get("transfer_mechanism"))
    put(
        "subprocessors.disclosed",
        "subprocessor_list_attached",
        row.get("subprocessor_list_attached"),
        boolean=True,
    )
    return True


def _incidents(f: _Facts, q: dict[str, QueryResult], as_of: date) -> None:
    result = q.get("Q_VENDOR_INCIDENTS") or q.get("Q_INCIDENTS_BY_NAME")
    if result is None:
        prov = [Provenance(kind="derived", system="itsm", field="not_queried")]
        f.unknown("incidents.itsm_vendor_related_24m", prov)
        f.unknown("incidents.material_unremediated_24m", prov)
        return
    since = as_of - timedelta(days=INCIDENT_WINDOW_DAYS)
    window = [r for r in result.rows if (_date(r.get("opened_at")) or since) >= since]
    related = [r for r in window if r.get("category") in MATERIAL_CATEGORIES]
    material = [
        r
        for r in related
        if r.get("severity") in {"P1", "P2"}
        and (r.get("rca_completed") is not True or r.get("status") == "open")
    ]
    f.known(
        "incidents.itsm_vendor_related_24m",
        len(related),
        [_sor(result, r, "category") for r in related] or [_sor(result, None, "category")],
    )
    f.known(
        "incidents.material_unremediated_24m",
        len(material),
        [_sor(result, r, "rca_completed") for r in material] or [_sor(result, None, "rca_completed")],
    )


def _names(state: CaseState, q: dict[str, QueryResult]) -> set[str]:
    names = {_norm(n) for n in (state.profile.get("legal_name"), state.profile.get("trading_name")) if n}
    aliases = q.get("Q_VENDOR_ALIASES")
    if aliases is not None:
        names |= {_norm(str(r.get("alias_lower"))) for r in aliases.rows if r.get("alias_lower")}
    return names


def _watchlist(f: _Facts, state: CaseState, q: dict[str, QueryResult]) -> None:
    names = _names(state, q)
    screen = q.get("Q_WATCHLIST_SCREEN")
    full = q.get("Q_WATCHLIST_ALL")
    exact_ids: set[str] = set()
    if screen is not None:
        exact_ids = {str(r.get("entry_id")) for r in screen.rows}
        f.known(
            "sanctions.watchlist_matches",
            len(screen.rows),
            [_sor(screen, r, "entity_name") for r in screen.rows] or [_sor(screen, None, "entity_name")],
        )
    elif full is not None:
        exact = [r for r in full.rows if _norm(str(r.get("entity_name"))) in names]
        exact_ids = {str(r.get("entry_id")) for r in exact}
        f.known(
            "sanctions.watchlist_matches",
            len(exact),
            [_sor(full, r, "entity_name") for r in exact] or [_sor(full, None, "entity_name")],
        )
    else:
        f.unknown("sanctions.watchlist_matches", [Provenance(kind="derived", system="grc_watchlist")])
    if full is None:
        f.unknown("sanctions.near_matches", [Provenance(kind="derived", system="grc_watchlist")])
        return
    near = [
        r
        for r in full.rows
        if str(r.get("entry_id")) not in exact_ids
        and _norm(str(r.get("entity_name"))) not in names
        and any(
            difflib.SequenceMatcher(None, _norm(str(r.get("entity_name"))), n).ratio() >= NEAR_MATCH_RATIO
            for n in names
        )
    ]
    f.known(
        "sanctions.near_matches",
        len(near),
        [_sor(full, r, "entity_name") for r in near] or [_sor(full, None, "entity_name")],
    )


def _vulnerabilities(f: _Facts, q: dict[str, QueryResult]) -> None:
    components = q.get("Q_VENDOR_COMPONENTS")
    kev = q.get("Q_COMPONENT_KEV") or q.get("Q_KEV_BY_PRODUCTS")
    if components is None:
        f.unknown("vuln.components_declared", [Provenance(kind="derived", system="trust_portal")])
        f.unknown("vuln.kev_matches", [Provenance(kind="derived", system="cisa_kev")])
    else:
        declared = len(components.rows)
        f.known("vuln.components_declared", declared, [_sor(components, None, "component_id")])
        if declared == 0:
            f.known("vuln.kev_matches", 0, [_sor(components, None, "component_id")])
        elif kev is None:
            f.unknown(
                "vuln.kev_matches", [Provenance(kind="derived", system="cisa_kev", field="not_queried")]
            )
        else:
            cves = sorted({str(r.get("cve_id")) for r in kev.rows if r.get("cve_id")})
            rows = {str(r.get("cve_id")): r for r in kev.rows}
            f.known(
                "vuln.kev_matches",
                len(cves),
                [_sor(kev, rows[c], "cve_id") for c in cves] or [_sor(kev, None, "cve_id")],
            )
    submission = q.get("Q_SUBMISSION")
    row = submission.rows[0] if submission is not None and submission.rows else None
    if row is not None and row.get("patch_sla_critical_days") is not None:
        f.known(
            "vuln.patch_sla_critical_days",
            row["patch_sla_critical_days"],
            [_sor(submission, row, "patch_sla_critical_days")],
        )  # type: ignore[arg-type]


def _assurance(
    f: _Facts, q: dict[str, QueryResult], blocked: set[str], dq: dict[str, list[str]], as_of: date
) -> None:
    result = q.get("Q_SUBMISSION_DOCUMENTS")
    docs = [] if result is None else list(result.rows)
    usable = [
        d for d in docs if str(d.get("doc_id")) not in blocked and not dq.get(f"doc_id={d.get('doc_id')}")
    ]
    claim = f.entries.get("assurance.claimed")
    claimed = claim.value if claim is not None and claim.state != "UNKNOWN" else None
    claim_prov = claim.provenance[0] if claim is not None and claim.provenance else None
    for item in assurance_facts(usable, claimed=claimed, claim_provenance=claim_prov, as_of=as_of):
        f.set(item.key, item.value, item.state, item.provenance)
    corroboration = mfa_corroboration(usable)
    for key in ("mfa.admin_enforced", "mfa.remote_enforced"):
        entry = f.entries.get(key)
        if entry is not None and entry.state == "TRUE" and corroboration:
            entry.provenance = [*entry.provenance, *corroboration]


def _contradictions(facts: list[Fact], policy: Policy) -> list[Contradiction]:
    index = {fact.key: fact for fact in facts}
    out: list[Contradiction] = []
    for control in policy.controls:
        for check in control.contradiction_checks:
            claim, sor = index.get(check.claim), index.get(check.sor)
            if claim is None or sor is None or claim.state == "UNKNOWN" or sor.state == "UNKNOWN":
                continue
            if not claim.derived_from_claims or claim.value is None or sor.value is None:
                continue
            if not _disagree(check.compare, claim.value, sor.value):
                continue
            out.append(
                Contradiction(
                    key=check.claim.removesuffix("_claimed"),
                    control_id=control.id,
                    claim_id=claim.derived_from_claims[0],
                    claim_value=claim.value,
                    sor_value=sor.value,
                    sor_provenance=sor.provenance[0],
                    severity="material" if check.severity == "material" else "minor",
                )
            )
    return out


def _disagree(compare: str, claim: Any, sor: Any) -> bool:
    if compare == "claim_zero_but_sor_positive":
        return float(claim) == 0 and float(sor) > 0
    if compare == "set_not_subset":
        return not set(claim if isinstance(claim, list) else [claim]) <= set(
            sor if isinstance(sor, list) else [sor]
        )
    if compare == "numeric_mismatch":
        return float(claim) != float(sor)
    return claim != sor
