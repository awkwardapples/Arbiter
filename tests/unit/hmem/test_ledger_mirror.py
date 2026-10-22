"""P2-T6: append-only ledger mirror (logs/hmem-ledger.jsonl in production)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.memory.hmem import HMEM
from app.memory.hmem.types import LedgerEntry

pytestmark = pytest.mark.p2a

T0 = 1_750_000_000_000


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def test_one_line_per_entry(tmp_path: Path) -> None:
    mirror = tmp_path / "logs" / "hmem-ledger.jsonl"
    hmem = HMEM(clock=lambda: T0, ledger_mirror=mirror)
    m = hmem.add("mirrored record about docker deploys", source="t")
    hmem.query("docker deploys", threshold=0)
    hmem.feedback(m.id, "wrong")

    lines = _lines(mirror)
    entries = hmem.ledger.all()
    assert len(lines) == len(entries) == 3
    for line, entry in zip(lines, entries, strict=True):
        assert LedgerEntry.model_validate(json.loads(line)) == entry
    assert [json.loads(line)["action"] for line in lines] == ["create", "read", "feedback"]
    assert "memoryId" in json.loads(lines[0])


def test_mirror_is_append_only_across_instances(tmp_path: Path) -> None:
    mirror = tmp_path / "hmem-ledger.jsonl"
    first = HMEM(clock=lambda: T0, ledger_mirror=mirror)
    first.add("first instance record", source="t")
    first.add("another first instance record", source="t")
    before = _lines(mirror)
    assert len(before) == 2

    second = HMEM(clock=lambda: T0 + 1, ledger_mirror=mirror)
    second.add("second instance record", source="t")
    after = _lines(mirror)
    assert len(after) == 3
    assert after[:2] == before
    assert len(second.ledger.all()) == 1  # the mirror is write-only; it is not loaded back


def test_mirror_off_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    HMEM(clock=lambda: T0).add("no mirror configured", source="t")
    assert list(tmp_path.iterdir()) == []
