"""P18A-T11, T13: the built console is served at /console/, and recordings ship in the image."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes_cases, routes_web
from tests.e2e.support import offline_env

pytestmark = pytest.mark.p18a
__all__ = ["offline_env"]

ROOT = Path(__file__).resolve().parents[3]
HTML = "<!doctype html><title>Arbiter</title><div id=root></div>"


def _app(dist: Path) -> FastAPI:
    app = FastAPI()
    app.include_router(routes_cases.router)
    routes_web.install(app, dist)
    return app


def test_p18a_t11_console_served_when_built(offline_env: Path, tmp_path: Path) -> None:
    """P18A-T11: / → /console/; client routes return index.html; API routes keep JSON."""
    del offline_env
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(HTML, encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    client = TestClient(_app(dist))

    root = client.get("/", follow_redirects=False)
    assert root.status_code == 307
    assert root.headers["location"] == "/console/"
    for path in ("/console/", "/console/cases/CASE-0007"):
        page = client.get(path)
        assert page.status_code == 200
        assert page.headers["content-type"].startswith("text/html")
        assert page.text == HTML
    asset = client.get("/console/assets/app.js")
    assert asset.status_code == 200 and asset.text == "console.log(1)"
    cases = client.get("/cases")
    assert cases.status_code == 200
    assert cases.headers["content-type"].startswith("application/json")
    assert cases.json() == []


def test_p18a_t11_not_built(tmp_path: Path) -> None:
    """P18A-T11: without web/dist/index.html, / explains how to reach the API and the classic console."""
    client = TestClient(_app(tmp_path / "missing"))
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200
    assert response.json() == {
        "console": "not built",
        "api_docs": "/docs",
        "classic_console": "python run.py ui",
    }
    assert client.get("/console/").status_code == 404


def test_p18a_t13_dockerignore_keeps_recordings() -> None:
    """P18A-T13: logs/* stays excluded, but logs/examples/** is re-included after it."""
    lines = [
        line.strip()
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert "logs/*" in lines
    exclude = lines.index("logs/*")
    assert "!logs/examples/" in lines[exclude + 1 :]
    assert "!logs/examples/**" in lines[exclude + 1 :]
    assert "eval/results_live" not in lines
