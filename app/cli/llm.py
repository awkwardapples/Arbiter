from __future__ import annotations

import argparse

from app.cli._stub import stub_command


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("llm", help="LLM provider utilities")
    sub2 = p.add_subparsers(dest="llm_cmd", required=True)
    ping = sub2.add_parser("ping")
    ping.add_argument("--route", choices=["fast", "deep"], default="fast")
    ping.set_defaults(_handler=lambda _a: stub_command("P2-B"))
