"""Shared secret detection patterns (scan_secrets, config.mask_secrets, tracing)."""

from __future__ import annotations

import re

PLACEHOLDER_PREFIXES = ("your-", "generate-", "changeme", "example", "placeholder")
PLACEHOLDER_EXACT = ("***",)

SECRET_REGEXES: list[tuple[str, re.Pattern[str]]] = [
    ("sk", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
    ("nvapi", re.compile(r"nvapi-[A-Za-z0-9_-]{20,}")),
    ("akia", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("ghp", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("slack", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("pem", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("jwt", re.compile(r"eyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{10,}")),
    (
        "assignment",
        re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[=:]\s*['\"]?([^\s'\"#]{12,})"),
    ),
]


def is_placeholder_value(value: str) -> bool:
    if not value or not value.strip():
        return True
    v = value.strip()
    if v in PLACEHOLDER_EXACT:
        return True
    lower = v.lower()
    if lower.startswith(PLACEHOLDER_PREFIXES):
        return True
    return bool(v.startswith("<") and v.endswith(">"))


def mask_secret_value(value: str) -> str:
    if len(value) <= 4:
        return "***"
    return value[:4] + "***"


def contains_secret(text: str) -> bool:
    return any(pattern.search(text) for _name, pattern in SECRET_REGEXES)


def mask_secrets_in_text(text: str, *, extra_values: list[str] | None = None) -> str:
    out = text
    for _name, pattern in SECRET_REGEXES:
        out = pattern.sub(lambda m: _mask_match(m), out)
    if extra_values:
        for val in extra_values:
            if val and not is_placeholder_value(val):
                out = out.replace(val, "***")
    return out


def _mask_match(match: re.Match[str]) -> str:
    if match.lastindex and match.lastindex >= 2:
        val = match.group(2)
        if is_placeholder_value(val):
            return match.group(0)
    full = match.group(0)
    if "=" in full or ":" in full:
        key, _, _rest = full.partition("=" if "=" in full else ":")
        return f"{key.strip()}=***"
    return "***"
