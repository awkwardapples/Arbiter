"""P2-T2: FNV-1a, tokenizer and deterministic embeddings (plus the optional Node golden check)."""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest

from app.memory.hmem.embeddings import DIM, cosine, embed, fnv1a, jaccard, tokenize

pytestmark = pytest.mark.p2a

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ("text", "expected"),
    [("", 0x811C9DC5), ("a", 0xE40C292C), ("foobar", 0xBF9CF968)],
)
def test_fnv1a_known_vectors(text: str, expected: int) -> None:
    assert fnv1a(text) == expected


def test_fnv1a_hashes_utf16_code_units() -> None:
    h = 0x811C9DC5
    for unit in (0xD83D, 0xDE00):  # U+1F600 as a surrogate pair, as JS charCodeAt sees it
        h ^= unit
        h = (h * 0x01000193) & 0xFFFFFFFF
    assert fnv1a("\U0001f600") == h


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hello, World! a b2 C++", ["hello", "world", "b2"]),
        ("foo\ufeffbar", ["foo", "bar"]),
        ("foo\x1cbar", ["foo", "bar"]),
        ("café au lait", ["caf", "au", "lait"]),
        ("  ", []),
    ],
)
def test_tokenize(text: str, expected: list[str]) -> None:
    assert tokenize(text) == expected


@pytest.mark.parametrize("text", ["we deploy the api with docker", "prefer short bullet answers", "x y z"])
def test_embed_is_unit_length_or_zero(text: str) -> None:
    v = embed(text)
    assert len(v) == DIM
    norm = math.sqrt(sum(x * x for x in v))
    assert norm == 0 or abs(norm - 1) < 1e-12


def test_embed_zero_when_no_tokens() -> None:
    assert embed("") == [0.0] * DIM
    assert embed("a !") == [0.0] * DIM


def test_embed_is_deterministic() -> None:
    text = "precedent control c05 mitigation bridge letter tier t2"
    assert embed(text) == embed(text)
    assert abs(cosine(embed(text), embed(text)) - 1) < 1e-12


def test_jaccard() -> None:
    assert jaccard([], ["a"]) == 0
    assert jaccard(["a", "b"], ["b", "c"]) == 1 / 3
    assert jaccard(["a", "a"], ["a"]) == 1


def _load_golden():
    spec = importlib.util.spec_from_file_location("hmem_golden", ROOT / "scripts" / "dev" / "hmem_golden.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_golden_strings_are_fixed() -> None:
    golden = _load_golden()
    assert len(golden.golden_strings()) == 50
    assert golden.golden_strings() == golden.golden_strings()


def test_embed_matches_typescript_reference() -> None:
    golden = _load_golden()
    reason = golden.unavailable_reason()
    if reason:
        pytest.skip(f"TS golden check unavailable: {reason}")
    assert golden.compare(golden.golden_strings()) == []
