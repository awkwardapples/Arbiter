"""Provider proof panel: what served the last run, from /health and the stored trace (lane P14-B)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

PROOF_PATH = Path(__file__).resolve().parents[1] / "docs" / "evidence" / "nightshift_proof.json"
OFFLINE_LINE = "Offline fallback (deterministic). Live runs use Meterless Nightshift → NVIDIA Nemotron."
PROOF_PLACEHOLDER = "Live Nightshift proof is produced by the P15 pass. See docs/evidence/ when it lands."


def _served(trace: list[dict[str, Any]]) -> tuple[dict[str, str], str | None]:
    """Model served per route and the last receipt id, from model-call events only."""
    models: dict[str, str] = {}
    receipt: str | None = None
    for event in trace:
        if event.get("provider") not in ("meterless", "nvidia"):
            continue
        meta = event.get("provider_meta") or {}
        # provider_model is the routing mode (meterless/auto), not the model that served the call
        model = event.get("model") or meta.get("routed_model") or meta.get("winning_route.model")
        route = event.get("route")
        if model and route:
            models[str(route)] = str(model)
        if meta.get("receipt_id"):
            receipt = str(meta["receipt_id"])
    return models, receipt


def provider_lines(health: dict[str, Any], trace: list[dict[str, Any]]) -> list[str]:
    """Lines for the panel. Reads named fields only, so a token in the payload is never shown."""
    provider = health.get("provider") or {}
    resolved = str(provider.get("provider_resolved") or "offline")
    models, receipt = _served(trace)
    lines: list[str] = []
    if resolved == "meterless":
        meterless = provider.get("meterless") or {}
        status, url = meterless.get("status", "unknown"), meterless.get("base_url", "unknown")
        lines.append(f"Nightshift: {status} · {url} · token hidden")
    elif resolved == "nvidia":
        nvidia = provider.get("nvidia") or {}
        lines.append(f"NVIDIA API (direct): {nvidia.get('base_url', 'unknown')} · key hidden")
    else:
        lines.append(OFFLINE_LINE)
    if resolved != "offline":
        for route in ("fast", "deep"):
            if route in models:
                lines.append(f"{route} → {models[route]}")
        if receipt:
            lines.append(f"Last receipt: {receipt}")
    if receipt is None and not PROOF_PATH.is_file():
        lines.append(PROOF_PLACEHOLDER)
    elif PROOF_PATH.is_file():
        lines.append("Committed proof: docs/evidence/nightshift_proof.json")
    return lines
