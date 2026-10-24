"""P6-T2: metadata.json matches the playbook shape and the configured routes."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

LIVE = os.environ.get("ARBITER_LIVE_TESTS") == "1"

pytestmark = pytest.mark.p6

ROOT = Path(__file__).resolve().parents[3]

SUPER_VL = "nvidia/nemotron-3.5-super-vl-120b-a12b"
LIGHTNING = "nvidia/nemotron-3.5-lightning-30b-a3b"
NOT_ENTITLED = "nvidia/nemotron-3-super-120b-a12b"


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
    # P17 retarget: models are the Nemotron ids observed in live traces, not the configured settings.
    assert meta["models"] == [SUPER_VL, LIGHTNING]
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
    paths = sorted(directory.glob("trace-*.jsonl")) + sorted((directory / "live").glob("trace-*.jsonl"))
    return "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in paths)


def _receipt_lines(path: Path) -> list[dict]:
    """Successful Nightshift model calls in a committed trace, or the two lanes of the proof file."""
    if path.suffix == ".json":
        proof = json.loads(path.read_text(encoding="utf-8"))
        return [
            {"model": proof[lane]["routed_model"], "receipt_id": proof[lane]["receipt_id"]}
            for lane in ("fast", "deep")
        ]
    found: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("provider") == "meterless" and event.get("status") == "success" and event.get("model"):
            found.append(
                {"model": event["model"], "receipt_id": (event.get("provider_meta") or {}).get("receipt_id")}
            )
    return found


@pytest.mark.p17
def test_p17_t6_models_were_served_live() -> None:
    """P17-T6: each metadata model id has a Nightshift receipt in a committed live trace or the proof."""
    meta = json.loads((ROOT / "metadata.json").read_text(encoding="utf-8"))
    assert sorted(meta["models"]) == sorted(meta["sponsor_technologies"]["nvidia"]["models"])
    evidence = meta["model_evidence"]
    for model in meta["models"]:
        entries = evidence.get(model)
        assert entries, model
        for entry in entries:
            rel = entry["file"]
            assert rel.startswith(
                ("logs/examples/live/", "eval/results_live/", "docs/evidence/nightshift_proof.json")
            ), rel
            served = _receipt_lines(ROOT / rel)
            assert {"model": model, "receipt_id": entry["receipt_id"]} in served, entry
    live_models = set()
    for path in (ROOT / "logs" / "examples" / "live").glob("trace-*.jsonl"):
        live_models.update(item["model"] for item in _receipt_lines(path))
    assert SUPER_VL in live_models
    assert any(e["file"].startswith("logs/examples/live/") for e in evidence[SUPER_VL])


@pytest.mark.p17
def test_p17_t7_deep_lane_claim_corrected_in_metadata() -> None:
    """P17-T7: the not-entitled Super 3 120B id never appears in metadata.json; no other model family does."""
    raw = (ROOT / "metadata.json").read_text(encoding="utf-8")
    assert NOT_ENTITLED not in raw
    assert not re.search(r"deepseek|llama|qwen|mistral|gemini|gpt-\d", raw, re.IGNORECASE)
    meta = json.loads(raw)
    assert "nightshift_deviations.md" in meta["sponsor_technologies"]["nvidia"]["access"]
    assert meta["lane_deviation"]["file"] == "docs/evidence/nightshift_deviations.md"


@pytest.mark.p17
def test_p17_t6_check_metadata_reads_live_traces(tmp_path: Path) -> None:
    """P17-T6: check_metadata.py matches models against logs/examples/live/ too."""
    from scripts.check_metadata import validate

    (tmp_path / "README.md").write_text("Track: Reasoning Architecture\n", encoding="utf-8")
    live = tmp_path / "logs" / "examples" / "live"
    live.mkdir(parents=True)
    (live / "trace-run-x.jsonl").write_text(
        json.dumps({"provider": "meterless", "status": "success", "model": SUPER_VL}) + "\n", encoding="utf-8"
    )
    meta = json.loads((ROOT / "metadata.json").read_text(encoding="utf-8"))
    meta["sponsor_technologies"] = {k: {"files": []} for k in ("zetaris", "meterless", "nvidia", "cursor")}
    meta["models"] = [SUPER_VL]
    (tmp_path / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    assert validate(tmp_path) == []
    meta["models"] = [SUPER_VL, "nvidia/not-served"]
    (tmp_path / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    assert any("nvidia/not-served" in item for item in validate(tmp_path))
