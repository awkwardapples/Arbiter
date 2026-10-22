"""FastAPI simulator for synthetic enterprise systems (:8100)."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[1]
SYSTEMS_DIR = ROOT / "data" / "sample" / "systems"
KEV_PATH = ROOT / "data" / "kev" / "kev_snapshot.json"

ROUTE_FILES = {
    "/procurement/v1/vendors": "procurement_vendors.json",
    "/procurement/v1/vendor-aliases": "procurement_vendor_aliases.json",
    "/clm/v2/contracts": "clm_contracts.json",
    "/itsm/api/incidents": "itsm_incidents.json",
    "/grc/v1/watchlist": "grc_watchlist.json",
    "/trust/v1/submissions": "trust_submissions.json",
    "/trust/v1/answers": "trust_answers.json",
    "/trust/v1/documents": "trust_documents.json",
    "/trust/v1/components": "trust_components.json",
}


@lru_cache
def _load(name: str) -> dict[str, Any]:
    path = SYSTEMS_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def _fault_key(system: str) -> str | None:
    raw = os.environ.get("SIM_FAULTS", "")
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if part.lower().startswith(f"{system.lower()}:"):
            return part.split(":", 1)[1]
    return None


_fault_state: dict[str, int] = {}


def _should_fault(route: str) -> bool:
    system_map = {
        "/itsm/api/incidents": "itsm",
    }
    system = system_map.get(route)
    if not system:
        return False
    spec = _fault_key(system)
    if not spec:
        return False
    if spec.startswith("500x"):
        try:
            remaining = int(spec[4:])
        except ValueError:
            return False
        key = system
        used = _fault_state.get(key, 0)
        if used < remaining:
            _fault_state[key] = used + 1
            return True
    return False


def create_app(*, systems_dir: Path | None = None) -> FastAPI:
    global SYSTEMS_DIR
    if systems_dir is not None:
        SYSTEMS_DIR = systems_dir

    app = FastAPI(title="Arbiter enterprise simulator")

    @app.get("/health")
    def health() -> dict[str, object]:
        counts = {route: _load(fname)["count"] for route, fname in ROUTE_FILES.items()}
        sample = _load("procurement_vendors.json")
        return {"status": "ok", "as_of": sample.get("as_of"), "counts": counts}

    @app.get("/public/kev-snapshot")
    def kev_snapshot() -> dict[str, Any]:
        return json.loads(KEV_PATH.read_text(encoding="utf-8"))

    for route, fname in ROUTE_FILES.items():

        def _make_handler(file_name: str, route_path: str):
            def handler() -> Response:
                if _should_fault(route_path):
                    return JSONResponse(status_code=500, content={"error": "simulated fault"})
                return _load(file_name)

            return handler

        app.get(route)(_make_handler(fname, route))

    return app


def main() -> None:
    import uvicorn

    port = int(os.environ.get("SOURCES_PORT", "8100"))
    uvicorn.run(create_app(), host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
