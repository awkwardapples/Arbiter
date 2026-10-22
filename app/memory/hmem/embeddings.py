"""Deterministic mock embedder (port of `reference/src/embeddings.ts`).

FNV-1a hash per token into a 64-dim vector, summed and L2-normalised. A pure function of
the input text, so retrieval scores are reproducible across runs and machines.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable

from app.memory.hmem.jsfmt import imul32, utf16_units

DIM = 64

# JS: lower-case, replace [^a-z0-9\s] with " ", split on \s+, keep tokens longer than 1.
# Every surviving character is in [a-z0-9] or is whitespace, so the tokens are exactly the
# maximal [a-z0-9] runs, whichever whitespace definition is used.
_WORD_RUN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return [t for t in _WORD_RUN.findall(text.lower()) if len(t) > 1]


def fnv1a(s: str) -> int:
    h = 0x811C9DC5
    for unit in utf16_units(s):
        h ^= unit
        h = imul32(h, 0x01000193)
    return h


def embed(text: str) -> list[float]:
    vec = [0.0] * DIM
    for token in tokenize(text):
        h = fnv1a(token)
        idx = h % DIM
        sign = 1 if (h >> 8) % 2 == 0 else -1
        mag = 1 + ((h >> 16) % 8) / 8
        vec[idx] += sign * mag
    total = 0.0
    for v in vec:
        total += v * v
    norm = math.sqrt(total)
    return vec if norm == 0 else [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    """Dot product; both vectors are unit length. A shorter `b` gives NaN, as in JS."""
    if len(b) < len(a):
        return math.nan
    dot = 0.0
    for i in range(len(a)):
        dot += a[i] * b[i]
    return dot


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0
    inter = sum(1 for x in sa if x in sb)
    return inter / (len(sa) + len(sb) - inter)
