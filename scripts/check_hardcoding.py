#!/usr/bin/env python3
"""Integrity scan: no eval/example hardcoding in runtime paths."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_STRINGS = [
    "output_examples",
    "expected.json",
    "data/evals",
    "labels.jsonl",
    "splits.json",
    "truth_facts",
]
VND_RE = re.compile(r"VND-\d{4}")
CASE_RE = re.compile(r"CASE-\d+")
SCENARIO_RE = re.compile(r'"S\d\d"')

SCAN_DIRS = ["app", "sources", "ui"]
SKIP_UNDER_APP = {"cli"}


def scan_path(base: Path) -> list[str]:
    findings: list[str] = []
    if not base.exists():
        return findings
    for file in base.rglob("*"):
        if not file.is_file() or file.suffix not in {".py", ".yaml", ".yml", ".md"}:
            continue
        rel = file.relative_to(base)
        if base.name == "app" and len(rel.parts) > 0 and rel.parts[0] in SKIP_UNDER_APP:
            continue
        try:
            text = file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        display = f"{base.name}/{rel.as_posix()}" if base.name != "app" else rel.as_posix()
        for s in FORBIDDEN_STRINGS:
            if s in text:
                findings.append(f"{display}: forbidden string {s!r}")
        rel_posix = rel.as_posix()
        agent_policy_paths = (
            rel_posix.startswith("agents/"),
            rel_posix.startswith("policy/"),
            rel_posix.startswith("extract/"),
            rel_posix.startswith("memory/"),
            rel_posix == "orchestrator.py",
            rel_posix == "facts.py",
        )
        if base.name == "app" and any(agent_policy_paths):
            vnd = VND_RE.search(text)
            case = CASE_RE.search(text)
            if vnd:
                findings.append(f"{display}: forbidden vendor id literal {vnd.group(0)}")
            if case:
                findings.append(f"{display}: forbidden case id literal {case.group(0)}")
        if base.name == "app" and SCENARIO_RE.search(text):
            findings.append(f"{display}: forbidden scenario code literal")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hardcoding integrity check")
    parser.add_argument("roots", nargs="*", default=SCAN_DIRS)
    args = parser.parse_args(argv)

    findings: list[str] = []
    for root_name in args.roots:
        base = Path(root_name)
        if not base.is_absolute():
            base = ROOT / root_name
        findings.extend(scan_path(base))

    if findings:
        for f in findings:
            print(f)
        return 1
    print("hardcode-check: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
