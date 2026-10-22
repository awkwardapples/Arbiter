from __future__ import annotations

import argparse
import json
import sys
import uuid

from pydantic import BaseModel


class _Pong(BaseModel):
    ok: bool


PING_PROMPT = 'Reply with only this JSON object and nothing else: {"ok": true}'


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("llm", help="LLM provider utilities")
    sub2 = p.add_subparsers(dest="llm_cmd", required=True)
    ping = sub2.add_parser("ping", help="One JSON round-trip on a route; prints provider, model, latency")
    ping.add_argument("--route", choices=["fast", "deep"], default="fast")
    ping.set_defaults(_handler=_ping)
    status = sub2.add_parser("status", help="Provider resolution and discovery details (no secrets)")
    status.add_argument("--all-models", action="store_true", help="list every model id seen")
    status.set_defaults(_handler=_status)


def _status(args: argparse.Namespace) -> None:
    from app.llm import status

    info = status.check()
    meterless = dict(info["meterless"])  # type: ignore[arg-type]
    seen = list(meterless.get("models_seen") or [])
    if not args.all_models:
        meterless["models_seen"] = [m for m in seen if m.startswith(("meterless/", "nvidia/"))]
        meterless["models_seen_total"] = len(seen)
    print(json.dumps({**info, "meterless": meterless}, indent=2))


def _ping(args: argparse.Namespace) -> None:
    from app.config import get_settings
    from app.errors import ArbiterError
    from app.llm.generator import generate
    from app.tracing import Tracer

    settings = get_settings()
    run_id = f"ping-{args.route}-{uuid.uuid4().hex[:8]}"
    tracer = Tracer(run_id, mode=settings.mode())
    try:
        result = generate(
            PING_PROMPT,
            route=args.route,
            response="json",
            schema=_Pong,
            purpose="ping",
            tracer=tracer,
            agent_name="CLI",
        )
    except ArbiterError as exc:
        print(f"ping {args.route}: FAILED {exc.type}: {exc.message}")
        print(f"trace: logs/trace-{run_id}.jsonl")
        sys.exit(1)
    finally:
        tracer.close()
    print(f"ping {args.route}: ok")
    print(f"  provider   {result.provider}")
    print(f"  model      {result.model}")
    print(f"  latency_ms {result.latency_ms}")
    print(f"  tokens     in={result.tokens_in} out={result.tokens_out}")
    print(f"  repaired   {result.repaired}")
    print(f"  trace      logs/trace-{run_id}.jsonl")
