"""Robust JSON extraction from model output: fences, prose, then the first balanced value."""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, ValidationError

from app.errors import ParseFailure

_FENCE_OPEN = re.compile(r"```[A-Za-z0-9_-]*[ \t]*\r?\n")
_PAIRS = {"{": "}", "[": "]"}


def _failure(errors: list[str]) -> ParseFailure:
    exc = ParseFailure("; ".join(errors))
    exc.errors = errors  # type: ignore[attr-defined]
    return exc


def _balanced_end(text: str, start: int) -> int | None:
    """Index just past the value opened at `start`, respecting strings and escapes."""
    stack = [_PAIRS[text[start]]]
    in_string = False
    escaped = False
    for i in range(start + 1, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in _PAIRS:
            stack.append(_PAIRS[ch])
        elif ch in "}]":
            if ch != stack[-1]:
                return None
            stack.pop()
            if not stack:
                return i + 1
    return None


def extract_json(text: str) -> str:
    """Return the first balanced JSON object or array in `text` (after an opening fence, if any)."""
    if not text or not text.strip():
        raise _failure(["empty model output"])
    fence = _FENCE_OPEN.search(text)
    offset = fence.end() if fence else 0
    starts = [i for i in (text.find("{", offset), text.find("[", offset)) if i != -1]
    if not starts:
        raise _failure(["no JSON object or array found"])
    start = min(starts)
    end = _balanced_end(text, start)
    if end is None:
        raise _failure([f"unbalanced or truncated JSON starting at offset {start}"])
    return text[start:end]


def parse[T: BaseModel](text: str, schema: type[T]) -> tuple[T, str]:
    """Extract, decode and validate. Returns `(model, raw_json)`; raises `ParseFailure(errors)`."""
    raw = extract_json(text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise _failure([f"invalid JSON: {exc.msg} at offset {exc.pos}"]) from None
    try:
        return schema.model_validate(data), raw
    except ValidationError as exc:
        errors = [f"{'.'.join(str(p) for p in err['loc']) or '<root>'}: {err['msg']}" for err in exc.errors()]
        raise _failure(errors or ["schema validation failed"]) from None
