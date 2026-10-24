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
    # P17 retarget: live traces sit in logs/examples/live/ (P15); failed live attempts are not evidence.
    lines: set[str] = set()
    for path in (ROOT / "logs" / "examples").rglob("trace-*.jsonl"):
        if "live_failed" in path.parts:
            continue
        lines.update(line for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return lines


SUPER_VL = "nvidia/nemotron-3.5-super-vl-120b-a12b"
LIGHTNING = "nvidia/nemotron-3.5-lightning-30b-a3b"
NOT_ENTITLED = "nvidia/nemotron-3-super-120b-a12b"
_OTHER_MODELS = re.compile(r"deepseek|llama|qwen|mistral|gemini|gpt-\d", re.IGNORECASE)
_NVIDIA_ID = re.compile(r"nvidia/[a-z0-9][a-z0-9.\-]*[a-z0-9]")


@pytest.mark.p17
@pytest.mark.parametrize(
    "rel",
    [
        "README.md",
        "docs/SPONSORS.md",
        "docs/SLIDES.md",
        "docs/DEMO_SCRIPT.md",
        "docs/QA_PREP.md",
        "docs/IMPACT.md",
    ],
)
def test_p17_t7_only_models_that_ran(rel: str) -> None:
    """P17-T7: only Super VL and Lightning are named; Super 3 120B only where it is called not entitled."""
    text = (ROOT / rel).read_text(encoding="utf-8")
    assert not _OTHER_MODELS.search(text), rel
    for line in text.splitlines():
        for model in _NVIDIA_ID.findall(line):
            if model == NOT_ENTITLED:
                assert re.search(r"not entitled|404", line), (rel, line)
            else:
                assert model.startswith((SUPER_VL, LIGHTNING)), (rel, model)


@pytest.mark.p17
@pytest.mark.parametrize("rel", ["README.md", "docs/SPONSORS.md"])
def test_p17_t7_deep_lane_is_super_vl_with_deviation(rel: str) -> None:
    """P17-T7: the deep lane is stated as Super VL, with the coercion and the vendor acknowledgement."""
    text = (ROOT / rel).read_text(encoding="utf-8")
    deep_rows = [
        line for line in text.splitlines() if line.startswith("|") and "deep" in line and "nvidia/" in line
    ]
    assert deep_rows, rel
    assert all(SUPER_VL in line for line in deep_rows), deep_rows
    assert "docs/evidence/nightshift_deviations.md" in text
    assert "docs/evidence/nightshift_proof.json" in text
    assert "auto" in text and "coerce" in text
    assert re.search(r"acknowledged", text), rel
    assert "Sunday" in text, rel
    assert NOT_ENTITLED in text, "the correction must name the model that is not entitled"


@pytest.mark.p17
def test_p17_t7_sponsors_nemotron_section() -> None:
    """P17-T7: SPONSORS lists each LLM step with its lane, served model and receipt."""
    text = (ROOT / "docs" / "SPONSORS.md").read_text(encoding="utf-8")
    assert "Our agents do real work on Nemotron" in text
    section = text.split("Our agents do real work on Nemotron", 1)[1].split("\n## ", 1)[0]
    for step in ("plan", "extract", "critique", "challenge", "brief"):
        assert re.search(rf"\|\s*{step}", section, re.IGNORECASE), step
    assert re.findall(r"rcpt_req_[a-z0-9]+", section)
