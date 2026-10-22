"""JavaScript semantics the H-MEM port must reproduce exactly.

The reference engine is TypeScript; these helpers stand in for the JS built-ins whose
behaviour differs from Python's (number formatting, string length and trimming, the
whitespace class, default `Array.prototype.sort`, `JSON.stringify` of lone surrogates).
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

# ECMAScript WhiteSpace (TAB, VT, FF, ZWNBSP, every Zs code point) plus LineTerminator.
# Python's `\s` differs: it adds U+001C–U+001F and U+0085 and omits U+FEFF.
JS_WHITESPACE = (
    "\t\v\f \u00a0\u1680"
    + "".join(chr(c) for c in range(0x2000, 0x200B))
    + "\u202f\u205f\u3000\ufeff"
    + "\n\r\u2028\u2029"
)
JS_WS_CLASS = "[" + "".join(f"\\u{ord(c):04x}" for c in JS_WHITESPACE) + "]"

_LONE_SURROGATE = re.compile("[\ud800-\udfff]")
_ASCII_ID = re.compile(r"[\x20-\x7e]*")


def imul32(a: int, b: int) -> int:
    """`Math.imul(a, b) >>> 0`."""
    return (a * b) & 0xFFFFFFFF


def utf16_units(s: str) -> list[int]:
    """The UTF-16 code units JS `charCodeAt` iterates over."""
    data = s.encode("utf-16-be", "surrogatepass")
    return [int.from_bytes(data[i : i + 2], "big") for i in range(0, len(data), 2)]


def js_len(s: str) -> int:
    """`String.prototype.length` (UTF-16 code units, not code points)."""
    return len(s.encode("utf-16-be", "surrogatepass")) // 2


def js_slice(s: str, start: int, end: int) -> str:
    """`String.prototype.slice(start, end)` for non-negative indices, in UTF-16 code units."""
    data = s.encode("utf-16-be", "surrogatepass")
    return data[2 * start : 2 * end].decode("utf-16-be", "surrogatepass")


def js_trim(s: str) -> str:
    return s.strip(JS_WHITESPACE)


def to_fixed(x: float, digits: int) -> float:
    """`Number(x.toFixed(digits))`: half away from zero on the exact binary value."""
    if not math.isfinite(x):
        return x
    quantum = Decimal(1).scaleb(-digits)
    return float(Decimal(x).quantize(quantum, rounding=ROUND_HALF_UP))


def clamp01(x: float) -> float:
    """`Math.min(1, Math.max(0, x))`, including NaN propagation."""
    if math.isnan(x):
        return x
    return min(1.0, max(0.0, x))


def js_default_sort_key(s: str) -> bytes:
    """Key for `Array.prototype.sort()` with no comparator: UTF-16 code-unit order."""
    return s.encode("utf-16-be", "surrogatepass")


def js_string(value: Any) -> str:
    """`String(value)` for the value kinds the engine sorts (strings, arrays, objects)."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, (list, tuple)):
        return ",".join(js_string(v) for v in value)
    return "[object Object]"


def js_sort_entries[K, V](items: Sequence[tuple[K, V]]) -> list[tuple[K, V]]:
    """`[...map.entries()].sort()`: compares `String([k, v])`, not just the key."""
    return sorted(items, key=lambda kv: js_default_sort_key(js_string(list(kv))))


def assert_ascii_id(s: str) -> str:
    """Ids are compared with `localeCompare`; for printable ASCII that equals plain comparison."""
    if not _ASCII_ID.fullmatch(s):
        raise ValueError(f"H-MEM id is not printable ASCII: {s!r}")
    return s


def js_json_dumps(obj: Any, *, indent: int | None = None) -> str:
    """`JSON.stringify` output: no ASCII escaping, compact separators, lone surrogates escaped."""
    separators = (",", ": ") if indent is not None else (",", ":")
    text = json.dumps(obj, ensure_ascii=False, indent=indent, separators=separators, allow_nan=False)
    return _LONE_SURROGATE.sub(lambda m: f"\\u{ord(m.group()):04x}", text)


def _reject_constant(name: str) -> Any:
    raise ValueError(f"invalid JSON constant {name}")


def js_json_loads(text: str) -> Any:
    """`JSON.parse`: rejects the NaN/Infinity tokens Python's json module accepts."""
    return json.loads(text, parse_constant=_reject_constant)
