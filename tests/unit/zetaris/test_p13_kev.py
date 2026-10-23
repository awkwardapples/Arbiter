"""P13-T3: the KEV REST table always reads the configured CISA catalogue URL."""

from __future__ import annotations

import pytest

from app.config import get_settings
from zetaris.onboard import kev_rest_url

KEV = "https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json"


@pytest.mark.p13
@pytest.mark.parametrize("mode", ["simulator", "github_raw"])
def test_p13_t3_kev_rest_url_follows_settings(monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    """P13-T3: kev_rest_url returns settings.KEV_URL in every source mode."""
    monkeypatch.setenv("ZETARIS_SOURCE_MODE", mode)
    monkeypatch.setenv("KEV_URL", KEV)
    monkeypatch.setenv(
        "GITHUB_RAW_BASE",
        "https://raw.githubusercontent.com/awkwardapples/Arbiter/main/data/sample/systems",
    )
    get_settings.cache_clear()
    settings = get_settings()
    assert kev_rest_url(settings) == settings.KEV_URL
    get_settings.cache_clear()
