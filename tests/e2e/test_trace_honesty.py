"""P3-T13: trace honesty. model_call events == provider calls; query_* events == backend calls."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import app.llm.generator as generator_module
from app.data.factory import get_backend
from app.llm.providers.base import ChatResult
from app.orchestrator import Deps, RunOptions, run
from tests.e2e.support import load_example, offline_env, trace

pytestmark = pytest.mark.p3
__all__ = ["offline_env"]


class FakeProvider:
    """Answers every chat with text that is not JSON, so each step repairs once and falls back."""

    name = "fake"

    def __init__(self) -> None:
        self.calls = 0

    def model_for(self, route: str) -> str:
        return f"fake/{route}"

    def chat(self, messages: list[dict[str, str]], **_kwargs: Any) -> ChatResult:
        self.calls += 1
        return ChatResult(text="not json at all", model="fake-model", latency_ms=1)


class CountingBackend:
    name = "counting"

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.calls = 0

    def run(self, query_id: str, params: dict[str, object]) -> Any:
        self.calls += 1
        return self.inner.run(query_id, params)


@pytest.mark.parametrize("name", ["example_2.json", "example_6.json"])
def test_p3_t13_events_match_executed_actions(
    name: str, offline_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    provider = FakeProvider()
    monkeypatch.setattr(generator_module, "resolve", lambda *a, **k: provider)
    backends: list[CountingBackend] = []

    def factory(settings: Any, tracer: Any, submission: Any = None) -> Any:
        backend = CountingBackend(get_backend(settings, tracer, submission))
        backends.append(backend)
        return backend

    resp = run(load_example(name), options=RunOptions(), deps=Deps(backend_factory=factory))
    rows = trace(resp.log_file)

    model_calls = [r for r in rows if r["action"] == "model_call"]
    assert provider.calls > 0
    assert len(model_calls) == provider.calls
    query_events = [r for r in rows if r["action"].startswith("query_")]
    assert sum(b.calls for b in backends) > 0
    assert len(query_events) == sum(b.calls for b in backends)
    fallbacks = [r for r in rows if r["status"] == "fallback" and r["provider"] == "offline"]
    assert fallbacks
