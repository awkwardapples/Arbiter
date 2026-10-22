"""Pass 5b gate: offline inline split on the DuckDB mirror."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    py = sys.executable
    with tempfile.TemporaryDirectory(prefix="arbiter-p5b-gate-") as tmp:
        env = os.environ.copy()
        env["SAMPLE_MODE"] = "true"
        env["LLM_PROVIDER"] = "offline"
        env["ARBITER_MEMORY"] = "off"
        env["ARBITER_EVAL_ROOT"] = tmp
        proc = subprocess.run(
            [
                py,
                str(ROOT / "run.py"),
                "eval",
                "--split",
                "inline",
                "--systems",
                "arbiter_offline,baseline",
                "--llm",
                "offline",
            ],
            cwd=ROOT,
            env=env,
            check=False,
        )
        if proc.returncode != 0:
            return int(proc.returncode)
        summaries = list(Path(tmp).glob("*/summary.json"))
        if len(summaries) != 1:
            print("gate p5b: expected one summary.json", file=sys.stderr)
            return 1
        summary = json.loads(summaries[0].read_text(encoding="utf-8"))
        if summary.get("splits") != ["inline"]:
            print("gate p5b: inline split was not the one that ran", file=sys.stderr)
            return 1
        from eval.metrics import METRIC_KEYS

        for name, block in (summary.get("systems") or {}).items():
            missing = [key for key in METRIC_KEYS if key not in block]
            if missing:
                print(f"gate p5b: {name} missing {missing}", file=sys.stderr)
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
