"""Facts from assurance documents: SOC 2 / ISO / bridge-letter currency and C01 corroboration (02 §4)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from app.extract.deterministic import sentences
from app.schemas.common import Provenance, TriState

_STANDARDS = (
    # fact key, document type, claimed label, current-by-expiry
    ("assurance.soc2_type2_current", "soc2_type2_summary", "SOC 2 Type II", False),
    ("assurance.iso27001_current", "iso27001_certificate", "ISO 27001", True),
)
_MFA = re.compile(r"\b(mfa|multi[- ]factor)\b", re.IGNORECASE)
_PRIVILEGED = re.compile(r"\b(privileged|admin\w*)\b", re.IGNORECASE)
_REMOTE = re.compile(r"\bremote\b", re.IGNORECASE)
_EXCEPTION_NOTED = re.compile(
    r"\b(exceptions? (noted|found|identified)|not enforced|except for|qualified)\b", re.I
)


@dataclass(frozen=True)
class DocFact:
    key: str
    value: Any
    state: TriState
    provenance: list[Provenance]


def _date(value: object) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _issued_within_year(doc: dict[str, Any], as_of: date) -> bool:
    issued = _date(doc.get("issued_on"))
    return issued is not None and as_of - timedelta(days=365) <= issued <= as_of


def _not_expired(doc: dict[str, Any], as_of: date) -> bool:
    expires = _date(doc.get("expires_on"))
    return expires is not None and expires >= as_of


def _doc_provenance(doc: dict[str, Any], field: str) -> Provenance:
    return Provenance(
        kind="vendor_document",
        system="trust_portal",
        query_id="Q_SUBMISSION_DOCUMENTS",
        record_key=f"doc_id={doc.get('doc_id')}",
        field=field,
    )


def assurance_facts(
    docs: list[dict[str, Any]],
    *,
    claimed: list[str] | None,
    claim_provenance: Provenance | None,
    as_of: date,
) -> list[DocFact]:
    """`docs` are the usable (not blocked, not DQ-flagged) documents; `claimed` is Q07's grounded set."""
    out: list[DocFact] = []
    answer = [claim_provenance] if claim_provenance is not None else []
    for key, doc_type, label, by_expiry in _STANDARDS:
        typed = [d for d in docs if d.get("doc_type") == doc_type]
        current = [
            d for d in typed if (_not_expired(d, as_of) if by_expiry else _issued_within_year(d, as_of))
        ]
        field = "expires_on" if by_expiry else "issued_on"
        if current:
            out.append(DocFact(key, True, "TRUE", [_doc_provenance(d, field) for d in current]))
        elif typed:
            out.append(DocFact(key, False, "FALSE", [_doc_provenance(d, field) for d in typed]))
        elif claimed is None or label in claimed:
            out.append(DocFact(key, None, "UNKNOWN", answer or [Provenance(kind="derived", field=key)]))
        else:
            out.append(DocFact(key, False, "FALSE", answer))
    bridges = [d for d in docs if d.get("doc_type") == "bridge_letter"]
    live = [d for d in bridges if _issued_within_year(d, as_of) and _not_expired(d, as_of)]
    if live:
        out.append(
            DocFact(
                "assurance.bridge_letter_current",
                True,
                "TRUE",
                [_doc_provenance(d, "issued_on") for d in live],
            )
        )
    else:
        prov = [_doc_provenance(d, "expires_on") for d in bridges] or [
            Provenance(kind="derived", system="trust_portal", query_id="Q_SUBMISSION_DOCUMENTS")
        ]
        out.append(DocFact("assurance.bridge_letter_current", False, "FALSE", prov))
    return out


def mfa_corroboration(docs: list[dict[str, Any]]) -> list[Provenance]:
    """Assurance-report sentences that note MFA for privileged and remote access with no exception."""
    found: list[Provenance] = []
    for doc in docs:
        if doc.get("doc_type") not in {"soc2_type2_summary", "iso27001_certificate"}:
            continue
        for sentence in sentences(str(doc.get("text") or "")):
            if (
                _MFA.search(sentence)
                and _PRIVILEGED.search(sentence)
                and _REMOTE.search(sentence)
                and not _EXCEPTION_NOTED.search(sentence)
            ):
                prov = _doc_provenance(doc, "text").model_copy(update={"quote": sentence})
                found.append(prov)
                break
    return found
