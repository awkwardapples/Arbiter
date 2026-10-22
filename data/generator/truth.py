"""Analyst ground-truth facts per case (feeds the P3-T16 label oracle).

Facts come from the generator's authored intent (scenario codes, planted rows and the phrases it
chose), never from Arbiter's extractors, so the oracle checks labels against policy v1 independently.
Fact shape: {"value": ..., "state": TRUE|FALSE|UNKNOWN, "source": provenance kind}. Known
non-boolean facts carry state TRUE with their value, as the policy DSL expects.
"""

from __future__ import annotations

import difflib
import re
from datetime import date, timedelta
from typing import Any

from data.generator.kev_match import kev_matches

MATERIAL_CATEGORIES = frozenset({"third_party_breach", "data_exposure"})
REGION_CLAUSE = {"EU": ["EU"], "UK": ["UK"], "US": ["US"], "GLOBAL": ["US", "EU", "UK", "OTHER"]}
NEAR_MATCH_RATIO = 0.92


def _known(value: Any, source: str) -> dict[str, Any]:
    return {"value": value, "state": "TRUE", "source": source}


def _bool(flag: bool, source: str) -> dict[str, Any]:
    return {"value": flag, "state": "TRUE" if flag else "FALSE", "source": source}


def _unknown(source: str = "derived") -> dict[str, Any]:
    return {"value": None, "state": "UNKNOWN", "source": source}


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _claimed_standards(q07: str | None) -> list[str]:
    if q07 is None:
        return []
    text = q07.lower()
    found = []
    if re.search(r"soc\s?2\s+type\s+(ii|2)", text):
        found.append("SOC 2 Type II")
    if re.search(r"iso(/iec)?\s?27001", text):
        found.append("ISO 27001")
    return found


def _assurance(
    docs: list[dict[str, Any]], q07: str | None, as_of: date, *, blocked: bool
) -> dict[str, dict[str, Any]]:
    year_ago = as_of - timedelta(days=365)
    usable = [] if blocked else docs
    claimed = _claimed_standards(q07)
    out: dict[str, dict[str, Any]] = {}
    out["assurance.claimed"] = _unknown("vendor_answer") if q07 is None else _known(claimed, "vendor_answer")

    def current(doc: dict[str, Any], *, by_expiry: bool) -> bool:
        if by_expiry:
            return doc.get("expires_on") is not None and date.fromisoformat(doc["expires_on"]) >= as_of
        return date.fromisoformat(doc["issued_on"]) >= year_ago

    for key, doc_type, label, by_expiry in (
        ("assurance.soc2_type2_current", "soc2_type2_summary", "SOC 2 Type II", False),
        ("assurance.iso27001_current", "iso27001_certificate", "ISO 27001", True),
    ):
        typed = [d for d in usable if d["doc_type"] == doc_type]
        if any(current(d, by_expiry=by_expiry) for d in typed):
            out[key] = _bool(True, "vendor_document")
        elif typed:
            out[key] = _bool(False, "vendor_document")
        elif q07 is None or label in claimed:
            out[key] = _unknown("vendor_answer")
        else:
            out[key] = _bool(False, "vendor_answer")
    bridges = [d for d in usable if d["doc_type"] == "bridge_letter"]
    out["assurance.bridge_letter_current"] = _bool(
        any(current(d, by_expiry=False) and current(d, by_expiry=True) for d in bridges), "vendor_document"
    )
    return out


