"""P6-T2: metadata.json matches the playbook shape and the latest eval env."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

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
    env = _latest_env()
    assert meta["models"] == env.get("model_ids", [])
    assert meta["track"] == "Reasoning Architecture"


def test_p6_t2_rejects_unknown_model_and_missing_file(tmp_path: Path) -> None:
    """P6-T2: a missing files path and a model id absent from traces are errors."""
    try:
        from scripts.check_metadata import validate
    except ImportError:
        pytest.fail("scripts/check_metadata.py is not implemented")

    (tmp_path / "README.md").write_text("Track: Reasoning Architecture\n", encoding="utf-8")
    (tmp_path / "logs" / "examples").mkdir(parents=True)
    (tmp_path / "logs" / "examples" / "trace-run-test.jsonl").write_text("{}\n", encoding="utf-8")
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


def _latest_env() -> dict:
    found = sorted((ROOT / "eval" / "results").glob("*/env.json"))
    assert found, "eval env.json is missing"
    payload = json.loads(found[-1].read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload
