"""Grounding: a quote counts only if it appears verbatim (after normalisation) at word boundaries."""

from __future__ import annotations

import re

_DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"), "-")
_QUOTES = {ord("\u2018"): "'", ord("\u2019"): "'", ord("\u201c"): '"', ord("\u201d"): '"'}
_SPACE = re.compile(r"\s+")
_TRAIL = re.compile(r"[\s.,;:!?]+$")


def normalise(text: str) -> str:
    text = text.translate(_DASHES).translate(_QUOTES).casefold()
    return _SPACE.sub(" ", text).strip()


def is_grounded(quote: str, source: str) -> bool:
    needle = _TRAIL.sub("", normalise(quote))
    if not needle:
        return False
    hay = normalise(source)
    start = hay.find(needle)
    while start != -1:
        end = start + len(needle)
        before_ok = start == 0 or not hay[start - 1].isalnum()
        after_ok = end == len(hay) or not hay[end].isalnum()
        if before_ok and after_ok:
            return True
        start = hay.find(needle, start + 1)
    return False