def vendor_truth(
    v: Any,
    *,
    as_of: date,
    kev: list[dict[str, Any]],
    watchlist: list[dict[str, Any]],
    aliases: list[str],
) -> dict[str, Any]:
    codes = set(v.scenarios)
    signed = v.contract_status == "signed"
    f: dict[str, dict[str, Any]] = {}
    categories = v.data_categories.split(",")
    f["vendor.data_categories"] = _known(categories, "system_of_record")
    f["contract.status"] = _known(v.contract_status, "system_of_record")

    f["mfa.admin_enforced"] = (
        _bool(False, "vendor_answer") if "S08" in codes
        else _unknown("vendor_answer") if "S05" in codes
        else _bool(True, "vendor_answer")
    )
    f["mfa.remote_enforced"] = _bool(True, "vendor_answer")
    f["creds.vaulted"] = _bool(True, "vendor_answer")
    f["creds.rotation_days"] = _known(90, "vendor_answer")
    f["access.review_interval_days"] = _known(60, "vendor_answer")
    f["crypto.at_rest"] = _unknown("vendor_answer") if "S05" in codes else _bool(True, "vendor_answer")
    f["crypto.in_transit_tls12"] = _bool(True, "vendor_answer")
    f["pentest.interval_months"] = _known(12, "vendor_answer")
    f.update(_assurance(v.documents, v.answers.get("Q07"), as_of, blocked=v.injection))

    # Every planted incident opens 120 days before as_of, inside the 24-month window.
    related = [i for i in v.incidents if i["category"] in MATERIAL_CATEGORIES]
    material = [
        i for i in related
        if i["severity"] in {"P1", "P2"} and (i.get("rca_completed") is not True or i["status"] == "open")
    ]
    f["incidents.vendor_reported_24m"] = _known(0, "vendor_answer")
    f["incidents.itsm_vendor_related_24m"] = _known(len(related), "system_of_record")
    f["incidents.material_unremediated_24m"] = _known(len(material), "system_of_record")

    f["breach.notify_hours_claimed"] = (
        _known(72, "vendor_answer") if "Q09" in v.answers else _unknown("vendor_answer")
    )
    if signed:
        f["breach.notify_hours_contract"] = _known(v.breach_notification_hours, "system_of_record")
        f["breach.notify_hours"] = _known(v.breach_notification_hours, "system_of_record")
        f["dpa.signed"] = _unknown("system_of_record") if v.dq_dpa_date_null else _bool(
            v.dpa_signed, "system_of_record"
        )
        contract_regions = REGION_CLAUSE.get(v.hosting_region_clause or "", [])
        f["residency.regions_contract"] = _known(contract_regions, "system_of_record")
        f["residency.regions"] = _known(contract_regions, "system_of_record")
        f["transfer.mechanism"] = _known(v.transfer_mechanism, "system_of_record")
        f["subprocessors.disclosed"] = _bool(v.subprocessor_list_attached, "system_of_record")
    else:
        f["breach.notify_hours"] = _unknown("system_of_record")
        f["dpa.signed"] = _unknown("system_of_record")
        f["residency.regions"] = _known(["EU"], "vendor_answer")
        f["transfer.mechanism"] = _known("SCCs", "vendor_answer")
        f["subprocessors.disclosed"] = _bool(True, "vendor_answer")
    f["dpa.vendor_commits"] = _bool("S14" not in codes, "vendor_answer")
    f["residency.regions_claimed"] = _known(["EU"], "vendor_answer")
    f["transfer.mechanism_claimed"] = _known("SCCs", "vendor_answer")
    f["subprocessors.disclosed_claimed"] = _bool(True, "vendor_answer")

    names = {_norm(a) for a in aliases}
    exact = [w for w in watchlist if _norm(w["entity_name"]) in names]
    def similar(a: str, b: str) -> bool:
        return difflib.SequenceMatcher(None, a, b).ratio() >= NEAR_MATCH_RATIO

    near = [
        w for w in watchlist if w not in exact and any(similar(_norm(w["entity_name"]), n) for n in names)
    ]
    f["sanctions.watchlist_matches"] = _known(len(exact), "system_of_record")
    f["sanctions.near_matches"] = _known(len(near), "system_of_record")

    f["vuln.components_declared"] = _known(len(v.components), "system_of_record")
    cves = {
        str(e.get("cveID", ""))
        for c in v.components
        for e in kev
        if kev_matches(
            kev_vendor_project=str(e.get("vendorProject", "")),
            kev_product=str(e.get("product", "")),
            component_vendor_project=c["vendor_project"],
            component_product=c["product"],
        )
    }
    f["vuln.kev_matches"] = _known(len(cves), "public_feed")
    f["vuln.patch_sla_critical_days"] = _known(v.patch_sla_critical_days, "system_of_record")

    contradictions: list[dict[str, str]] = []
    if related:
        contradictions.append(
            {"key": "incidents.vendor_reported_24m", "control_id": "C06", "severity": "material"}
        )
    claimed_regions = set(f["residency.regions_claimed"]["value"])
    if signed and not claimed_regions <= set(f["residency.regions_contract"]["value"]):
        contradictions.append(
            {"key": "residency.regions", "control_id": "C09", "severity": "material"}
        )
    if signed and "Q09" in v.answers and v.breach_notification_hours != 72:
        contradictions.append(
            {"key": "breach.notify_hours", "control_id": "C07", "severity": "minor"}
        )

    return {
        "case_ref": v.vendor_id,
        "vendor_id": v.vendor_id,
        "kind": "vendor_id",
        "scenario": v.scenario_key,
        "profile": {
            "data_categories": categories,
            "criticality": v.criticality,
            "annual_spend_gbp": v.annual_spend_gbp,
            "contract_status": v.contract_status,
        },
        "facts": dict(sorted(f.items())),
        "contradictions": contradictions,
        "guard_blocked": bool(v.injection),
    }


