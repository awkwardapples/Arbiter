from __future__ import annotations

import argparse
from datetime import date

from app.config import get_settings


def register(sub: argparse._SubParsersAction) -> None:
    gen = sub.add_parser("generate-data", help="Generate synthetic enterprise data")
    gen.add_argument("--seed", type=int, default=2026)
    gen.add_argument("--as-of", type=str, default="2026-10-26")
    gen.add_argument("--refresh-kev", action="store_true")
    gen.set_defaults(_handler=_generate_data)

    src = sub.add_parser("sources", help="Run the enterprise systems simulator")
    src.add_argument("--port", type=int, default=8100)
    src.set_defaults(_handler=_sources)


def _generate_data(args: argparse.Namespace) -> None:
    from data.generator.generate import generate

    settings = get_settings()
    as_of = date.fromisoformat(args.as_of)
    generate(
        seed=args.seed,
        as_of=as_of,
        refresh_kev=args.refresh_kev,
        kev_url=settings.KEV_URL,
    )


def _sources(args: argparse.Namespace) -> None:
    import os

    os.environ["SOURCES_PORT"] = str(args.port)
    from sources.simulator import main

    main()
