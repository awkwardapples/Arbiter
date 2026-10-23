"""Pass 13 gate: USL parity is green and the judging note has sections 1–7."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARITY = ROOT / "docs" / "passes" / "P1-B_parity.json"
DOC = ROOT / "docs" / "ZETARIS_USL.md"


def main() -> int:
    if not PARITY.is_file():
        print("gate p13: missing docs/passes/P1-B_parity.json")
        return 1
    data = json.loads(PARITY.read_text(encoding="utf-8"))
    if data.get("all_green") is not True or data.get("query_layer") != "usl":
        print("gate p13: need all_green true and query_layer usl")
        return 1
    if not DOC.is_file():
        print("gate p13: missing docs/ZETARIS_USL.md")
        return 1
    text = DOC.read_text(encoding="utf-8")
    missing = [n for n in range(1, 8) if f"## {n}." not in text]
    if missing:
        print(f"gate p13: docs/ZETARIS_USL.md missing sections {missing}")
        return 1
    print("gate p13: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
