from __future__ import annotations

import argparse
import sys

from app.config import get_settings


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
        p.set_defaults(_handler=_dispatch)


def _dispatch(args: argparse.Namespace) -> None:
    settings = get_settings()
    if args.zetaris_cmd == "status":
        import json

        from app.data.zetaris import status

        print(json.dumps(status(settings), indent=2))
        return
    if args.zetaris_cmd == "onboard":
        from zetaris.onboard import run_onboard

        code = run_onboard(
            settings,
            dry_run=args.dry_run,
            skip_exists=args.skip_exists,
            only=args.only,
            yes=args.yes,
        )
        sys.exit(code)
    if args.zetaris_cmd == "parity":
        from zetaris.parity import run_parity

        report = run_parity(settings)
        print(f"all_green={report.get('all_green')}")
        sys.exit(0 if report.get("all_green") else 1)