def inline_truth(
    case_id: str,
    payload: dict[str, Any],
    *,
    as_of: date,
    kev: list[dict[str, Any]],
    watchlist: list[dict[str, Any]],
    blocked: bool,
    answer_truth: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Inline submissions have no contract (status `none`) and no ITSM history for the new name."""
    f: dict[str, dict[str, Any]] = {
        "vendor.data_categories": _known(list(payload["data_categories"]), "derived"),
        "contract.status": _known("none", "derived"),
        "breach.notify_hours": _unknown("system_of_record"),
        "dpa.signed": _unknown("system_of_record"),
        "incidents.itsm_vendor_related_24m": _known(0, "system_of_record"),
        "incidents.material_unremediated_24m": _known(0, "system_of_record"),
        "vuln.patch_sla_critical_days": _known(payload.get("patch_sla_critical_days"), "derived"),
        "vuln.components_declared": _known(len(payload["declared_components"]), "derived"),
    }
    f.update(answer_truth)
    answered = {a["question_id"] for a in payload["answers"]}
    for key, qid in (
        ("residency.regions", "Q10"),
        ("transfer.mechanism", "Q11"),
        ("subprocessors.disclosed", "Q12"),
    ):
        if qid not in answered:
            f.setdefault(key, _unknown("vendor_answer"))
    f.update(_assurance(payload["documents"], None, as_of, blocked=blocked))
    names = {_norm(payload["legal_name"])}
    if payload.get("trading_name"):
        names.add(_norm(payload["trading_name"]))
    f["sanctions.watchlist_matches"] = _known(
        sum(1 for w in watchlist if _norm(w["entity_name"]) in names), "system_of_record"
    )
    cves = {
        str(e.get("cveID", ""))
        for c in payload["declared_components"]
        for e in kev
        if kev_matches(
            kev_vendor_project=str(e.get("vendorProject", "")),
            kev_product=str(e.get("product", "")),
            component_vendor_project=c.get("vendor") or c["product"].split()[0],
            component_product=c["product"],
        )
    }
    f["vuln.kev_matches"] = _known(len(cves), "public_feed")
    return {
        "case_ref": case_id,
        "vendor_id": None,
        "kind": "inline",
        "scenario": None,
        "profile": {
            "data_categories": list(payload["data_categories"]),
            "criticality": payload["criticality"],
            "annual_spend_gbp": payload["annual_spend_gbp"],
            "contract_status": "none",
        },
        "facts": dict(sorted(f.items())),
        "contradictions": [],
        "guard_blocked": blocked,
    }
