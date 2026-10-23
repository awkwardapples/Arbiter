#!/usr/bin/env python3
"""Arbiter CLI dispatcher (master spec §8.11)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.cli import (  # noqa: E402
    audit,
    data,
    dossier,
    eval,
    examples,
    guard,
    llm,
    meta,
    review,
    run_case,
    zetaris,
)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        argv = ["serve"]
    parser = argparse.ArgumentParser(prog="run.py", description="Arbiter command-line interface")
    sub = parser.add_subparsers(dest="command")

    meta.register(sub)
    data.register(sub)
    zetaris.register(sub)
    llm.register(sub)
    guard.register(sub)
    run_case.register(sub)
    review.register(sub)
    audit.register(sub)
    dossier.register(sub)
    eval.register(sub)
    examples.register(sub)

    args = parser.parse_args(argv)
    if not hasattr(args, "_handler"):
        parser.print_help()
        return 2
    args._handler(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
