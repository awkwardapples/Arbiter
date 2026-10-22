from __future__ import annotations

import argparse
import subprocess
import sys

import uvicorn

from app.config import get_settings


def register(sub: argparse._SubParsersAction) -> None:
    serve_p = sub.add_parser("serve", help="Run the Arbiter API")
    serve_p.set_defaults(_handler=_serve)

    ui_p = sub.add_parser("ui", help="Run the Streamlit reviewer console")
    ui_p.set_defaults(_handler=_ui)

    preflight_p = sub.add_parser("preflight", help="Check provider and data status")
    preflight_p.set_defaults(_handler=_preflight)


def _serve(_args: argparse.Namespace) -> None:
    settings = get_settings()
    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
    )


def _ui(_args: argparse.Namespace) -> None:
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "ui/app.py"],
        check=False,
    )


def _preflight(_args: argparse.Namespace) -> None:
    rows: list[tuple[str, str]] = []
    try:
        from app.llm import status as llm_status

        info = llm_status.check()
        rows.append(("llm", str(info.get("provider_resolved", "unknown"))))
    except Exception:
        rows.append(("llm", "not yet implemented"))
    try:
        from app.data import status as data_status

        info = data_status.check()
        rows.append(("data", str(info.get("backend", "unknown"))))
    except Exception:
        rows.append(("data", "not yet implemented"))
    settings = get_settings()
    rows.append(("mode.data", settings.mode()["data"]))
    rows.append(("mode.llm", settings.mode()["llm"]))
    print("Preflight (no secrets):")
    for key, val in rows:
        print(f"  {key:12} {val}")
