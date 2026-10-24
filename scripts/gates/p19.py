"""P19 gate: the lane's report and usage note exist, and the Evaluation page reads no fixed path."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    errors: list[str] = []
    for name in ("docs/passes/P19_REPORT.md", "docs/cursor-usage/P19.md", ".streamlit/config.toml"):
        if not (ROOT / name).is_file():
            errors.append(f"missing {name}")
    if "eval/results/" in (ROOT / "ui" / "screens.py").read_text(encoding="utf-8"):
        errors.append("ui/screens.py still names an eval/results path")
    for item in errors:
        print(item)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
