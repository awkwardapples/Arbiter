"""Canonical JSON and hashing for replay and signatures."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from typing import Any

from pydantic import BaseModel


def _normalize(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return _normalize(obj.model_dump(mode="json"))
    if isinstance(obj, datetime):
        obj = obj.replace(tzinfo=UTC) if obj.tzinfo is None else obj.astimezone(UTC)
        return obj.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _normalize(v) for k, v in sorted(obj.items(), key=lambda x: x[0])}
    if isinstance(obj, list):
        return [_normalize(v) for v in obj]
    return obj


def canonical_json(obj: Any) -> str:
    normalized = _normalize(obj)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()
