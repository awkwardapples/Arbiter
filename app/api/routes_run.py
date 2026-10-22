from __future__ import annotations

from fastapi import APIRouter

from app.errors import NotImplemented as ArbiterNotImplemented
from app.schemas.api import RunRequest

router = APIRouter(tags=["run"])


@router.post("/run")
def run_case(_body: RunRequest) -> None:
    raise ArbiterNotImplemented("Case execution is implemented in lane P3")
