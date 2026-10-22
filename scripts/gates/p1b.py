"""Pass 1b gate: parity evidence or documented exceptions."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARITY = ROOT / "docs" / "passes" / "P1-B_parity.json"
REPORT = ROOT / "docs" / "passes" / "P1-B_REPORT.md"


def main() -> int:
    if PARITY.is_file():
        data = json.loads(PARITY.read_text(encoding="utf-8"))
        if data.get("all_green") is True:
            print("gate p1b: ok (parity all_green)")
            return 0
    if REPORT.is_file():
        text = REPORT.read_text(encoding="utf-8")
        if re.search(r"^##\s+Parity exceptions\s*$", text, re.MULTILINE | re.IGNORECASE):
            print("gate p1b: ok (parity exceptions documented)")
            return 0
    print("gate p1b: need all_green parity or Parity exceptions in P1-B_REPORT.md")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
