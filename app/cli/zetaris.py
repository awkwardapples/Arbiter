from __future__ import annotations

import argparse

from app.cli._stub import stub_command


def register(sub: argparse._SubParsersAction) -> None:
    z = sub.add_parser("zetaris", help="Zetaris onboarding and parity")
    zsub = z.add_subparsers(dest="zetaris_cmd", required=True)
    for name in ("onboard", "parity", "status"):
        p = zsub.add_parser(name)
        if name == "onboard":
            p.add_argument("--dry-run", action="store_true")
            p.add_argument("--skip-exists", action="store_true")
            p.add_argument("--only", choices=["01", "02", "03"])
            p.add_argument("--yes", action="store_true")
        p.set_defaults(_handler=lambda _a: stub_command("P1-B"))
