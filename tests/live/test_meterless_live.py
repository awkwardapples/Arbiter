"""Live Meterless Nightshift tests (marker `live`; run only with ARBITER_LIVE_TESTS=1).

P2-T20L: a JSON round-trip on the fast and deep routes through `generate()`.

`test_p2b_capture_fixtures` (opt-in with ARBITER_CAPTURE_FIXTURES=1) records the real responses
used by the offline unit tests. It stores response bodies and `meterless-*` response headers only,
never request headers, and refuses to write a file that contains the runtime token.
"""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import BaseModel

pytestmark = [
    pytest.mark.p2b,
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get("ARBITER_LIVE_TESTS") != "1", reason="ARBITER_LIVE_TESTS != 1"),
]

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
CAPTURE_PROMPT = 'Reply with only this JSON object and nothing else: {"ok": true}'


class Tiny(BaseModel):
    ok: bool


@pytest.mark.parametrize("route", ["fast", "deep"])
def test_p2_t20l_roundtrip(route: str, tmp_path: Path) -> None:
    from app.llm import generator, resolve
    from app.tracing import Tracer

    resolve.reset_cache()
    tracer = Tracer(f"live-p2b-{route}", mode={"data": "duckdb", "llm": "meterless"}, log_dir=str(tmp_path))
    try:
        result = generator.generate(
            CAPTURE_PROMPT,
            route=route,  # type: ignore[arg-type]
            response="json",
            schema=Tiny,
            purpose="ping",
            tracer=tracer,
            agent_name="LiveTest",
        )
    finally:
        tracer.close()
    assert result.provider == "meterless"
    assert isinstance(result.parsed, Tiny) and result.parsed.ok is True
    assert result.model
    events = [
        json.loads(line) for line in (tmp_path / f"trace-live-p2b-{route}.jsonl").read_text().splitlines()
    ]
    calls = [e for e in events if e["action"] == "model_call"]
    assert calls and calls[-1]["status"] == "success"
    assert calls[-1]["provider"] == "meterless"
    assert calls[-1]["model"] == result.model
    assert calls[-1]["route"] == route


def _record(resp: httpx.Response, request: dict[str, Any]) -> dict[str, Any]:
    return {
        "request": request,
        "status": resp.status_code,
        "headers": {k: v for k, v in resp.headers.items() if k.lower().startswith("meterless")},
        "body": resp.json(),
    }


def _write(name: str, payload: dict[str, Any], token: str) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    assert token not in text, "refusing to write a fixture containing the runtime token"
    (FIXTURES / name).write_text(text, encoding="utf-8")


@pytest.mark.skipif(os.environ.get("ARBITER_CAPTURE_FIXTURES") != "1", reason="capture is opt-in")
def test_p2b_capture_fixtures() -> None:
    from app.config import get_settings
    from app.llm.providers.meterless import normalise_base_url

    s = get_settings()
    assert s.METERLESS_RUNTIME_TOKEN is not None, "METERLESS_RUNTIME_TOKEN must be set in .env"
    token = s.METERLESS_RUNTIME_TOKEN.get_secret_value()
    base = normalise_base_url(s.METERLESS_BASE_URL or "http://127.0.0.1:8088")
    headers = {"Authorization": f"Bearer {token}", "meterless-app": s.METERLESS_APP_ID}
    captured_at = datetime.now(UTC).isoformat(timespec="seconds")

    with httpx.Client(timeout=httpx.Timeout(180.0, connect=2.0)) as client:
        models = client.get(f"{base}/models", headers=headers)
        assert models.status_code == 200, f"/v1/models returned {models.status_code}"
        _write(
            "meterless_models.json",
            {"captured_at": captured_at, **_record(models, {"method": "GET", "path": "/v1/models"})},
            token,
        )

        chats: dict[str, Any] = {"captured_at": captured_at}
        for route, model, max_tokens in (
            ("fast", s.METERLESS_MODEL_FAST, 1024),
            ("deep", s.METERLESS_MODEL_DEEP, 2048),
        ):
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": CAPTURE_PROMPT}],
                "temperature": 0.0,
                "max_tokens": max_tokens,
            }
            start = time.monotonic()
            resp = client.post(
                f"{base}/chat/completions", headers={**headers, "meterless-scope": "user"}, json=payload
            )
            assert resp.status_code == 200, f"{route}: HTTP {resp.status_code} {resp.text[:300]}"
            chats[route] = {
                **_record(resp, {"method": "POST", "path": "/v1/chat/completions", **payload}),
                "latency_ms": int((time.monotonic() - start) * 1000),
            }
        _write("meterless_chat.json", chats, token)
