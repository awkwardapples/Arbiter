"""P1-T13 FallbackBackend behaviour."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.data.backend import FailingBackend, FallbackBackend
from app.data.duckdb_backend import DuckDBBackend, reset_cache
from app.errors import Unauthorized, UpstreamTimeout
from app.tracing import Tracer


@pytest.mark.p1a
def test_p1_t13_fallback_timeout_and_unauthorized(tmp_path: Path) -> None:
    """P1-T13: timeout per-query fallback; 401 pins secondary."""
    reset_cache()
    duck = DuckDBBackend()
    tracer = Tracer("run-fallback", mode={"sample": "true"}, log_dir=str(tmp_path))
    fb = FallbackBackend(
        FailingBackend(UpstreamTimeout("slow")),
        duck,
        tracer,
    )
    res = fb.run("Q_VENDOR_PROFILE", {"vendor_id": "VND-0003"})
    assert res.fallback_from == "failing"
    assert res.rows
    lines = (tmp_path / "trace-run-fallback.jsonl").read_text().strip().splitlines()
    assert any(json.loads(line).get("status") == "fallback" for line in lines)

    fb2 = FallbackBackend(FailingBackend(Unauthorized("nope")), duck, tracer)
    fb2.run("Q_VENDOR_PROFILE", {"vendor_id": "VND-0003"})
    res2 = fb2.run("Q_VENDOR_PROFILE", {"vendor_id": "VND-0004"})
    assert res2.fallback_from == "failing"
