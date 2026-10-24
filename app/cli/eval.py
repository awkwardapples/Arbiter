"""Evaluation and calibration commands. Delegates to `eval/`; does not read labels itself."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from app.config import get_settings
from app.llm.resolve import reset_cache

ROOT = Path(__file__).resolve().parents[2]


def _offline_env(*, memory: str) -> None:
    os.environ["SAMPLE_MODE"] = "true"
    os.environ["LLM_PROVIDER"] = "offline"
    os.environ["ARBITER_MEMORY"] = memory
    get_settings.cache_clear()
    reset_cache()


def cmd_eval(args: argparse.Namespace) -> None:
    if args.session:
        _offline_env(memory="on")
        from app.cli.review import cmd_demo_session

        raise SystemExit(cmd_demo_session(argparse.Namespace(reset=True, yes=True, live=False)))

    publish_only = args.publish and not args.split and not args.systems and not args.consistency
    if publish_only:
        from eval.report import latest_summary, publish

        summary = latest_summary(_results_root())
        publish(summary, docs_path=ROOT / "docs" / "EVALUATION.md", readme_path=ROOT / "README.md")
        return

    splits = [part.strip() for part in (args.split or "test").split(",") if part.strip()]
    systems = [part.strip() for part in (args.systems or "arbiter_offline").split(",") if part.strip()]
    consistency = _consistency(args.consistency)
    live = bool(getattr(args, "live", False))
    if not live:
        _offline_env(memory="off")
    from eval.harness import run

    # Offline unless --live: then arbiter and baseline run on Zetaris and Nightshift (P15).
    # --llm is accepted and ignored; --live pins LLM_PROVIDER=meterless per system.
    out = run(
        systems,
        splits,
        consistency=consistency,
        live=live,
        limit=getattr(args, "cases", None),
        results_root=_results_root(live=live),
    )
    if args.publish:
        from eval.report import publish

        summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
        # A live run publishes docs/EVALUATION.md only; the README block belongs to P17.
        readme = None if live else ROOT / "README.md"
        publish(summary, docs_path=ROOT / "docs" / "EVALUATION.md", readme_path=readme)
    print(out)


def cmd_calibrate(_args: argparse.Namespace) -> None:
    _offline_env(memory="off")
    from eval.calibrate import calibrate_split

    result = calibrate_split(
        out_dir=ROOT / "policy" / "calibration",
        active_path=ROOT / "policy" / "calibration" / "ACTIVE",
    )
    print(result.path)


def _results_root(*, live: bool = False) -> Path:
    override = os.environ.get("ARBITER_EVAL_ROOT")
    if override:
        return Path(override)
    return ROOT / "eval" / ("results_live" if live else "results")


def _consistency(raw: str | None) -> tuple[int, int] | None:
    if not raw:
        return None
    text = raw.lower().replace("×", "x")
    if "x" not in text:
        raise SystemExit("consistency must look like 8x3")
    width, repeats = text.split("x", 1)
    return int(width), int(repeats)


def register(sub: argparse._SubParsersAction) -> None:
    ev = sub.add_parser("eval", help="Run the evaluation harness")
    ev.add_argument("--split")
    ev.add_argument("--systems")
    ev.add_argument("--consistency")
    ev.add_argument("--llm")
    ev.add_argument("--publish", action="store_true")
    ev.add_argument("--live", action="store_true", help="arbiter and baseline on Zetaris and Nightshift")
    ev.add_argument("--cases", type=int, help="live systems run the first N cases by case id")
    ev.add_argument("--session", action="store_true")
    ev.set_defaults(_handler=cmd_eval)

    sub.add_parser("calibrate", help="Calibrate confidence gates").set_defaults(_handler=cmd_calibrate)
