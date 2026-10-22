"""P1-B onboard script tests (P1-T23)."""

from __future__ import annotations

import pytest

from zetaris.onboard import load_statements, run_onboard, substitute_placeholders


@pytest.mark.p1b
def test_p1_t23_statement_split_and_substitution(monkeypatch: pytest.MonkeyPatch) -> None:
    """P1-T23: @@stmt splitting, COMPILE USL stays one statement, URL modes, --yes guard."""
    stmts = load_statements(only="03")
    compile_stmts = [s for label, s in stmts if "COMPILE USL" in s]
    assert len(compile_stmts) == 1
    assert compile_stmts[0].count("CREATE TABLE") >= 10

    monkeypatch.setenv("ZETARIS_SOURCE_MODE", "simulator")
    monkeypatch.setenv("SOURCES_PUBLIC_BASE", "http://sim:8100")
    monkeypatch.setenv(
        "GITHUB_RAW_BASE", "https://raw.githubusercontent.com/awkwardapples/Arbiter/main/data/sample/systems"
    )
    from app.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    sim_sql = substitute_placeholders("SELECT '{URL:clm_contracts_raw}'", settings)
    assert sim_sql.endswith("http://sim:8100/clm/v2/contracts'")

    monkeypatch.setenv("ZETARIS_SOURCE_MODE", "github_raw")
    get_settings.cache_clear()
    settings = get_settings()
    raw_sql = substitute_placeholders("SELECT '{URL:clm_contracts_raw}'", settings)
    assert "awkwardapples/Arbiter/main/data/sample/systems/clm_contracts.json" in raw_sql

    monkeypatch.setenv("ZETARIS_API_KEY", "test-key")
    get_settings.cache_clear()
    settings = get_settings()
    code = run_onboard(settings, dry_run=True)
    assert code == 0
    dry = run_onboard(settings, dry_run=False, yes=False)
    assert dry == 2
    assert "test-key" not in str(substitute_placeholders("SELECT 1", settings))
