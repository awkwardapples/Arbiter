"""P2-T10: jsonparse finds the first balanced JSON value and validates it."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, RootModel

from app.errors import ParseFailure
from app.llm import jsonparse

pytestmark = pytest.mark.p2b


class Item(BaseModel):
    a: int
    s: str = ""


class Inner(BaseModel):
    b: list[int]


class Nested(BaseModel):
    a: int
    inner: Inner


Items = RootModel[list[Item]]


@pytest.mark.parametrize(
    ("text", "a", "s"),
    [
        ('```json\n{"a": 1}\n```', 1, ""),
        ('```\n{"a": 2}\n```', 2, ""),
        ('{"a": 3}', 3, ""),
        ('  {"a": 4}\n', 4, ""),
        ('Sure, here it is: {"a": 5} Let me know if you need more.', 5, ""),
        ('{"a": 6, "s": "x } y { z"}', 6, "x } y { z"),
        ('{"a": 7, "s": "he said \\"hi }\\" twice"}', 7, 'he said "hi }" twice'),
        ('{"a": 8, "s": "back\\\\slash"}', 8, "back\\slash"),
        ('Answer:\n```json\n{"a": 9, "s": "```"}\n```\nDone.', 9, "```"),
    ],
)
def test_p2_t10_passes(text: str, a: int, s: str) -> None:
    model, raw = jsonparse.parse(text, Item)
    assert isinstance(model, Item)
    assert (model.a, model.s) == (a, s)
    assert raw.startswith("{") and raw.endswith("}")


def test_p2_t10_raw_json_no_fence_is_returned_verbatim() -> None:
    text = '{"a": 1, "s": "plain"}'
    model, raw = jsonparse.parse(text, Item)
    assert raw == text
    assert model.s == "plain"


def test_p2_t10_nested_objects() -> None:
    model, raw = jsonparse.parse('result: {"a": 1, "inner": {"b": [1, 2, 3]}} end', Nested)
    assert model.inner.b == [1, 2, 3]
    assert raw == '{"a": 1, "inner": {"b": [1, 2, 3]}}'


def test_p2_t10_arrays() -> None:
    model, raw = jsonparse.parse('Here: [{"a": 1}, {"a": 2, "s": "]"}] thanks', Items)
    assert [i.a for i in model.root] == [1, 2]
    assert model.root[1].s == "]"
    assert raw.startswith("[") and raw.endswith("]")


def test_p2_t10_extract_json_returns_first_balanced_value() -> None:
    assert jsonparse.extract_json('x {"a": {"b": 1}} y {"c": 2}') == '{"a": {"b": 1}}'


@pytest.mark.parametrize(
    "text",
    [
        '{"a": 1',
        '{"a": 1, "s": "unterminated}',
        '{bad} {"a": 1}',
        "",
        "   ",
        "no json here at all",
        '{"a": "not-an-int"}',
        '{"s": "missing a"}',
    ],
)
def test_p2_t10_failures(text: str) -> None:
    with pytest.raises(ParseFailure) as exc_info:
        jsonparse.parse(text, Item)
    errors = getattr(exc_info.value, "errors", None)
    assert isinstance(errors, list) and errors
    assert all(isinstance(e, str) and e for e in errors)
