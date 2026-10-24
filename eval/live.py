"""Live/offline switches for the harness: options, scoped environment, case subset, per-system run facts."""

from __future__ import annotations

import json
import math
import os
import statistics
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.llm.resolve import reset_cache
from app.orchestrator import RunOptions

_ENV_KEYS = ("SAMPLE_MODE", "LLM_PROVIDER", "ARBITER_MEMORY")


def force_offline() -> Settings:
    """DuckDB mirror and the offline generator. No Nightshift and no Zetaris."""
    os.environ["SAMPLE_MODE"] = "true"
    os.environ["LLM_PROVIDER"] = "offline"
    os.environ["ARBITER_MEMORY"] = "off"
    get_settings.cache_clear()
    reset_cache()
    return Settings()


def is_live(system: str, *, live: bool) -> bool:
    return live and system != "arbiter_offline"


def system_options(system: str, *, live: bool) -> RunOptions:
    if is_live(system, live=live):
        return RunOptions(sample_mode=False, llm="meterless")
    return RunOptions(sample_mode=True, llm="offline")


@contextmanager
def system_env(system: str, *, live: bool) -> Iterator[Settings]:
    """Environment for one system. Live pins `LLM_PROVIDER=meterless`, so a Nightshift outage never
    turns into a silent NVIDIA-direct or offline run. The previous environment is restored after."""
    saved = {key: os.environ.get(key) for key in _ENV_KEYS}
    try:
        if is_live(system, live=live):
            os.environ["SAMPLE_MODE"] = "false"
            os.environ["LLM_PROVIDER"] = "meterless"
            os.environ["ARBITER_MEMORY"] = "off"
            get_settings.cache_clear()
            reset_cache()
            yield Settings()
        else:
            yield force_offline()
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        get_settings.cache_clear()
        reset_cache()


def select_cases(refs: list[str], limit: int | None) -> list[str]:
    """The first `limit` cases by case id, or every case."""
    if limit is None:
        return list(refs)
    return sorted(refs)[:limit]


def run_block(rows: list[dict[str, Any]], *, mode: dict[str, str]) -> dict[str, Any]:
    """Per-system run facts read from its own traces: models, routed model per lane, latency, fallbacks."""
    primary = [row for row in rows if int(row.get("repeat") or 0) == 0]
    model_ids: list[str] = []
    routed: dict[str, list[str]] = {}
    calls = 0
    fallbacks = 0
    for row in primary:
        path = Path(row["trace_path"]) if row.get("trace_path") else None
        if path is None or not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("action") != "model_call":
                continue
            calls += 1
            if event.get("status") == "fallback":
                fallbacks += 1
            model = event.get("model")
            if isinstance(model, str) and model and model not in model_ids:
                model_ids.append(model)
            target = (event.get("provider_meta") or {}).get("routed_model") or model
            lane = event.get("route")
            if isinstance(target, str) and target and isinstance(lane, str):
                seen = routed.setdefault(lane, [])
                if target not in seen:
                    seen.append(target)
    latencies = sorted(int(row.get("latency_ms") or 0) for row in primary)
    return {
        "mode": dict(mode),
        "n": len(primary),
        "case_refs": [str(row["case_ref"]) for row in primary],
        "model_ids": model_ids,
        "routed_models": {lane: routed[lane] for lane in sorted(routed)},
        "latency_ms": {
            "p50": int(statistics.median(latencies)) if latencies else 0,
            "p95": latencies[max(math.ceil(0.95 * len(latencies)) - 1, 0)] if latencies else 0,
        },
        "model_calls_per_case": calls / len(primary) if primary else 0.0,
        "fallback_rate": {"rate": fallbacks / calls if calls else None, "count": fallbacks, "n": calls},
    }
