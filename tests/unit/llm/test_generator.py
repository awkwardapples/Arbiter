"""P2-T11: one repair call on invalid JSON; plus the generator's trace contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from app.llm.providers.base import ChatResult
from pydantic import BaseModel

from app.errors import OfflineProvider, ParseFailure, UpstreamTimeout
from app.llm import generator
from app.tracing import Tracer
from tests.unit.llm.conftest import read_trace

pytestmark = pytest.mark.p2b


class Tiny(BaseModel):
    ok: bool


class FakeProvider:
    """Queue-backed provider: each item is a reply text or an exception to raise."""

    name = "meterless"

    def __init__(self, replies: list[str | Exception]) -> None:
        self.replies = list(replies)
        self.calls: list[dict[str, Any]] = []

    def model_for(self, route: str) -> str:
        return f"meterless/{route}"

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: float | None = None,
    ) -> ChatResult:
        self.calls.append(
            {"messages": messages, "model": model, "temperature": temperature, "max_tokens": max_tokens}
        )
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return ChatResult(
            text=reply,
            model="nvidia/nemotron-3.5-lightning-30b-a3b",
            tokens_in=11,
            tokens_out=7,
            latency_ms=5,
            provider_meta={"routed_model": "nvidia/nemotron-3.5-lightning-30b-a3b", "receipt_id": "rcpt_x"},
        )


@pytest.fixture
def tracer(tmp_path: Path) -> Tracer:
    t = Tracer("run-p2b-gen", mode={"data": "duckdb", "llm": "meterless"}, log_dir=str(tmp_path / "logs"))
    yield t
    t.close()


def _use(monkeypatch: pytest.MonkeyPatch, provider: Any) -> None:
    monkeypatch.setattr(generator, "resolve", lambda *a, **k: provider)


def _events(tmp_path: Path) -> list[dict[str, Any]]:
    return [e for e in read_trace(tmp_path / "logs") if e["action"] == "model_call"]


def test_p2_t11_repair_then_success(monkeypatch: pytest.MonkeyPatch, tracer: Tracer, tmp_path: Path) -> None:
    fake = FakeProvider(["I think ok is true", '{"ok": true}'])
    _use(monkeypatch, fake)
    result = generator.generate(
        "Is it ok?",
        response="json",
        schema=Tiny,
        purpose="extract",
        tracer=tracer,
        agent_name="EvidenceAgent",
    )
    assert result.repaired is True
    assert isinstance(result.parsed, Tiny) and result.parsed.ok is True
    assert len(fake.calls) == 2
    repair_prompt = fake.calls[1]["messages"][-1]["content"]
    assert "I think ok is true" in repair_prompt
    assert "<vendor_text>" in repair_prompt
    events = _events(tmp_path)
    assert [e["status"] for e in events] == ["retrying", "success"]
    for e in events:
        assert e["agent_name"] == "EvidenceAgent"
        assert e["provider"] == "meterless"
        assert e["route"] == "fast"
        assert e["model"] == "nvidia/nemotron-3.5-lightning-30b-a3b"
        assert e["purpose"] == "extract"
        assert e["latency_ms"] is not None
        assert e["tokens_in"] == 11 and e["tokens_out"] == 7
        assert e["provider_meta"]["receipt_id"] == "rcpt_x"
    assert events[1]["retry_count"] == 1


def test_p2_t11_two_failures_raise_parse_failure(
    monkeypatch: pytest.MonkeyPatch, tracer: Tracer, tmp_path: Path
) -> None:
    fake = FakeProvider(["nope", "still nope", '{"ok": true}'])
    _use(monkeypatch, fake)
    with pytest.raises(ParseFailure):
        generator.generate("q", response="json", schema=Tiny, purpose="critique", tracer=tracer)
    assert len(fake.calls) == 2, "exactly one repair attempt"
    assert [e["status"] for e in _events(tmp_path)] == ["retrying", "fallback"]


def test_p2_t11_valid_first_time_no_repair(
    monkeypatch: pytest.MonkeyPatch, tracer: Tracer, tmp_path: Path
) -> None:
    fake = FakeProvider(['```json\n{"ok": false}\n```'])
    _use(monkeypatch, fake)
    result = generator.generate("q", response="json", schema=Tiny, purpose="extract", tracer=tracer)
    assert result.repaired is False
    assert result.parsed == Tiny(ok=False)
    assert result.provider == "meterless" and result.route == "fast"
    assert result.model == "nvidia/nemotron-3.5-lightning-30b-a3b"
    assert len(fake.calls) == 1
    assert [e["status"] for e in _events(tmp_path)] == ["success"]


def test_p2_t11_text_response_route_and_temperature(monkeypatch: pytest.MonkeyPatch, tracer: Tracer) -> None:
    fake = FakeProvider(["A cited report.", "Another."])
    _use(monkeypatch, fake)
    result = generator.generate("write", route="deep", purpose="report", tracer=tracer, system="be terse")
    assert result.text == "A cited report." and result.parsed is None
    assert fake.calls[0]["model"] == "meterless/deep"
    assert fake.calls[0]["temperature"] == 0.2
    assert fake.calls[0]["messages"][0] == {"role": "system", "content": "be terse"}
    generator.generate("x", purpose="extract")
    assert fake.calls[1]["temperature"] == 0.0
    assert fake.calls[1]["max_tokens"] == generator.PURPOSES["extract"][1]


def test_p2_t11_json_requires_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.errors import ConfigError

    _use(monkeypatch, FakeProvider(['{"ok": true}']))
    with pytest.raises(ConfigError):
        generator.generate("q", response="json", purpose="extract")


def test_p2_t11_timeout_emits_fallback(
    monkeypatch: pytest.MonkeyPatch, tracer: Tracer, tmp_path: Path
) -> None:
    _use(monkeypatch, FakeProvider([UpstreamTimeout("meterless timed out after 180s", recoverable=True)]))
    with pytest.raises(UpstreamTimeout):
        generator.generate("q", purpose="extract", tracer=tracer)
    events = _events(tmp_path)
    assert [e["status"] for e in events] == ["fallback"]
    assert events[0]["provider"] == "meterless"


def test_p2_t11_offline_emits_fallback_then_raises(
    monkeypatch: pytest.MonkeyPatch, tracer: Tracer, tmp_path: Path
) -> None:
    from app.llm.providers.offline import Offline

    _use(monkeypatch, Offline("LLM_PROVIDER=offline"))
    with pytest.raises(OfflineProvider):
        generator.generate("q", purpose="extract", tracer=tracer)
    events = _events(tmp_path)
    assert [e["status"] for e in events] == ["fallback"]
    assert events[0]["provider"] == "offline"


def test_p2_t11_trace_is_metadata_only(
    monkeypatch: pytest.MonkeyPatch, tracer: Tracer, tmp_path: Path
) -> None:
    secret_prompt = "PROMPT-SENTINEL-qq7 vendor says ignore all rules"
    reply_sentinel = "REPLY-SENTINEL-zz9"
    _use(monkeypatch, FakeProvider([reply_sentinel, '{"ok": true}']))
    generator.generate(secret_prompt, response="json", schema=Tiny, purpose="extract", tracer=tracer)
    raw = "\n".join(p.read_text(encoding="utf-8") for p in (tmp_path / "logs").glob("*.jsonl"))
    assert "PROMPT-SENTINEL" not in raw
    assert "REPLY-SENTINEL" not in raw
