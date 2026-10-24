"""P6 gate: metadata and example traces."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_metadata.py")],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return int(proc.returncode)
    from scripts.check_trace import validate_file

    errors: list[str] = []
    for path in sorted((ROOT / "output_examples").glob("example_*_output.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        header = document["header"]
        live = _says_live(header)  # P15: live traces live in logs/examples/live/
        trace = ROOT / "logs" / "examples" / ("live" if live else "") / f"trace-{header['run_id']}.jsonl"
        if not trace.is_file():
            errors.append(f"missing {trace.name}")
            continue
        errors.extend(validate_file(trace, require_collaboration=True, require_live=live))
    if errors:
        for item in errors:
            print(item)
        return 1
    return 0


def _says_live(header: dict) -> bool:
    mode = header.get("mode")
    return isinstance(mode, dict) and mode.get("llm") == "meterless" and mode.get("data") == "zetaris"


if __name__ == "__main__":
    raise SystemExit(main())
