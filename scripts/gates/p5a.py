"""P5-A gate: reviewer console modules present."""

from __future__ import annotations

import os
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    required = (
        root / "ui" / "client.py",
        root / "ui" / "app.py",
        root / "ui" / "components.py",
        root / "ui" / "timeline.py",
        root / "ui" / "validation.py",
    )
    missing = [p for p in required if not p.is_file()]
    if missing:
        for path in missing:
            print(f"missing {path}")
        return 1
    if os.environ.get("P5A_REQUIRE_SCREENSHOTS") == "1":
        shots = list((root / "docs" / "img").glob("ui_*.png"))
        if not shots:
            print("P5A_REQUIRE_SCREENSHOTS=1 but no docs/img/ui_*.png")
            return 1
    return 0
