from __future__ import annotations

import argparse
import json
import sys

from app.audit.chain import AuditChain
from app.audit.replay import replay


def register(sub: argparse._SubParsersAction) -> None:
    rep = sub.add_parser("replay", help="Replay a case decision")
    rep.add_argument("case")
    rep.set_defaults(_handler=_replay)

    sub.add_parser("audit-verify", help="Verify the audit hash chain").set_defaults(_handler=_verify)


def _replay(args: argparse.Namespace) -> None:
    result = replay(args.case)
    print(result.model_dump_json())
    if not result.match:
        sys.exit(1)


def _verify(_args: argparse.Namespace) -> None:
    ok, seq = AuditChain().verify()
    print(json.dumps({"ok": ok, "first_bad_seq": seq}))
    if not ok:
        sys.exit(1)
