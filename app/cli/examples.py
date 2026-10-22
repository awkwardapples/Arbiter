from __future__ import annotations

import argparse

from app.cli._stub import stub_command


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("examples", help="Generate output examples and traces")
    p.add_argument("--live", action="store_true")
    p.set_defaults(_handler=lambda _a: stub_command("P6"))
