"""PII and credential redaction before LLM exposure."""

from __future__ import annotations

import re

_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}\b")
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
_SECRET = re.compile(
    r"\b("
    r"sk-[A-Za-z0-9]{20,}"
    r"|nvapi-[A-Za-z0-9_-]{20,}"
    r"|AKIA[A-Z0-9]{16}"
    r"|[A-Fa-f0-9]{32,}"
    r"|[A-Za-z0-9+/]{40,}={0,2}"
    r")\b"
)

_COUNTERS: dict[str, int] = {
    "EMAIL": 0,
    "PHONE": 0,
    "IBAN": 0,
    "SECRET": 0,
}


def _placeholder(kind: str) -> str:
    _COUNTERS[kind] += 1
    return f"[{kind}_{_COUNTERS[kind]}]"


def redact(text: str) -> tuple[str, dict[str, str]]:
    """Return redacted text and placeholder -> original value (in-memory only)."""
    for key in _COUNTERS:
        _COUNTERS[key] = 0
    mapping: dict[str, str] = {}

    def sub(kind: str, pattern: re.Pattern[str], value: str) -> str:
        def repl(match: re.Match[str]) -> str:
            original = match.group(0)
            for ph, orig in mapping.items():
                if orig == original:
                    return ph
            ph = _placeholder(kind)
            mapping[ph] = original
            return ph

        return pattern.sub(repl, value)

    out = text
    out = sub("EMAIL", _EMAIL, out)
    out = sub("PHONE", _PHONE, out)
    out = sub("IBAN", _IBAN, out)
    out = sub("SECRET", _SECRET, out)
    return out, mapping
