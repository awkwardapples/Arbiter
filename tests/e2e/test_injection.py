"""P3-T12: blocked vendor text never reaches the generator; the case escalates for tampering."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import app.llm.generator as generator_module
from app.data.factory import get_backend
from app.errors import OfflineProvider
from app.orchestrator import Deps, RunOptions, run
from app.store import Store
from tests.e2e.support import load_example, offline_env, trace

pytestmark = pytest.mark.p3
__all__ = ["offline_env"]

CANARY = "CANARY-7f3a9c"


class CanaryDocs:
    """Appends a canary to every document that carries an injection payload."""

    name = "canary"

    def __init__(self, inner: Any) -> None:
        self.inner = inner

    def run(self, query_id: str, params: dict[str, object]) -> Any:
        result = self.inner.run(query_id, params)
        if query_id != "Q_SUBMISSION_DOCUMENTS":
            return result
        rows = [
            {**r, "text": f"{r['text']} {CANARY}"} if "ignore previous" in str(r["text"]).lower() else r
            for r in result.rows
        ]
        return result.model_copy(update={"rows": rows})


def test_p3_t12_blocked_segment_never_reaches_generate(
    offline_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    prompts: list[dict[str, Any]] = []

    def spy(prompt: str, **kwargs: Any) -> Any:
        prompts.append(
            {"prompt": prompt, "system": kwargs.get("system") or "", "purpose": kwargs.get("purpose")}
        )
        raise OfflineProvider("spy")

    monkeypatch.setattr(generator_module, "generate", spy)

    def factory(settings: Any, tracer: Any, submission: Any = None) -> Any:
        return CanaryDocs(get_backend(settings, tracer, submission))

    resp = run(
        load_example("example_3.json"),
        options=RunOptions(),
        deps=Deps(backend_factory=factory, generator=spy),
    )

    assert any(p["purpose"] == "extract" for p in prompts), "extraction never asked the generator"
    assert any("<vendor_text>" in p["prompt"] for p in prompts)
    for p in prompts:
        assert CANARY not in p["prompt"] and CANARY not in p["system"]
        assert "ignore previous instructions" not in p["prompt"].lower()

    bundle = Store().get(resp.output.case_id)
    assert bundle.decision.outcome == "ESCALATE"
    assert "UNTRUSTED_CONTENT_TAMPERING" in bundle.decision.outcome_reasons
    rows = trace(resp.log_file)
    assert any(r["agent_name"] == "ScoutGuard" and r["status"] == "blocked" for r in rows)
    assert all(CANARY not in r["input_summary"] + r["output_summary"] for r in rows)
