"""P18-B gate: the web console checks (npm run check), dist freshness and, when possible, the smoke."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
BASE = os.environ.get("ARBITER_API_URL", "http://localhost:8000").rstrip("/")
SMOKE_HELP = f"""Smoke not run here. To run it:
  SAMPLE_MODE=true LLM_PROVIDER=offline python run.py serve
  python scripts/capture_web.py --smoke --base-url {BASE}"""


def _npm_check() -> int:
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if shutil.which("node") is None or npm is None:
        print("Node.js 20.19 or newer is required for `npm run check` in web/.", file=sys.stderr)
        return 1
    if not (WEB / "node_modules").is_dir():
        code = subprocess.run([npm, "ci"], cwd=WEB, check=False).returncode
        if code != 0:
            return code
    return subprocess.run([npm, "run", "check"], cwd=WEB, check=False).returncode


def _dist_fresh() -> int:
    cmd = [sys.executable, "-m", "pytest", "-q", "tests/unit/web/test_dist_fresh.py"]
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def _console_served() -> bool:
    # /health also probes Zetaris, so allow it time; retry because the sample-mode API can answer 500
    # while another request holds its database (reported to lane 18a).
    for attempt in range(3):
        try:
            health = httpx.get(f"{BASE}/health", timeout=20)
            console = httpx.get(f"{BASE}/console/", timeout=10)
        except httpx.HTTPError:
            return False
        if health.status_code == 200 and console.status_code == 200 and '<div id="root">' in console.text:
            return True
        time.sleep(1 + attempt)
    return False


def _smoke() -> int:
    if importlib.util.find_spec("playwright") is None or not _console_served():
        print(SMOKE_HELP)
        return 0
    cmd = [sys.executable, str(ROOT / "scripts" / "capture_web.py"), "--smoke", "--base-url", BASE]
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def main() -> int:
    for step in (_npm_check, _dist_fresh, _smoke):
        code = step()
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
