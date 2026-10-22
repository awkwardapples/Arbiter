"""P1-T10, P1-T14 inline and watchlist screening."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.data.duckdb_backend import DuckDBBackend, reset_cache
from app.data.inline import inline_vendor_ref
from app.data.registry import watchlist_screen
from app.schemas.api import RunRequest
from app.schemas.case import VendorSubmission

ROOT = Path(__file__).resolve().parents[3]
INPUT_DIR = ROOT / "input_examples"


@pytest.mark.p1a
def test_p1_t10_input_examples_and_inline_ref() -> None:
    """P1-T10: examples validate; expected covers six; inline SUB- ref."""
    expected = json.loads((INPUT_DIR / "expected.json").read_text(encoding="utf-8"))
    files = sorted(INPUT_DIR.glob("example_*.json"))
    assert len(files) == 6
    assert set(expected) == {f.name for f in files}
    for path in files:
        RunRequest.model_validate(json.loads(path.read_text(encoding="utf-8")))
    ex6 = json.loads((INPUT_DIR / "example_6.json").read_text(encoding="utf-8"))
    sub = VendorSubmission.model_validate(ex6["submission"])
    assert inline_vendor_ref(sub).startswith("SUB-")


@pytest.mark.p1a
def test_p1_t14_components_and_watchlist_screen() -> None:
    """P1-T14: components rows; watchlist exact and near matches."""
    reset_cache()
    backend = DuckDBBackend()
    comps = backend.run("Q_VENDOR_COMPONENTS", {"vendor_id": "VND-0007"}).rows
    assert len(comps) >= 1
    empty = backend.run("Q_VENDOR_COMPONENTS", {"vendor_id": "VND-0003"}).rows
    assert empty == []
    all_wl = backend.run("Q_WATCHLIST_ALL", {}).rows
    assert len(all_wl) >= 1
    aliases = backend.run("Q_VENDOR_ALIASES", {"vendor_id": "VND-0019"}).rows
    alias_names = [str(r["alias_lower"]) for r in aliases]
    exact, near = watchlist_screen(alias_names, all_wl)
    assert exact
    decoy_aliases = backend.run("Q_VENDOR_ALIASES", {"vendor_id": "VND-0001"}).rows
    _exact, near2 = watchlist_screen([str(r["alias_lower"]) for r in decoy_aliases], all_wl)
    assert near2
    clean = backend.run("Q_VENDOR_ALIASES", {"vendor_id": "VND-0003"}).rows
    ex, _ = watchlist_screen([str(r["alias_lower"]) for r in clean], all_wl)
    assert not ex
