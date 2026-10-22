"""Pass 1a gate: committed sample data present and under size budget."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 2 * 1024 * 1024


def main() -> int:
    systems = ROOT / "data" / "sample" / "systems"
    required = [
        "procurement_vendors.json",
        "procurement_vendor_aliases.json",
        "clm_contracts.json",
        "itsm_incidents.json",
        "grc_watchlist.json",
        "trust_submissions.json",
        "trust_answers.json",
        "trust_documents.json",
        "trust_components.json",
    ]
    missing = [f for f in required if not (systems / f).is_file()]
    if missing:
        print(f"gate p1a: missing system files: {missing}")
        return 1
    labels = ROOT / "data" / "evals" / "labels.jsonl"
    if not labels.is_file() or len(labels.read_text(encoding="utf-8").strip().splitlines()) < 32:
        print("gate p1a: labels.jsonl missing or incomplete")
        return 1
    total = 0
    for path in (ROOT / "data").rglob("*"):
        if path.is_file():
            total += path.stat().st_size
    for path in (ROOT / "input_examples").rglob("*"):
        if path.is_file():
            total += path.stat().st_size
    if total >= MAX_BYTES:
        print(f"gate p1a: data size {total} exceeds {MAX_BYTES}")
        return 1
    print("gate p1a: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
