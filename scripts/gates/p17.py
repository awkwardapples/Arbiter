"""P17 gate: metadata, live traces, failed live attempts and the compiled usage log."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    for script in (["check_metadata.py"], ["compile_cursor_usage.py", "--check"]):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script[0]), *script[1:]], cwd=ROOT, check=False
        )
        if proc.returncode != 0:
            return int(proc.returncode)
    from scripts.check_trace import validate_file

    errors: list[str] = []
    live = sorted((ROOT / "logs" / "examples" / "live").glob("trace-*.jsonl"))
    if not live:
        errors.append("no live traces in logs/examples/live/")
    for path in live:
        errors.extend(validate_file(path, require_collaboration=True, require_live=True))
    # A failed live attempt must not pass as live evidence.
    for path in sorted((ROOT / "logs" / "examples" / "live_failed").glob("trace-*.jsonl")):
        if not validate_file(path, require_collaboration=False, require_live=True):
            errors.append(f"{path.name} passes --require-live but is a failed attempt")
    for item in errors:
        print(item)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
