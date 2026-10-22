"""POST /run: one assessment, from intake through the signed contract."""

from __future__ import annotations

from fastapi import APIRouter

from app.orchestrator import RunOptions, run
from app.schemas.api import RunRequest, RunResponse

router = APIRouter(tags=["run"])


@router.post("/run", response_model=RunResponse)
def run_case(body: RunRequest) -> RunResponse:
    options = body.options
    return run(
        body.case,
        options=RunOptions(
            sample_mode=None if options is None else options.sample_mode,
            llm=None if options is None else options.llm,
        ),
    )
