from __future__ import annotations

import argparse

from app.cli._stub import stub_command


def register(sub: argparse._SubParsersAction) -> None:
    rep = sub.add_parser("replay", help="Replay a case decision")
    rep.add_argument("case")
    rep.set_defaults(_handler=lambda _a: stub_command("P4-B"))

    sub.add_parser("audit-verify", help="Verify the audit hash chain").set_defaults(
        _handler=lambda _a: stub_command("P4-B")
    )
