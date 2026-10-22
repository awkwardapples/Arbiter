"""P3-T9: every input example reaches its expected outcome offline, with an honest collaborative trace."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.orchestrator import RunOptions, run
from app.schemas.api import RunResponse
from scripts.check_trace import validate_file
from tests.e2e.support import EXAMPLE_FILES, expected, load_example, offline_env, trace

pytestmark = pytest.mark.p3
__all__ = ["offline_env"]


def test_p3_t9_six_examples_present() -> None:
    assert len(EXAMPLE_FILES) == 6
    assert set(EXAMPLE_FILES) == set(expected())


@pytest.mark.parametrize("name", EXAMPLE_FILES)
def test_p3_t9_example_offline(name: str, offline_env: Path) -> None:
    resp = run(load_example(name), options=RunOptions())
    RunResponse.model_validate(resp.model_dump(mode="json"))
    assert resp.output is not None
    assert resp.output.decision == expected()[name]["outcome"]
    assert resp.mode["data"] == "duckdb"
    assert validate_file(Path(resp.log_file), require_collaboration=True, require_live=False) == []
    rows = trace(resp.log_file)
    assert any(r["status"] == "needs_revision" and r["agent_name"] == "EvaluatorAgent" for r in rows)
    assert any(r.get("query_id") in {"Q_VENDOR_INCIDENTS", "Q_INCIDENTS_BY_NAME"} for r in rows)
    for artifact in resp.output.artifacts:
        assert (offline_env / artifact).is_file()


def test_p3_t9_example_2_loop_reaches_kev(offline_env: Path) -> None:
    resp = run(load_example("example_2.json"), options=RunOptions())
    rows = trace(resp.log_file)
    revision = [i for i, r in enumerate(rows) if r["status"] == "needs_revision"]
    kev = [i for i, r in enumerate(rows) if r.get("query_id") == "Q_COMPONENT_KEV"]
    assert revision and kev
    assert min(kev) > min(revision)
