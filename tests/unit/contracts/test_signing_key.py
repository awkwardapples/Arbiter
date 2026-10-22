"""P2-T48: ephemeral signing key."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.actions import keys
from app.tracing import Tracer

pytestmark = pytest.mark.p2d


def test_p2_t48_ephemeral_key_reuse_and_trace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARBITER_SIGNING_KEY", raising=False)
    keys.reset_signing_key_cache_for_tests()
    key_dir = tmp_path / "var" / "keys"
    key_dir.mkdir(parents=True)
    key_path = key_dir / "ephemeral.key"
    monkeypatch.chdir(tmp_path)

    tracer = Tracer("run-key", mode={"sample": "true"}, log_dir=str(tmp_path / "logs"))
    try:
        k1 = keys.signing_key(tracer=tracer)
        k2 = keys.signing_key()
    finally:
        tracer.close()

    assert k1 == k2
    assert key_path.is_file()
    assert keys.ephemeral_key_was_noted()
    logs_dir = tmp_path / "logs"
    for path in logs_dir.rglob("*"):
        if path.is_file():
            assert k1.hex() not in path.read_text(encoding="utf-8", errors="ignore")
    monkeypatch.delenv("ARBITER_SIGNING_KEY", raising=False)
    keys.reset_signing_key_cache_for_tests()
