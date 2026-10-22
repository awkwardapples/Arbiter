"""HMAC signing key from environment or ephemeral file."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from app.config import get_settings
from app.tracing import Tracer

logger = logging.getLogger("arbiter.keys")

_EPHEMERAL_PATH = Path("var/keys/ephemeral.key")
_cached_key: bytes | None = None
_ephemeral_noted = False


def ephemeral_key_was_noted() -> bool:
    return _ephemeral_noted


def signing_key(*, tracer: Tracer | None = None) -> bytes:
    global _cached_key, _ephemeral_noted
    if _cached_key is not None:
        return _cached_key

    settings = get_settings()
    configured = settings.ARBITER_SIGNING_KEY
    env_hex = configured.get_secret_value() if configured else os.environ.get("ARBITER_SIGNING_KEY")
    if env_hex:
        raw = bytes.fromhex(env_hex.strip())
        if len(raw) < 32:
            raise ValueError("ARBITER_SIGNING_KEY must be at least 32 bytes (hex)")
        _cached_key = raw
        return _cached_key

    _EPHEMERAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if _EPHEMERAL_PATH.is_file():
        _cached_key = _EPHEMERAL_PATH.read_bytes()
        return _cached_key

    import secrets

    _cached_key = secrets.token_bytes(32)
    _EPHEMERAL_PATH.write_bytes(_cached_key)
    _ephemeral_noted = True
    logger.info("generated ephemeral signing key at %s", _EPHEMERAL_PATH)
    if tracer:
        tracer.event(
            "SigningKey",
            "ephemeral_key",
            input_summary="ARBITER_SIGNING_KEY unset",
            output_summary="ephemeral_signing_key var/keys/ephemeral.key",
            status="success",
        )
    return _cached_key


def reset_signing_key_cache_for_tests() -> None:
    global _cached_key, _ephemeral_noted
    _cached_key = None
    _ephemeral_noted = False
