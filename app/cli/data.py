from __future__ import annotations

import argparse

from app.cli._stub import add_stub, stub_command


def register(sub: argparse._SubParsersAction) -> None:
    gen = sub.add_parser("generate-data", help="Generate synthetic enterprise data")
    gen.add_argument("--seed", type=int, default=2026)
    gen.add_argument("--as-of", type=str, default="2026-10-26")
    gen.add_argument("--refresh-kev", action="store_true")
    gen.set_defaults(_handler=lambda _a: stub_command("P1-A"))

    add_stub(sub, "sources", "P1-A", help_text="Run the enterprise systems simulator")
