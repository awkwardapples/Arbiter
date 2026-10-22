from __future__ import annotations

import argparse

from app.cli._stub import stub_command


def register(sub: argparse._SubParsersAction) -> None:
    ev = sub.add_parser("eval", help="Run the evaluation harness")
    ev.add_argument("--split")
    ev.add_argument("--systems")
    ev.add_argument("--consistency")
    ev.add_argument("--llm")
    ev.add_argument("--publish", action="store_true")
    ev.add_argument("--session", action="store_true")
    ev.set_defaults(_handler=lambda _a: stub_command("P5-B"))

    sub.add_parser("calibrate", help="Calibrate confidence gates").set_defaults(
        _handler=lambda _a: stub_command("P5-B")
    )
