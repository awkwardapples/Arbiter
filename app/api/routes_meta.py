from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.api import HealthResponse

router = APIRouter(tags=["meta"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(mode=settings.mode())
