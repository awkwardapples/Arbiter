"""Shared helpers for P3 end-to-end tests (offline: DuckDB + deterministic fallbacks, temp var/)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.schemas.case import CaseInput

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "input_examples"
EXAMPLE_FILES = sorted(p.name for p in EXAMPLES.glob("example_*.json"))


@pytest.fixture
def offline_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SAMPLE_MODE", "true")
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    monkeypatch.setenv("ARBITER_MEMORY", "off")
    from app.llm.resolve import reset_cache

    reset_cache()
    return tmp_path


def load_example(name: str) -> CaseInput:
    return CaseInput.model_validate(json.loads((EXAMPLES / name).read_text(encoding="utf-8")))


def expected() -> dict[str, Any]:
    return json.loads((EXAMPLES / "expected.json").read_text(encoding="utf-8"))


def trace(log_file: str) -> list[dict[str, Any]]:
    lines = Path(log_file).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]
