"""Export a stored decision dossier."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.dossier import render
from app.store import Store


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("dossier", help="Export a decision dossier")
    parser.add_argument("case")
    parser.add_argument("--format", choices=("md", "html"), default="md")
    parser.add_argument("--out")
    parser.set_defaults(_handler=_export)


def _export(args: argparse.Namespace) -> None:
    text = render(Store().get(args.case), args.format)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        return
    sys.stdout.write(text)
