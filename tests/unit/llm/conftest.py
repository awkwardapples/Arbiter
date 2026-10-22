"""Shared fixtures for lane P2-B unit tests.

Tests never read the developer's `.env` (cwd moves to a temp dir) and never reach a real
provider: provider env vars are cleared and HTTP goes through respx or injected transports.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"

PROVIDER_ENV = (
    "LLM_PROVIDER",
    "METERLESS_BASE_URL",
    "METERLESS_RUNTIME_TOKEN",
    "METERLESS_APP_ID",
    "METERLESS_MODEL_FAST",
    "METERLESS_MODEL_DEEP",
    "METERLESS_TIMEOUT_SECONDS",
    "NVIDIA_BASE_URL",
    "NVIDIA_API_KEY",
    "NVIDIA_MODEL_FAST",
    "NVIDIA_MODEL_DEEP",
    "NVIDIA_TIMEOUT_SECONDS",
    "MODEL_BASE_URL",
    "MODEL_API_KEY",
    "NEMOTRON_MODEL",
)


def make_token(prefix: str) -> str:
    """A fake credential assembled at runtime so the repo secret scanner sees no literal."""
    return prefix + "-" + "".join(chr(ord("a") + (i * 7) % 26) for i in range(32))


@pytest.fixture(autouse=True)
def _isolated_llm_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    for name in PROVIDER_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    from app.llm import resolve

    resolve.reset_cache()
    yield
    resolve.reset_cache()


@pytest.fixture
def meterless_token() -> str:
    return make_token("mlt")


@pytest.fixture
def nvidia_key() -> str:
    return make_token("nvk")


def load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def models_fixture() -> dict[str, Any]:
    return load_fixture("meterless_models.json")


@pytest.fixture
def chat_fixture() -> dict[str, Any]:
    return load_fixture("meterless_chat.json")


class RecordingTransport(httpx.BaseTransport):
    """Records every request (URL and timeout extension) and answers with `handler`."""

    def __init__(self, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        self.handler = handler
        self.requests: list[httpx.Request] = []

    @property
    def timeouts(self) -> list[dict[str, float | None]]:
        return [dict(r.extensions.get("timeout", {})) for r in self.requests]

    @property
    def urls(self) -> list[str]:
        return [str(r.url) for r in self.requests]

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.handler(request)


def read_trace(log_dir: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in sorted(log_dir.glob("trace-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
    return events
