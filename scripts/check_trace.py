#!/usr/bin/env python3
"""Validate trace JSONL files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.schemas.trace import TraceEvent  # noqa: E402
from scripts.secret_patterns import contains_secret  # noqa: E402


def validate_file(path: Path, *, require_collaboration: bool, require_live: bool) -> list[str]:
    errors: list[str] = []
    agents: set[str] = set()
    has_collab = False
    has_zetaris = False
    has_meterless = False
    has_model_call = False
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        if contains_secret(line):
            errors.append(f"{path}:{line_no} contains a secret pattern")
            continue
        try:
            data = json.loads(line)
            evt = TraceEvent.model_validate(data)
        except Exception as exc:
            errors.append(f"{path}:{line_no} invalid TraceEvent: {exc}")
            continue
        agents.add(evt.agent_name)
        collab_status = {"needs_revision", "retrying", "fallback", "escalated"}
        if evt.status in collab_status or evt.action == "request_replan":
            has_collab = True
        if evt.backend == "zetaris":
            has_zetaris = True
        if evt.provider == "meterless":
            has_meterless = True
            # A fallback event also carries provider=meterless; only a completed call proves live use.
            if evt.status == "success" and evt.model:
                has_model_call = True
        if "status" not in data:
            errors.append(f"{path}:{line_no} missing status")

    if require_collaboration:
        if len(agents) < 2:
            errors.append(f"{path}: fewer than 2 distinct agents")
        if not has_collab:
            errors.append(f"{path}: no collaboration status event")
    if require_live:
        if not has_zetaris:
            errors.append(f"{path}: no backend=zetaris event")
        if not has_meterless:
            errors.append(f"{path}: no provider=meterless event")
        elif not has_model_call:
            errors.append(f"{path}: no successful provider=meterless model call")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate trace JSONL")
    parser.add_argument("paths", nargs="*", default=[str(ROOT / "logs")])
    parser.add_argument("--require-collaboration", action="store_true")
    parser.add_argument("--require-live", action="store_true")
    args = parser.parse_args(argv)

    all_errors: list[str] = []
    for raw in args.paths:
        p = Path(raw)
        files = sorted(p.glob("trace-*.jsonl")) if p.is_dir() else [p]
        for f in files:
            if f.is_file():
                all_errors.extend(
                    validate_file(
                        f,
                        require_collaboration=args.require_collaboration,
                        require_live=args.require_live,
                    )
                )

    if all_errors:
        for e in all_errors:
            print(e)
        return 1
    print("trace-check: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
