"""Inline submission backend (judges' own vendor input)."""

from __future__ import annotations

import time
import uuid

from app.canon import sha256_hex
from app.data.backend import DataBackend, QueryResult
from app.data.registry import load_registry
from app.schemas.case import VendorSubmission

INLINE_QUERIES = {
    "Q_VENDOR_PROFILE",
    "Q_SUBMISSION",
    "Q_SUBMISSION_ANSWERS",
    "Q_SUBMISSION_DOCUMENTS",
    "Q_VENDOR_COMPONENTS",
}
DELEGATED = {"Q_KEV_BY_PRODUCTS", "Q_WATCHLIST_ALL", "Q_INCIDENTS_BY_NAME"}


def inline_vendor_ref(submission: VendorSubmission) -> str:
    digest = sha256_hex(submission.model_dump(mode="json"))
    return f"SUB-{digest[:8]}"


class InlineBackend:
    name = "inline"

    def __init__(self, submission: VendorSubmission, main: DataBackend) -> None:
        self._submission = submission
        self._main = main
        self._vendor_id = inline_vendor_ref(submission)

    def run(self, query_id: str, params: dict[str, object]) -> QueryResult:
        t0 = time.perf_counter()
        registry = load_registry()
        qdef = registry[query_id]
        if query_id in DELEGATED:
            result = self._delegated(query_id, params)
        elif query_id in INLINE_QUERIES:
            result = self._inline_rows(query_id)
        else:
            result = self._main.run(query_id, params)
            latency = int((time.perf_counter() - t0) * 1000)
            return result.model_copy(update={"backend": "inline", "latency_ms": latency})
        latency = int((time.perf_counter() - t0) * 1000)
        return QueryResult(
            query_id=query_id,
            rows=result,
            columns=qdef.columns,
            backend="inline",
            request_id=uuid.uuid4().hex,
            latency_ms=latency,
        )

    def _inline_rows(self, query_id: str) -> list[dict[str, object]]:
        sub = self._submission
        vid = self._vendor_id
        if query_id == "Q_VENDOR_PROFILE":
            return [
                {
                    "vendor_id": vid,
                    "legal_name": sub.legal_name,
                    "trading_name": sub.trading_name,
                    "category": sub.category,
                    "requested_service": sub.requested_service,
                    "business_owner": "inline_submitter",
                    "annual_spend_gbp": sub.annual_spend_gbp,
                    "criticality": sub.criticality,
                    "data_categories": ",".join(sub.data_categories),
                    "processing_countries": ",".join(sub.processing_countries),
                    "clm_supplier_ref": None,
                    "onboarding_status": "requested",
                    "requested_at": "2026-10-20",
                }
            ]
        if query_id == "Q_SUBMISSION":
            return [
                {
                    "submission_id": f"SUBM-{vid[-8:]}",
                    "vendor_id": vid,
                    "submitted_at": "2026-10-20",
                    "patch_sla_critical_days": sub.patch_sla_critical_days,
                    "contact_role": "security",
                }
            ]
        if query_id == "Q_SUBMISSION_ANSWERS":
            return [
                {
                    "answer_id": f"A-{a.question_id}",
                    "submission_id": f"SUBM-{vid[-8:]}",
                    "vendor_id": vid,
                    "question_id": a.question_id,
                    "question": a.question,
                    "answer_text": a.answer_text,
                }
                for a in sub.answers
            ]
        if query_id == "Q_SUBMISSION_DOCUMENTS":
            return [
                {
                    "doc_id": d.doc_id,
                    "submission_id": f"SUBM-{vid[-8:]}",
                    "vendor_id": vid,
                    "doc_type": d.doc_type,
                    "title": d.title,
                    "issued_on": d.issued_on,
                    "expires_on": d.expires_on,
                    "text": d.text,
                }
                for d in sub.documents
            ]
        if query_id == "Q_VENDOR_COMPONENTS":
            rows: list[dict[str, object]] = []
            for i, comp in enumerate(sub.declared_components):
                rows.append(
                    {
                        "component_id": f"CMP-{i:04d}",
                        "vendor_id": vid,
                        "vendor_project": comp.vendor or comp.product.split()[0],
                        "product": comp.product,
                        "version": comp.version,
                    }
                )
            return rows
        return []

    def _delegated(self, query_id: str, params: dict[str, object]) -> list[dict[str, object]]:
        sub = self._submission
        if query_id == "Q_KEV_BY_PRODUCTS":
            products = [c.product for c in sub.declared_components]
            res = self._main.run(query_id, {"products": products})
            return res.rows
        if query_id == "Q_WATCHLIST_ALL":
            res = self._main.run(query_id, {})
            return res.rows
        if query_id == "Q_INCIDENTS_BY_NAME":
            names = [sub.legal_name]
            if sub.trading_name:
                names.append(sub.trading_name)
            since = params.get("since", "2024-10-26")
            res = self._main.run(query_id, {"names": names, "since": since})
            return res.rows
        return []
