from __future__ import annotations

import argparse

from app.cli._stub import stub_command


def register(sub: argparse._SubParsersAction) -> None:
    rev = sub.add_parser("review", help="Submit a human review for a case")
    rev.add_argument("case")
    rev.add_argument("--input", required=True)
    rev.set_defaults(_handler=lambda _a: stub_command("P4-A"))

    demo = sub.add_parser("demo-session", help="Run a guided demo session")
    demo.add_argument("--live", action="store_true")
    demo.add_argument("--reset", action="store_true")
    demo.add_argument("--yes", action="store_true")
    demo.set_defaults(_handler=lambda _a: stub_command("P4-A"))
