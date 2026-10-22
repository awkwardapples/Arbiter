"""P4-T17: CI builds the repo Dockerfile; the container smoke is opt-in."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.p4b

ROOT = Path(__file__).resolve().parents[3]


def test_p4_t17_ci_builds_from_dockerfile() -> None:
    """P4-T17: the GitHub docker job builds this repo's Dockerfile and does not pull a tag."""
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "docker:" in text
    assert "docker build" in text
    assert "docker pull" not in text


def test_p4_t17_docker_sample_smoke() -> None:
    """P4-T17: local image smoke. Skipped unless ARBITER_DOCKER_TESTS=1 and docker is usable."""
    if os.environ.get("ARBITER_DOCKER_TESTS") != "1":
        pytest.skip("local docker smoke is opt-in via ARBITER_DOCKER_TESTS=1")
    if os.environ.get("DOCKER") == "0" or shutil.which("docker") is None:
        pytest.skip("docker smoke skipped because DOCKER=0 or docker is not on PATH")

    image = "arbiter-p4b-smoke"
    build = subprocess.run(
        ["docker", "build", "-f", str(ROOT / "Dockerfile"), "-t", image, str(ROOT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert build.returncode == 0, build.stderr[-2000:]
    name = "arbiter-p4b-smoke-run"
    subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)
    run = subprocess.run(
        ["docker", "run", "-d", "--name", name, "-p", "8000:8000", "-e", "SAMPLE_MODE=true", image],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    try:
        _wait_and_assert_examples()
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)


def _wait_and_assert_examples() -> None:
    import json
    import time
    import urllib.request

    deadline = time.monotonic() + 60
    health = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=3) as resp:
                health = resp.status
                if health == 200:
                    break
        except Exception:
            time.sleep(1)
    assert health == 200
    expected = json.loads((ROOT / "input_examples" / "expected.json").read_text(encoding="utf-8"))
    for name, spec in sorted(expected.items()):
        payload = (ROOT / "input_examples" / name).read_bytes()
        request = urllib.request.Request(
            "http://127.0.0.1:8000/run",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        assert body["output"]["decision"] == spec["outcome"]
