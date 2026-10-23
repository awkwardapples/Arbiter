#!/usr/bin/env python3
"""Scan the tree for accidental secret commits."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.secret_patterns import (
    SECRET_REGEXES,
    is_placeholder_value,
    mask_secret_value,
)

SKIP_DIRS = {".git", ".venv", "var", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache"}
SKIP_FILES = {".env", ".env.local"}


def _load_allowlist(path: Path) -> list[str]:
    if not path.is_file():
        return []
    globs: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        globs.append(line)
    return globs


def _allowed(rel: str, allow_globs: list[str]) -> bool:
    from fnmatch import fnmatch

    return any(fnmatch(rel, g) for g in allow_globs)


def scan_file(path: Path, allow_globs: list[str]) -> list[tuple[int, str, str]]:
    if path.name in SKIP_FILES:
        return []
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:
        rel = path.as_posix()
    if _allowed(rel, allow_globs):
        return []
    findings: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return findings
    for line_no, line in enumerate(text.splitlines(), start=1):
        for name, pattern in SECRET_REGEXES:
            m = pattern.search(line)
            if not m:
                continue
            if name == "assignment" and m.lastindex and m.lastindex >= 2:
                val = m.group(2)
                if is_placeholder_value(val):
                    continue
            findings.append((line_no, name, mask_secret_value(m.group(0)[:32])))
    return findings


def scan_tree(paths: list[Path], allow_globs: list[str]) -> list[str]:
    messages: list[str] = []
    for base in paths:
        files = [base] if base.is_file() else [p for p in base.rglob("*") if p.is_file()]
        for f in files:
            if any(part in SKIP_DIRS for part in f.parts):
                continue
            for line_no, kind, preview in scan_file(f, allow_globs):
                try:
                    rel = f.relative_to(ROOT).as_posix()
                except ValueError:
                    rel = f.name if f.parent == base else f.as_posix()
                messages.append(f"{rel}:{line_no} [{kind}] {preview}")
    return messages


def scan_history(allow_globs: list[str] | None = None) -> list[str]:
    allow = allow_globs or []
    proc = subprocess.run(
        ["git", "log", "-p", "--no-color"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    messages: list[str] = []
    current_file = "git-history"
    for line in proc.stdout.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue
        if _allowed(current_file, allow):
            continue
        for name, pattern in SECRET_REGEXES:
            m = pattern.search(line)
            if not m:
                continue
            if name == "assignment" and m.lastindex and m.lastindex >= 2 and is_placeholder_value(m.group(2)):
                continue
            messages.append(f"{current_file}:history [{name}] {mask_secret_value(m.group(0)[:32])}")
    return messages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan for secret patterns")
    parser.add_argument("paths", nargs="*", default=[str(ROOT)])
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args(argv)

    allow = _load_allowlist(ROOT / ".secrets-allowlist")
    paths = [Path(p).resolve() for p in args.paths]
    messages = scan_tree(paths, allow)
    if args.history:
        messages.extend(scan_history(allow))

    if messages:
        for msg in messages:
            print(msg)
        return 1
    print("secret-scan: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
