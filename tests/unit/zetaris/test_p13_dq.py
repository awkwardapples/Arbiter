"""P13: USL names stay qualified, and SHOW DQ object rows become keys."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from app.config import get_settings
from app.data.registry import load_registry
from app.data.zetaris import ZetarisBackend
from app.tracing import Tracer


@pytest.fixture
def backend(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ZetarisBackend:
    monkeypatch.setenv("ZETARIS_API_KEY", "test-key-not-real")
    monkeypatch.setenv("ZETARIS_REST_URL", "http://zetaris.test/api/v1.0")
    monkeypatch.setenv("ZETARIS_QUERY_LAYER", "usl")
    get_settings.cache_clear()
    tracer = Tracer("p13-dq", mode={"data": "zetaris"}, log_dir=str(tmp_path))
    client = ZetarisBackend(get_settings(), load_registry(), tracer)
    yield client
    get_settings.cache_clear()


@pytest.mark.p13
def test_p13_qualify_leaves_dotted_names(backend: ZetarisBackend) -> None:
    """Already-qualified USL names are not rewritten. A bare table name is."""
    shown = "SHOW DQ ALL INVALID TABLE lightning.metastore.arbiter.vendor_risk.contract"
    assert backend._qualify_dq_sql(shown) == shown
    counted = "SELECT COUNT(*) AS c FROM lightning.metastore.arbiter.vendor_risk.vendor"
    assert backend._qualify_dq_sql(counted) == counted
    bare = backend._qualify_dq_sql("SELECT vendor_id FROM vendor")
    assert "lightning.metastore.arbiter.vendor_risk.vendor" in bare


@pytest.mark.p13
def test_p13_dq_invalid_reads_object_record(backend: ZetarisBackend) -> None:
    """SHOW DQ returns one JSON object in records, not a list."""
    payload = {
        "headers": ["records"],
        "data": [[json.dumps({"contract_id": "CTR-30028", "supplier_ref": "SUP-7028"})]],
    }
    with respx.mock:
        respx.post("http://zetaris.test/api/v1.0/sql-editor/sqls/run").mock(
            return_value=httpx.Response(200, json=payload)
        )
        keys = backend.dq_invalid("contract")
    assert keys == {"CTR-30028"}
