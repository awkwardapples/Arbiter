"""Assess one case. Same `orchestrator.run` path as POST /run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.orchestrator import RunOptions, run
from app.schemas.case import CaseInput


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("assess", help="Assess a vendor case from input JSON")
    p.add_argument("--input", required=True)
    p.add_argument("--sample", action="store_true")
    p.add_argument("--llm", choices=["auto", "meterless", "nvidia", "offline"], default=None)
    p.add_argument("--out")
    p.set_defaults(_handler=cmd_assess)


def cmd_assess(args: argparse.Namespace) -> None:
    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    case = CaseInput.model_validate(raw)
    response = run(
        case,
        options=RunOptions(sample_mode=True if args.sample else None, llm=args.llm),
    )
    text = response.model_dump_json()
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    if response.output is None:
        sys.exit(1)
