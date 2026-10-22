from __future__ import annotations

import argparse

from app.cli._stub import stub_command


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("guard-eval", help="Run Scout guard evaluation")
    p.add_argument("--set", choices=["scout", "domain", "all"], default="all")
    p.add_argument("--no-model", action="store_true")
    p.set_defaults(_handler=lambda _a: stub_command("P2-D"))
