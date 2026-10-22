"""Tri-state condition DSL. No eval."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.errors import PolicyError
from app.schemas.common import TriState
from app.schemas.evidence import Fact

LEAF_OPS = frozenset(
    {
        "is_true",
        "is_false",
        "eq",
        "ne",
        "lte",
        "gte",
        "lt",
        "gt",
        "in",
        "not_in",
        "in_any",
        "subset_of",
        "exists",
    }
)
_LIST_OPS = frozenset({"in", "not_in", "in_any", "subset_of"})


def evaluate(rule: Mapping[str, Any], facts: dict[str, Fact]) -> TriState:
    if "all" in rule:
        return _combine(rule["all"], facts, false_wins=True)
    if "any" in rule:
        return _combine(rule["any"], facts, false_wins=False)
    if "op" in rule and "fact" in rule:
        return _leaf(rule, facts)
    raise PolicyError("invalid rule")


def referenced_keys(rule: Mapping[str, Any]) -> list[str]:
    found: list[str] = []
    _collect_keys(rule, found)
    return found


def _combine(children: list[Mapping[str, Any]], facts: dict[str, Fact], *, false_wins: bool) -> TriState:
    stop = "FALSE" if false_wins else "TRUE"
    saw_unknown = False
    for child in children:
        state = evaluate(child, facts)
        if state == stop:
            return stop
        if state == "UNKNOWN":
            saw_unknown = True
    if saw_unknown:
        return "UNKNOWN"
    return "TRUE" if false_wins else "FALSE"


def _leaf(rule: Mapping[str, Any], facts: dict[str, Fact]) -> TriState:
    op = str(rule["op"])
    if op not in LEAF_OPS:
        raise PolicyError(f"unknown op: {op}")
    fact = facts.get(str(rule["fact"]))
    if fact is None or fact.state == "UNKNOWN":
        return "UNKNOWN"
    if op == "exists":
        return "TRUE"
    if op == "is_true":
        return "TRUE" if fact.state == "TRUE" else "FALSE"
    if op == "is_false":
        return "TRUE" if fact.state == "FALSE" else "FALSE"
    if fact.value is None:
        return "UNKNOWN"
    value = rule.get("value")
    if op in _LIST_OPS and not isinstance(value, list):
        return "UNKNOWN"
    if op == "eq":
        return _tri(_equal(fact.value, value))
    if op == "ne":
        return _tri(not _equal(fact.value, value))
    if op == "in":
        return _tri(any(_equal(fact.value, item) for item in value))
    if op == "not_in":
        return _tri(all(not _equal(fact.value, item) for item in value))
    if op in {"lt", "lte", "gt", "gte"}:
        return _compare(fact.value, value, op)
    items = fact.value if isinstance(fact.value, list) else None
    if items is None:
        return "UNKNOWN"
    if op == "in_any":
        return _tri(any(_equal(item, allowed) for item in items for allowed in value))
    return _tri(all(any(_equal(item, allowed) for allowed in value) for item in items))


def _compare(left: Any, right: Any, op: str) -> TriState:
    number_left = _number(left)
    number_right = _number(right)
    if number_left is None or number_right is None:
        return "UNKNOWN"
    if op == "lt":
        return _tri(number_left < number_right)
    if op == "lte":
        return _tri(number_left <= number_right)
    if op == "gt":
        return _tri(number_left > number_right)
    return _tri(number_left >= number_right)


def _equal(left: Any, right: Any) -> bool:
    number_left = _number(left)
    number_right = _number(right)
    if number_left is not None and number_right is not None:
        return number_left == number_right
    return bool(left == right)


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _tri(flag: bool) -> TriState:
    return "TRUE" if flag else "FALSE"


def _collect_keys(rule: Mapping[str, Any], found: list[str]) -> None:
    if "all" in rule:
        for child in rule["all"]:
            _collect_keys(child, found)
        return
    if "any" in rule:
        for child in rule["any"]:
            _collect_keys(child, found)
        return
    if "fact" in rule:
        found.append(str(rule["fact"]))
