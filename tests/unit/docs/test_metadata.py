"""P6-T2: metadata.json matches the playbook shape and the configured routes."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

LIVE = os.environ.get("ARBITER_LIVE_TESTS") == "1"

pytestmark = pytest.mark.p6

ROOT = Path(__file__).resolve().parents[3]


def test_p6_t2_check_metadata_passes() -> None:
    """P6-T2: check_metadata.py accepts the committed metadata.json."""
    script = ROOT / "scripts" / "check_metadata.py"
    if not script.is_file():
        pytest.fail("scripts/check_metadata.py is not implemented")
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    meta = json.loads((ROOT / "metadata.json").read_text(encoding="utf-8"))
    assert meta["models"] == ["meterless/fast", "nvidia/nemotron-3-super-120b-a12b"]
    assert meta["track"] == "Reasoning Architecture"


@pytest.mark.skipif(
    not LIVE,
    reason="offline run records no model ids; live trace assertion runs only with ARBITER_LIVE_TESTS=1",
)
def test_p6_t2_live_traces_contain_configured_ids() -> None:
    """P6-T2: a live run's logs/examples contain each metadata.models id."""
    meta = json.loads((ROOT / "metadata.json").read_text(encoding="utf-8"))
    corpus = _trace_corpus(ROOT)
    missing = [model for model in meta["models"] if model not in corpus]
    assert not missing, missing


def test_p6_t2_rejects_unknown_model_and_missing_file(tmp_path: Path) -> None:
    """P6-T2: a live trace that omits a model id, and a missing files path, are errors."""
    try:
        from scripts.check_metadata import validate
    except ImportError:
        pytest.fail("scripts/check_metadata.py is not implemented")

    (tmp_path / "README.md").write_text("Track: Reasoning Architecture\n", encoding="utf-8")
    (tmp_path / "logs" / "examples").mkdir(parents=True)
    (tmp_path / "logs" / "examples" / "trace-run-test.jsonl").write_text(
        json.dumps({"provider": "meterless", "model": "other-model"}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "eval" / "results" / "1").mkdir(parents=True)
    (tmp_path / "eval" / "results" / "1" / "env.json").write_text(
        json.dumps({"model_ids": []}),
        encoding="utf-8",
    )
    meta = {
        "schema": "arbiter-metadata/1",
        "project_name": "Arbiter",
        "description": "x",
        "track": "Reasoning Architecture",
        "team": {"name": "Arbiter", "members": [{"name": "A", "github": "a", "role": "Solo builder"}]},
        "repository": "https://example.invalid/arbiter",
        "demo_video": "",
        "slide_deck": "",
        "entry_points": {"api": "POST /run", "cli": "python run.py assess", "docker_sample_mode": "docker"},
        "agents": [],
        "sponsor_technologies": {
            "zetaris": {"files": ["missing/file.py"]},
            "meterless": {"files": [], "evidence": []},
            "nvidia": {"files": [], "models": ["nvidia/nemotron-3-super-120b-a12b"]},
            "cursor": {"files": []},
        },
        "models": ["no-such-model"],
        "data": {"synthetic": True, "public": []},
        "sample_mode": "sample",
        "pre_existing_components": [],
        "licence": "MIT",
    }
    (tmp_path / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    errors = validate(tmp_path)
    joined = "\n".join(errors)
    assert any("missing/file.py" in item for item in errors)
    assert "no-such-model" in joined
    assert not any("nemotron" in item for item in errors)


def test_p6_t2_offline_traces_permit_absent_model_ids(tmp_path: Path) -> None:
    """P6-T2: provider=offline records model=null, so configured ids need not appear."""
    try:
        from scripts.check_metadata import validate
    except ImportError:
        pytest.fail("scripts/check_metadata.py is not implemented")

    (tmp_path / "README.md").write_text("Track: Reasoning Architecture\n", encoding="utf-8")
    (tmp_path / "logs" / "examples").mkdir(parents=True)
    (tmp_path / "logs" / "examples" / "trace-run-offline.jsonl").write_text(
        json.dumps({"provider": "offline", "model": None}) + "\n",
        encoding="utf-8",
    )
    meta = {
        "schema": "arbiter-metadata/1",
        "project_name": "Arbiter",
        "description": "x",
        "track": "Reasoning Architecture",
        "team": {"name": "Arbiter", "members": [{"name": "A", "github": "a", "role": "Solo builder"}]},
        "repository": "https://example.invalid/arbiter",
        "demo_video": "",
        "slide_deck": "",
        "entry_points": {"api": "POST /run", "cli": "python run.py assess", "docker_sample_mode": "docker"},
        "agents": [],
        "sponsor_technologies": {
            "zetaris": {"files": []},
            "meterless": {"files": [], "evidence": []},
            "nvidia": {"files": [], "models": ["nvidia/nemotron-3-super-120b-a12b"]},
            "cursor": {"files": []},
        },
        "models": ["meterless/fast", "nvidia/nemotron-3-super-120b-a12b"],
        "data": {"synthetic": True, "public": []},
        "sample_mode": "sample",
        "pre_existing_components": [],
        "licence": "MIT",
    }
    (tmp_path / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    errors = validate(tmp_path)
    assert not any("logs/examples" in item for item in errors)


def _trace_corpus(root: Path) -> str:
    directory = root / "logs" / "examples"
    return "\n".join(
        path.read_text(encoding="utf-8", errors="replace") for path in sorted(directory.glob("trace-*.jsonl"))
    )
