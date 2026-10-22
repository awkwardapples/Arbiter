"""Pass 4a gate: memory session smoke."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    py = sys.executable
    proc = subprocess.run(
        [py, str(ROOT / "run.py"), "demo-session", "--reset", "--yes"],
        cwd=ROOT,
    )
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
