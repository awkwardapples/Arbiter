"""P18-D gate: 18d acceptance tests exist with recorded fixtures, then npm run check and dist freshness."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
TEST_IDS = [f"P18D-T{n}" for n in range(1, 8)]
# Payloads recorded from a real sample-mode API by web/scripts/record-fixtures.mjs --lane 18d.
FIXTURES = [
    "web/src/features/intake/__tests__/fixtures/run_started.json",
    "web/src/features/usl/__tests__/fixtures/agents.json",
    "web/src/features/memory/__tests__/fixtures/review_submitted.json",
    "web/src/features/intake/__tests__/fixtures/questions.json",
    "web/src/features/usl/__tests__/fixtures/usl_model.json",
    "web/src/features/usl/__tests__/fixtures/registry_queries.json",
    "web/src/features/usl/__tests__/fixtures/evidence_parity.json",
    "web/src/features/usl/__tests__/fixtures/health.json",
    "web/src/features/usl/__tests__/fixtures/evidence_nightshift.json",
    "web/src/features/usl/__tests__/fixtures/case_trace.json",
    "web/src/features/usl/__tests__/fixtures/live_recording.json",
    "web/src/features/audit/__tests__/fixtures/audit_recent.json",
    "web/src/features/audit/__tests__/fixtures/audit_verify.json",
    "web/src/features/evaluation/__tests__/fixtures/eval_latest.json",
    "web/src/features/evaluation/__tests__/fixtures/not_found.json",
    "web/src/features/evaluation/__tests__/fixtures/cases.json",
    "web/src/features/memory/__tests__/fixtures/precedents.json",
    "web/src/features/memory/__tests__/fixtures/review_dry_run.json",
]
TEST_ROOTS = [WEB / "src" / "features", WEB / "src" / "pages"]


def _tests_present() -> int:
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for root in TEST_ROOTS
        if root.is_dir()
        for path in root.rglob("*.test.tsx")
    )
    missing = [tid for tid in TEST_IDS if tid not in sources]
    absent = [rel for rel in FIXTURES if not (ROOT / rel).is_file()]
    for tid in missing:
        print(f"p18d gate: no Vitest test named {tid}", file=sys.stderr)
    for rel in absent:
        print(f"p18d gate: recorded fixture missing: {rel}", file=sys.stderr)
    return 1 if missing or absent else 0


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


def main() -> int:
    for step in (_tests_present, _npm_check, _dist_fresh):
        code = step()
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
