from __future__ import annotations

import argparse
import sys


def stub_command(lane: str) -> None:
    print(f"not implemented yet (lane {lane})")
    sys.exit(3)


def add_stub(sub: argparse._SubParsersAction, name: str, lane: str, *, help_text: str = "") -> None:
    parser = sub.add_parser(name, help=help_text or f"{name} (stub)")
    parser.set_defaults(_handler=lambda _a: stub_command(lane))
