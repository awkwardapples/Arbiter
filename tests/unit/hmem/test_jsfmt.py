"""P2-T3: JavaScript number, string and sort semantics used by the H-MEM port."""

from __future__ import annotations

import pytest

from app.memory.hmem import HMEM
from app.memory.hmem.jsfmt import (
    JS_WHITESPACE,
    assert_ascii_id,
    js_default_sort_key,
    js_sort_entries,
    js_trim,
    to_fixed,
)

pytestmark = pytest.mark.p2a


@pytest.mark.parametrize(
    ("x", "digits", "expected"),
    [
        (1.005, 2, 1.0),  # JS "1.00": the binary value is 1.00499999…
        (2.5, 0, 3.0),
        (-2.5, 0, -3.0),
        (0.0005, 3, 0.001),  # JS "0.001": the binary value is 0.000500000000000000010…
        (1.45, 1, 1.4),  # binary 1.44999…
        (1.55, 1, 1.6),  # binary 1.55000…04
        (0.123456789, 4, 0.1235),
        (0.5, 3, 0.5),
        (0.0, 4, 0.0),
    ],
)
def test_to_fixed_matches_js(x: float, digits: int, expected: float) -> None:
    assert to_fixed(x, digits) == expected


def test_to_fixed_never_uses_bankers_rounding() -> None:
    assert round(2.5) == 2  # Python's builtin, which the port must not use
    assert to_fixed(2.5, 0) == 3.0
    assert to_fixed(0.125, 2) == 0.13  # exact binary .125: JS rounds half up, round() gives 0.12


def test_js_whitespace_set_is_ecmascript() -> None:
    expected = set("\t\n\v\f\r \u00a0\u1680\u2028\u2029\u202f\u205f\u3000\ufeff") | {
        chr(c) for c in range(0x2000, 0x200B)
    }
    assert set(JS_WHITESPACE) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  x  ", "x"),
        ("\ufeff x \u2028", "x"),  # JS trims BOM and LS; Python's strip() does not trim BOM
        ("\x1cx\x1c", "\x1cx\x1c"),  # Python's strip() would remove \x1c; JS does not
        ("\x85x", "\x85x"),  # NEL: Python whitespace, not JS whitespace
        ("\u3000x\u00a0", "x"),
    ],
)
def test_js_trim(raw: str, expected: str) -> None:
    assert js_trim(raw) == expected


def test_default_sort_compares_utf16_code_units() -> None:
    items = ["\uffff", "\U0001f600", "b", "a"]
    # Code-point order would put U+FFFF before U+1F600; UTF-16 order puts the surrogate D83D first.
    assert sorted(items, key=js_default_sort_key) == ["a", "b", "\U0001f600", "\uffff"]


def test_entries_sort_uses_array_string_not_key() -> None:
    entries = [("work", [object()]), ("work+x", [object()])]
    # String(["work", [...]]) = "work,[object Object]"; "+" (0x2B) sorts before "," (0x2C).
    assert [k for k, _ in js_sort_entries(entries)] == ["work+x", "work"]


def test_reinjection_domain_order_follows_js_sort() -> None:
    hmem = HMEM(clock=lambda: 1_750_000_000_000)
    hmem.add("deploy notes for the alpha service", tags=["project:work"], source="t")
    hmem.add("deploy notes for the beta service", tags=["project:work+x"], source="t")
    ctx = hmem.query("deploy notes service", threshold=0, top_n=10).context
    assert ctx.index("## work+x") < ctx.index("## work\n")


def test_ascii_id_guard() -> None:
    assert assert_ascii_id("mem-12") == "mem-12"
    with pytest.raises(ValueError):
        assert_ascii_id("mem-\u00e9")
