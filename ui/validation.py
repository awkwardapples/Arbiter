"""Client-side intake validation (lane P5-A)."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from ui.models import CaseInput, VendorSubmission


def parse_case_input(raw: str | dict[str, Any]) -> tuple[CaseInput | None, list[str]]:
    """Validate vendor_id or submission JSON. Returns (case, errors)."""
    errors: list[str] = []
    data: Any
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None, ["Paste JSON or pick a vendor."]
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            return None, [f"Invalid JSON: {exc.msg}"]
    else:
        data = raw

    if not isinstance(data, dict):
        return None, ["Submission must be a JSON object."]

    has_vendor = bool(str(data.get("vendor_id", "")).strip())
    has_sub = data.get("submission") is not None or "legal_name" in data
    if has_vendor and has_sub:
        return None, ["Provide either vendor_id or submission, not both."]

    try:
        if has_vendor:
            return CaseInput.model_validate({"vendor_id": data["vendor_id"]}), []
        if "submission" in data:
            return CaseInput.model_validate(data), []
        if "legal_name" in data:
            sub = VendorSubmission.model_validate(data)
            return CaseInput.model_validate({"submission": sub}), []
        return CaseInput.model_validate(data), []
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(part) for part in err.get("loc", ()))
            msg = err.get("msg", "invalid")
            errors.append(f"{loc}: {msg}" if loc else str(msg))
        return None, errors or ["Validation failed."]
