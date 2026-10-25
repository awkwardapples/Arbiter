"""P20 gate: metadata, the compiled usage log, live traces, and a current root of output_examples/."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIVE_MODE = {"data": "zetaris", "llm": "meterless"}


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
    outputs = ROOT / "output_examples"
    root = sorted(outputs.glob("*.json"))
    if [path.name for path in root] != [f"example_{n}_output.json" for n in range(1, 7)]:
        errors.append(f"output_examples/ root holds {[path.name for path in root]}, not examples 1-6")
    for path in root:
        header = json.loads(path.read_text(encoding="utf-8"))["header"]
        if header["mode"] == LIVE_MODE:
            if not (ROOT / "logs" / "examples" / "live" / f"trace-{header['run_id']}.jsonl").is_file():
                errors.append(f"{path.name}: live trace for {header['run_id']} not committed")
        elif (outputs / "sample_mode" / path.name).read_bytes() != path.read_bytes():
            errors.append(f"{path.name}: neither live nor a copy of sample_mode/{path.name}")
    for item in errors:
        print(item)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
