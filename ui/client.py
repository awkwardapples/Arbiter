"""HTTP client for the Arbiter API (lane P5-A)."""

from __future__ import annotations

import os
from typing import Any

import httpx

from app.schemas.api import (
    ApprovalRequest,
    CaseInput,
    HealthResponse,
    ReviewRequest,
    RunRequestOptions,
    RunResponse,
)
from app.schemas.trace import TraceEvent

DEFAULT_BASE_URL = "http://localhost:8000"
TIMEOUT = 30.0


class ArbiterAPIError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ArbiterClient:
    def __init__(self, base_url: str | None = None, *, client: httpx.Client | None = None) -> None:
        self.base_url = (base_url or os.environ.get("ARBITER_API_URL", DEFAULT_BASE_URL)).rstrip("/")
        self._client = client or httpx.Client(base_url=self.base_url, timeout=TIMEOUT)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            resp = self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise ArbiterAPIError(
                "The API did not respond in time. Is `python run.py serve` running?"
            ) from exc
        except httpx.RequestError as exc:
            raise ArbiterAPIError(f"Could not reach the API at {self.base_url}: {exc}") from exc
        if resp.status_code >= 400:
            message = self._error_message(resp)
            raise ArbiterAPIError(message, status_code=resp.status_code)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    @staticmethod
    def _error_message(resp: httpx.Response) -> str:
        try:
            body = resp.json()
        except ValueError:
            return f"Request failed ({resp.status_code})."
        err = body.get("error") if isinstance(body, dict) else None
        if isinstance(err, dict) and err.get("message"):
            return str(err["message"])
        if isinstance(body, dict) and body.get("detail"):
            return str(body["detail"])
        return f"Request failed ({resp.status_code})."

    def health(self) -> HealthResponse:
        return HealthResponse.model_validate(self._request("GET", "/health"))

    def list_vendors(self) -> list[dict[str, object]]:
        data = self._request("GET", "/vendors")
        return list(data) if isinstance(data, list) else []

    def run(self, case: CaseInput, *, options: RunRequestOptions | None = None) -> RunResponse:
        payload: dict[str, Any] = {"case": case.model_dump(mode="json")}
        if options is not None:
            payload["options"] = options.model_dump(mode="json", exclude_none=True)
        return RunResponse.model_validate(self._request("POST", "/run", json=payload))

    def list_cases(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/cases")
        return list(data) if isinstance(data, list) else []

    def get_case(self, case_id: str) -> dict[str, Any]:
        data = self._request("GET", f"/cases/{case_id}")
        return dict(data) if isinstance(data, dict) else {}

    def get_trace(self, case_id: str) -> list[dict[str, Any]]:
        data = self._request("GET", f"/cases/{case_id}/trace")
        return list(data) if isinstance(data, list) else []

    def replay(self, case_id: str) -> dict[str, Any]:
        data = self._request("POST", f"/cases/{case_id}/replay")
        return dict(data) if isinstance(data, dict) else {}

    def submit_review(self, case_id: str, body: ReviewRequest, *, dry_run: bool = False) -> dict[str, Any]:
        params = {"dry_run": "true"} if dry_run else None
        data = self._request(
            "POST",
            f"/cases/{case_id}/review",
            params=params,
            json=body.model_dump(mode="json"),
        )
        return dict(data) if isinstance(data, dict) else {}

    def list_precedents(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/memory/precedents")
        return list(data) if isinstance(data, list) else []

    def audit_verify(self) -> dict[str, Any]:
        data = self._request("GET", "/audit/verify")
        return dict(data) if isinstance(data, dict) else {}

    def approve_contract(self, contract_id: str, body: ApprovalRequest) -> dict[str, Any]:
        data = self._request(
            "POST",
            f"/contracts/{contract_id}/approve",
            json=body.model_dump(mode="json"),
        )
        return dict(data) if isinstance(data, dict) else {}

    def eval_latest(self) -> dict[str, Any]:
        return dict(self._request("GET", "/eval/latest"))

    @staticmethod
    def parse_trace_events(events: list[dict[str, Any]]) -> list[TraceEvent]:
        return [TraceEvent.model_validate(e) for e in events]
