from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    routes_cases,
    routes_contracts,
    routes_evidence,
    routes_meta,
    routes_review,
    routes_run,
    routes_stream,
    routes_web,
)
from app.errors import ArbiterError, ValidationFailed, http_status_for
from app.schemas.api import ErrorBody, ErrorResponse

logger = logging.getLogger("arbiter.api")

app = FastAPI(title="Arbiter", version="0.1.0")

app.include_router(routes_meta.router)
app.include_router(routes_run.router)
app.include_router(routes_cases.router)
app.include_router(routes_contracts.router)
app.include_router(routes_review.router)
app.include_router(routes_stream.router)
app.include_router(routes_evidence.router)
routes_web.install(app)

# Vite dev server only. Read here rather than in app/config.py (lane 19 owns it); moves to Settings after P19.
if os.environ.get("ARBITER_DEV_CORS") == "1":
    app.add_middleware(
        CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"]
    )


def _error_response(exc: ArbiterError, *, run_id: str | None = None) -> JSONResponse:
    body = ErrorResponse(
        run_id=run_id,
        error=ErrorBody(type=exc.type, message=exc.message, recoverable=exc.recoverable),
    )
    return JSONResponse(status_code=http_status_for(exc), content=body.model_dump(mode="json"))


@app.exception_handler(ArbiterError)
async def arbiter_error_handler(_request: Request, exc: ArbiterError) -> JSONResponse:
    return _error_response(exc)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    msg = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())
    err = ValidationFailed(msg)
    return _error_response(err)


@app.exception_handler(Exception)
async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API error: %s", type(exc).__name__)
    body = ErrorResponse(
        error=ErrorBody(type="InternalError", message="An internal error occurred", recoverable=False),
    )
    return JSONResponse(status_code=500, content=body.model_dump(mode="json"))
