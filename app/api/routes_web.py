"""Serve the built web console at /console/ when web/dist/index.html exists (lane P18-A)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.types import Scope

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "web" / "dist"

NOT_BUILT = {"console": "not built", "api_docs": "/docs", "classic_console": "python run.py ui"}


class SpaStaticFiles(StaticFiles):
    """Static files whose 404 is `index.html`: the catch-all for the console's client-side routes."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            return await super().get_response("index.html", scope)


def install(app: FastAPI, dist: Path = DIST) -> None:
    """Mount the console if it is built; otherwise `/` says how to reach the API and the classic UI."""
    if (dist / "index.html").is_file():
        app.mount("/console", SpaStaticFiles(directory=dist, html=True), name="console")

        @app.get("/", include_in_schema=False)
        def console_root() -> RedirectResponse:
            return RedirectResponse("/console/", status_code=307)

        return

    @app.get("/", include_in_schema=False)
    def not_built() -> dict[str, Any]:
        return dict(NOT_BUILT)
