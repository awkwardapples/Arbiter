"""Backend factory (DuckDB sample mode; Zetaris when P1-B provides it)."""

from __future__ import annotations

import importlib.util

from app.config import Settings
from app.data.backend import DataBackend, FallbackBackend
from app.data.duckdb_backend import DuckDBBackend
from app.data.inline import InlineBackend
from app.schemas.case import VendorSubmission
from app.tracing import Tracer


def _zetaris_available() -> bool:
    spec = importlib.util.find_spec("app.data.zetaris")
    if spec is None:
        return False
    mod = importlib.import_module("app.data.zetaris")
    return hasattr(mod, "ZetarisBackend") and callable(mod.ZetarisBackend)


def get_backend(
    settings: Settings,
    tracer: Tracer,
    submission: VendorSubmission | None = None,
) -> DataBackend:
    duck = DuckDBBackend()
    if settings.SAMPLE_MODE or not _zetaris_available():
        if not settings.SAMPLE_MODE:
            tracer.event(
                "data",
                "backend_select",
                input_summary="live mode",
                output_summary="ZetarisBackend not implemented; using duckdb",
                status="success",
            )
        main: DataBackend = duck
    else:
        from app.data.registry import load_registry
        from app.data.zetaris import ZetarisBackend

        primary = ZetarisBackend(settings, load_registry(), tracer)
        main = FallbackBackend(primary, duck, tracer)
    if submission is not None:
        return InlineBackend(submission, main)
    return main
