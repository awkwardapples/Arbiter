from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
