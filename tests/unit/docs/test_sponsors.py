"""P6-T7: sponsor claims point at real files and verbatim example-trace lines."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.p6

ROOT = Path(__file__).resolve().parents[3]

_PREFIXES = (
    "app/",
    "docs/",
    "eval/",
    "policy/",
    "zetaris/",
    "tests/",
    "vendor/",
    "scripts/",
    "data/",
    "logs/",
    "input_examples/",
    "output_examples/",
    "ui/",
    "sources/",
    ".cursor/",
    "AGENTS.md",
    "README.md",
    "metadata.json",
    "run.py",
    "requirements.txt",
    "Dockerfile",
    "docker-compose.yml",
    "pyproject.toml",
)

_FENCE = re.compile(r"```jsonl\n(.*?)```", re.DOTALL)
_TICK = re.compile(r"`([^`\n]+)`")


def test_p6_t7_files_and_trace_lines() -> None:
    """P6-T7: backtick paths exist, and every jsonl fence line is a real logs/examples line."""
    path = ROOT / "docs" / "SPONSORS.md"
    if not path.is_file():
        pytest.fail("docs/SPONSORS.md is missing")
    text = path.read_text(encoding="utf-8")
    missing = [token for token in _TICK.findall(text) if _is_path(token) and not _exists(token)]
    assert missing == []
    corpus = _trace_lines()
    assert corpus, "logs/examples has no trace lines"
    quoted: list[str] = []
    for block in _FENCE.findall(text):
        for line in block.splitlines():
            if line.strip():
                quoted.append(line)
    assert quoted, "docs/SPONSORS.md quotes no trace lines"
    absent = [line for line in quoted if line not in corpus]
    assert absent == []


def _is_path(raw: str) -> bool:
    raw = raw.strip().rstrip("/")
    return raw.startswith(_PREFIXES)


def _exists(raw: str) -> bool:
    return (ROOT / raw.strip().rstrip("/")).exists()


def _trace_lines() -> set[str]:
    lines: set[str] = set()
    for path in (ROOT / "logs" / "examples").glob("trace-*.jsonl"):
        lines.update(line for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return lines
