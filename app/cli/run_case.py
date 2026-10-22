from __future__ import annotations

import argparse

from app.cli._stub import stub_command


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("assess", help="Assess a vendor case from input JSON")
    p.add_argument("--input", required=True)
    p.add_argument("--sample", action="store_true")
    p.add_argument("--llm", choices=["auto", "meterless", "nvidia", "offline"], default="auto")
    p.add_argument("--out")
    p.set_defaults(_handler=lambda _a: stub_command("P3"))
