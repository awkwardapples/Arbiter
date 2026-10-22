"""Append-only hash-chained audit log in SQLite."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.canon import canonical_json, sha256_hex

_GENESIS_PREV = ""


class AuditChain:
    def __init__(self, db_path: Path | str = "var/audit.db") -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                seq INTEGER PRIMARY KEY,
                ts TEXT NOT NULL,
                case_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                hash TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def append(self, event_type: str, case_id: str, payload: dict[str, Any]) -> int:
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._conn:
            row = self._conn.execute("SELECT hash FROM audit_log ORDER BY seq DESC LIMIT 1").fetchone()
            prev_hash = row[0] if row else _GENESIS_PREV
            seq_row = self._conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM audit_log").fetchone()
            seq = int(seq_row[0])
            event = {
                "seq": seq,
                "ts": ts,
                "case_id": case_id,
                "event_type": event_type,
                "payload": payload,
            }
            digest = sha256_hex(prev_hash + canonical_json(event))
            self._conn.execute(
                """
                INSERT INTO audit_log (seq, ts, case_id, event_type, payload_json, prev_hash, hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    seq,
                    ts,
                    case_id,
                    event_type,
                    canonical_json(payload),
                    prev_hash,
                    digest,
                ),
            )
        return seq

    def verify(self) -> tuple[bool, int | None]:
        rows = self._conn.execute(
            "SELECT seq, ts, case_id, event_type, payload_json, prev_hash, hash FROM audit_log ORDER BY seq"
        ).fetchall()
        prev_hash = _GENESIS_PREV
        for seq, ts, case_id, event_type, payload_json, stored_prev, stored_hash in rows:
            if stored_prev != prev_hash:
                return False, seq
            import json

            payload = json.loads(payload_json)
            event = {
                "seq": seq,
                "ts": ts,
                "case_id": case_id,
                "event_type": event_type,
                "payload": payload,
            }
            expected = sha256_hex(prev_hash + canonical_json(event))
            if expected != stored_hash:
                return False, seq
            prev_hash = stored_hash
        return True, None

    def close(self) -> None:
        self._conn.close()
