"""Pass 0 gate: CI workflow present with required steps."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CI = ROOT / ".github" / "workflows" / "ci.yml"
REQUIRED = ("setup", "lint", "test", "secret-scan", "hardcode-check")


def main() -> int:
    if not CI.is_file():
        print("gate p0: missing .github/workflows/ci.yml")
        return 1
    text = CI.read_text(encoding="utf-8")
    missing = [s for s in REQUIRED if s not in text]
    if missing:
        print(f"gate p0: ci.yml missing steps: {missing}")
        return 1
    print("gate p0: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
