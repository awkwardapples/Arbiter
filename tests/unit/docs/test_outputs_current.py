"""P20-T2: no stale example output (C6). Runs on committed files."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.p20

ROOT = Path(__file__).resolve().parents[3]
OUTPUTS = ROOT / "output_examples"
P14A_MERGE = "228c52d"


def _documents() -> list[Path]:
    return sorted(OUTPUTS.glob("example_*_output.json")) + sorted(
        (OUTPUTS / "sample_mode").glob("example_*_output.json")
    )


def _root_documents() -> list[Path]:
    return sorted(OUTPUTS.glob("example_*_output.json"))


def test_p20_t2_no_stale_control_reason() -> None:
    """ALL_REQUIRED_CONTROLS_MET appears only in an APPROVE output (the bug Release 2 fixed)."""
    documents = _documents()
    assert len(documents) == 12, [path.name for path in documents]
    for path in documents:
        text = path.read_text(encoding="utf-8")
        outcome = json.loads(text)["response"]["output"]["decision"]
        if outcome != "APPROVE":
            assert "ALL_REQUIRED_CONTROLS_MET" not in text, f"{path.relative_to(ROOT)} ({outcome})"


def test_p20_t2_root_outputs_live_or_current_sample() -> None:
    """Each root output is live, or a byte copy of its current sample-mode output."""
    for path in _root_documents():
        header = json.loads(path.read_text(encoding="utf-8"))["header"]
        if header["mode"] == {"data": "zetaris", "llm": "meterless"}:
            continue
        sample = OUTPUTS / "sample_mode" / path.name
        assert sample.read_bytes() == path.read_bytes(), path.name


def _is_ancestor(ancestor: str, sha: str) -> bool | None:
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, sha],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode in (0, 1):
        return proc.returncode == 0
    return None


def test_p20_t2_root_outputs_made_after_p14a() -> None:
    """Every root output was made from a commit that descends from the P14-A merge."""
    if not (ROOT / ".git").exists():
        pytest.skip("no git history (archive checkout)")
    if _is_ancestor(P14A_MERGE, "HEAD") is None:
        pytest.skip("P14-A merge commit not in this clone (shallow history)")
    for path in _root_documents():
        sha = json.loads(path.read_text(encoding="utf-8"))["header"]["git_sha"]
        assert _is_ancestor(P14A_MERGE, sha) is True, f"{path.name}: {sha}"
