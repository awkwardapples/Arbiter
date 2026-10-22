"""Append-only trust ledger (port of `reference/src/trustLedger.ts`).

Entries are never mutated or deleted. `history()` reconstructs a memory's full change record
from the previousState/newState snapshots carried on each entry. Arbiter adds an optional
write-only mirror file (`logs/hmem-ledger.jsonl` in production) that is only ever appended to.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.memory.hmem.jsfmt import js_json_dumps, js_json_loads
from app.memory.hmem.types import LedgerAction, LedgerEntry


class TrustLedgerService:
    def __init__(
        self,
        clock: Callable[[], int],
        persist_dir: str | Path | None = None,
        mirror_path: str | Path | None = None,
    ) -> None:
        self._clock = clock
        self._entries: list[LedgerEntry] = []
        self._file: Path | None = None
        self._mirror = Path(mirror_path) if mirror_path is not None else None
        if persist_dir is not None:
            self._file = Path(persist_dir) / "ledger.jsonl"
            if self._file.exists():
                for line in self._file.read_text(encoding="utf-8").split("\n"):
                    if line:
                        self._entries.append(LedgerEntry.model_validate(js_json_loads(line)))

    def log(
        self,
        memory_id: str,
        action: LedgerAction,
        actor: str,
        *,
        previous_state: dict[str, Any] | None = None,
        new_state: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
    ) -> LedgerEntry:
        entry = LedgerEntry(
            memory_id=memory_id,
            action=action,
            actor=actor,
            timestamp=self._clock(),
            previous_state=previous_state,
            new_state=new_state,
            details=details,
        )
        self._entries.append(entry)
        line = js_json_dumps(entry.to_json()) + "\n"
        if self._file is not None:
            with self._file.open("a", encoding="utf-8") as fh:
                fh.write(line)
        if self._mirror is not None:
            self._mirror.parent.mkdir(parents=True, exist_ok=True)
            with self._mirror.open("a", encoding="utf-8") as fh:
                fh.write(line)
        return entry

    def history(self, memory_id: str) -> list[LedgerEntry]:
        return [e for e in self._entries if e.memory_id == memory_id]

    def all(self) -> tuple[LedgerEntry, ...]:
        return tuple(self._entries)

    def stats(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for e in self._entries:
            out[e.action] = out.get(e.action, 0) + 1
        return out
