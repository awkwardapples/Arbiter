"""P18-A gate: no committed trace is edited; new events appear only in new runs."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRACE_DIRS = ("logs/examples", "eval/results_live")


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)


def _base() -> str | None:
    for ref in ("main", "origin/main"):
        if _git("rev-parse", "--verify", "--quiet", ref).returncode == 0:
            return ref
    return None


def main() -> int:
    base = _base()
    if base is None:
        print("p18a gate: no main branch to compare against; skipped")
        return 0
    # Committed on this branch since it left main, plus anything still uncommitted.
    changed = _git("diff", "--name-only", f"{base}...HEAD", "--", *TRACE_DIRS).stdout.split()
    changed += _git("diff", "--name-only", "HEAD", "--", *TRACE_DIRS).stdout.split()
    edited = sorted({path for path in changed if path.endswith(".jsonl")})
    for path in edited:
        print(f"committed trace changed: {path}")
    return 1 if edited else 0


if __name__ == "__main__":
    raise SystemExit(main())
