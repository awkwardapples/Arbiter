"""H-MEM conformance: a 1:1 Python port of Meterless `engines/hmem/conformance/runner.ts`.

Same vectors (byte-identical copy in `vendor/meterless/hmem_vectors.json`), same case ids,
same assertions and messages, same `approx` epsilon. Run with `-s` to see the scorecard.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.p2a

ROOT = Path(__file__).resolve().parents[2]
VECTORS_PATH = ROOT / "vendor" / "meterless" / "hmem_vectors.json"
DAY = 24 * 60 * 60 * 1000
SECTIONS = (
    "record-validation",
    "feedback-deltas",
    "ranking-order",
    "sleep-guardrails",
    "conflict-gate",
    "ledger-audit",
    "dream-boundary",
)
EXPECTED_COUNTS = {
    "record-validation": 2,
    "feedback-deltas": 5,
    "ranking-order": 2,
    "sleep-guardrails": 1,
    "conflict-gate": 1,
    "ledger-audit": 1,
    "dream-boundary": 1,
}


class ConformanceFailure(AssertionError):
    pass


def load_vectors() -> dict[str, Any]:
    return json.loads(VECTORS_PATH.read_text(encoding="utf-8"))


def approx(a: float | None, b: float, eps: float = 1e-9) -> bool:
    return a is not None and abs(a - b) < eps


def check(cond: Any, msg: str) -> None:
    if not cond:
        raise ConformanceFailure(msg)


# Extra keyword arguments passed to every add(); P2-T5 uses this to inject agent fields.
AddExtras = dict[str, Any]


def _record_validation(hmem_cls: type, t0: int, c: dict, extra: AddExtras) -> None:
    hmem = hmem_cls(clock=lambda: t0)
    rejected = False
    try:
        hmem.add(c["input"]["content"], source=c["input"].get("source"), **extra)
    except Exception:
        rejected = True
    check(
        rejected == (c["expect"] == "reject"),
        f"expected {c['expect']}, got {'reject' if rejected else 'accept'}",
    )


def _feedback_deltas(hmem_cls: type, t0: int, c: dict, extra: AddExtras) -> None:
    hmem = hmem_cls(clock=lambda: t0)
    m = hmem.add("feedback target record", confidence=c["start"], source="conformance", **extra)
    access_before = m.access_count
    hmem.feedback(m.id, c["kind"])
    after = hmem.store.get(m.id)
    check(
        approx(after.confidence, c["expectConfidence"]),
        f"confidence {after.confidence}, expected {c['expectConfidence']}",
    )
    if c.get("expectAccessDelta") is not None:
        delta = after.access_count - access_before
        check(
            delta == c["expectAccessDelta"], f"accessCount delta {delta}, expected {c['expectAccessDelta']}"
        )
    if c.get("expectTag"):
        check(c["expectTag"] in after.tags, f"missing tag {c['expectTag']}")


def _ranking_order(hmem_cls: type, t0: int, c: dict, extra: AddExtras) -> None:
    hmem = hmem_cls(clock=lambda: t0)
    by_key: dict[str, Any] = {}
    for r in c["records"]:
        by_key[r["key"]] = hmem.add(
            r["content"], confidence=r.get("confidence"), layer=r.get("layer"), source="conformance", **extra
        )
    for r in c["records"]:
        if r.get("supersededByKey"):
            by_key[r["key"]].superseded_by = by_key[r["supersededByKey"]].id
    result = hmem.query(c["query"], threshold=0, top_n=10)
    order = [m.memory.id for m in result.memories]
    expected = [by_key[k].id for k in c["expectOrder"]]
    for i in range(len(expected) - 1):
        a = order.index(expected[i]) if expected[i] in order else -1
        b = order.index(expected[i + 1]) if expected[i + 1] in order else -1
        check(
            a < b,
            f"expected {c['expectOrder'][i]} before {c['expectOrder'][i + 1]}, got [{', '.join(order)}]",
        )


def _sleep_guardrails(hmem_cls: type, t0: int, c: dict, extra: AddExtras) -> None:
    now = [t0]
    hmem = hmem_cls(clock=lambda: now[0])
    by_key: dict[str, Any] = {}
    for r in c["records"]:
        by_key[r["key"]] = hmem.add(
            r["content"], source=r.get("source"), derived_from=r.get("derivedFrom"), **extra
        )
    now[0] = t0 + c["ageDays"] * DAY
    before = json.dumps(sorted(m.id for m in hmem.store.all()))
    preview = hmem.sleep.preview()
    check(json.dumps(sorted(m.id for m in hmem.store.all())) == before, "preview mutated the store")
    for k in c["expectArchived"]:
        check(by_key[k].id in preview.to_archive, f"{k} should be archivable")
    for k in c["expectProtected"]:
        check(by_key[k].id not in preview.to_archive, f"{k} is guardrail-protected and must not archive")
    report = hmem.sleep.execute(preview)
    for k in c["expectProtected"]:
        check(hmem.store.get(by_key[k].id) is not None, f"{k} was deleted despite guardrails")
    check(isinstance(report.backup_id, str) and len(report.backup_id) > 0, "execute must return a backupId")


def _conflict_gate(hmem_cls: type, t0: int, c: dict, extra: AddExtras) -> None:
    hmem = hmem_cls(clock=lambda: t0)
    a = hmem.add(c["a"]["content"], confidence=c["a"]["confidence"], source="conformance", **extra)
    b = hmem.add(c["b"]["content"], confidence=c["b"]["confidence"], source="conformance", **extra)
    found = hmem.conflicts.scan()
    check(len(found) > 0, "opposing always/never pair on similar content must be detected")
    outcome = hmem.conflicts.auto_resolve(found[0])
    check(outcome in ("resolved", "queued"), f"outcome must be resolved or queued, got {outcome}")
    if outcome == "resolved":
        loser = next(
            (m for m in (hmem.store.get(a.id), hmem.store.get(b.id)) if m is not None and m.superseded_by),
            None,
        )
        check(loser is not None, "resolved conflicts must mark the loser supersededBy")
    check(
        hmem.store.get(a.id) is not None and hmem.store.get(b.id) is not None,
        "conflict resolution must never delete records",
    )


def _ledger_audit(hmem_cls: type, t0: int, c: dict, extra: AddExtras) -> None:
    hmem = hmem_cls(clock=lambda: t0)
    m = hmem.add("audited record", confidence=c["start"], source="conformance", **extra)
    hmem.feedback(m.id, c["kind"])
    history = hmem.ledger.history(m.id)
    actions = [h.action for h in history]
    check(
        actions == c["expectActions"],
        f"actions [{','.join(actions)}], expected [{','.join(c['expectActions'])}]",
    )
    fb = history[-1]
    prev = (fb.previous_state or {}).get("confidence")
    new = (fb.new_state or {}).get("confidence")
    check(approx(prev, c["expectPrev"]), f"previousState.confidence {prev}, expected {c['expectPrev']}")
    check(approx(new, c["expectNew"]), f"newState.confidence {new}, expected {c['expectNew']}")


def _dream_boundary(hmem_cls: type, t0: int, c: dict, extra: AddExtras) -> None:
    hmem = hmem_cls(clock=lambda: t0)
    for r in c["records"]:
        hmem.add(r["content"], type=r.get("type"), source="conformance", **extra)
    count_before = len(hmem.store.all())
    proposals = hmem.dreaming.dream()
    check(len(proposals) > 0, "two related preferences must produce at least one proposal")
    check(len(hmem.store.all()) == count_before, "dreaming must not materialize anything before approval")
    created = hmem.dreaming.approve(proposals[0].id)
    if created is not None:
        check(created.layer == "long_term", "approved proposals materialize as long_term")
        check(len(created.derived_from or []) > 0, "approved proposals carry derivedFrom lineage")


CASE_FNS: dict[str, Callable[[type, int, dict, AddExtras], None]] = {
    "record-validation": _record_validation,
    "feedback-deltas": _feedback_deltas,
    "ranking-order": _ranking_order,
    "sleep-guardrails": _sleep_guardrails,
    "conflict-gate": _conflict_gate,
    "ledger-audit": _ledger_audit,
    "dream-boundary": _dream_boundary,
}


def iter_cases(vectors: dict[str, Any]) -> list[tuple[str, dict]]:
    return [(section, c) for section in SECTIONS for c in vectors["sections"][section]]


def run_case(section: str, case: dict, t0: int, extra: AddExtras | None = None) -> str | None:
    """Run one vector. Returns None on PASS, the failure detail on FAIL (like runner.ts)."""
    from app.memory.hmem import HMEM

    try:
        CASE_FNS[section](HMEM, t0, case, extra or {})
    except Exception as err:  # the runner records any thrown error as FAIL
        return f"{type(err).__name__}: {err}"
    return None


def run_all(extra: AddExtras | None = None) -> list[tuple[str, str, str, str | None]]:
    """(section, id, description, failure-or-None) for every vector, in runner order."""
    vectors = load_vectors()
    return [
        (section, c["id"], c["description"], run_case(section, c, vectors["clock"], extra))
        for section, c in iter_cases(vectors)
    ]


def format_scorecard(results: list[tuple[str, str, str, str | None]]) -> str:
    lines = ["", "H-MEM conformance: implementation = app.memory.hmem (Python port)"]
    current = ""
    for section, case_id, description, detail in results:
        if section != current:
            current = section
            lines += ["", f"  {current}"]
        lines.append(f"    {'FAIL' if detail else 'PASS'} {case_id} {description}")
        if detail:
            lines.append(f"         {detail}")
    passed = sum(1 for r in results if r[3] is None)
    total = len(results)
    lines += ["", f"  {passed}/{total} checks passed"]
    lines.append(f"H-MEM conformance: {passed}/{total} {'PASS' if passed == total else 'FAIL'}")
    return "\n".join(lines)


_VECTORS = load_vectors()
_RESULTS: list[tuple[str, str, str, str | None]] = []


def test_vector_counts_match_spec() -> None:
    counts = {s: len(_VECTORS["sections"][s]) for s in SECTIONS}
    assert counts == EXPECTED_COUNTS
    assert sum(counts.values()) == 13
    ids = [c["id"] for _, c in iter_cases(_VECTORS)]
    assert len(ids) == len(set(ids)), "duplicate case id"


@pytest.mark.parametrize(
    ("section", "case"), iter_cases(_VECTORS), ids=[c["id"] for _, c in iter_cases(_VECTORS)]
)
def test_conformance(section: str, case: dict) -> None:
    detail = run_case(section, case, _VECTORS["clock"])
    _RESULTS.append((section, case["id"], case["description"], detail))
    assert detail is None, detail


def teardown_module() -> None:
    if _RESULTS:
        print(format_scorecard(_RESULTS))
