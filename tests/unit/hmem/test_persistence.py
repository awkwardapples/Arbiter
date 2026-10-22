"""P2-T4: persistence round-trip (Python-written and JS-written state.json)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.memory.hmem import HMEM

pytestmark = pytest.mark.p2a

T0 = 1_750_000_000_000


def _populate(hmem: HMEM) -> list[str]:
    a = hmem.add("we deploy the api with docker on mondays", type="factual", layer="long_term", source="t")
    b = hmem.add("prefer python for scripting", type="preference", source="t", tags=["tech:python"])
    c = hmem.add("Sarah owns the Q2 roadmap review", source="t", confidence=0.9, derived_from=[a.id])
    d = hmem.add("actually we deploy the api with docker on tuesdays", source="t", supersedes=a.id)
    hmem.query("deploy the api with docker", threshold=0)
    hmem.feedback(a.id, "helpful")
    hmem.feedback(b.id, "not_helpful")
    hmem.feedback(c.id, "wrong")
    return [a.id, b.id, c.id, d.id]


def _dump(hmem: HMEM) -> dict[str, dict]:
    return {m.id: m.model_dump(by_alias=True, exclude_none=True) for m in hmem.store.all()}


def test_round_trip_state_and_queries(tmp_path: Path) -> None:
    first = HMEM(clock=lambda: T0, persist_dir=tmp_path)
    ids = _populate(first)
    state = _dump(first)
    ledger = [e.model_dump(by_alias=True, exclude_none=True) for e in first.ledger.all()]

    second = HMEM(clock=lambda: T0, persist_dir=tmp_path)
    assert _dump(second) == state
    assert [e.model_dump(by_alias=True, exclude_none=True) for e in second.ledger.all()] == ledger

    for q in ("deploy the api with docker", "python scripting", "roadmap review"):
        r1 = first.query(q, threshold=0, top_n=10)
        r2 = second.query(q, threshold=0, top_n=10)
        assert [(m.memory.id, m.relevance) for m in r1.memories] == [
            (m.memory.id, m.relevance) for m in r2.memories
        ]
        assert r1.trace == r2.trace
        assert r1.context == r2.context

    assert second.add("a new record after reload", source="t").id == f"mem-{len(ids) + 1}"


def test_state_json_uses_reference_field_names(tmp_path: Path) -> None:
    hmem = HMEM(clock=lambda: T0, persist_dir=tmp_path)
    hmem.add("record with camel case keys", source="t")
    saved = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert saved["seq"] == 1
    rec = saved["records"][0]
    for key in ("lastAccessed", "accessCount", "relatedTo", "provenance"):
        assert key in rec
    assert "learnedAt" in rec["provenance"]
    assert "supersedes" not in rec  # JS drops undefined fields
    assert (tmp_path / "ledger.jsonl").read_text(encoding="utf-8").count("\n") == 1


def test_loads_js_written_state(tmp_path: Path) -> None:
    js_state = {
        "seq": 2,
        "records": [
            {
                "id": "mem-1",
                "content": "js written record",
                "type": "general",
                "layer": "working",
                "timestamp": T0,
                "lastAccessed": T0,
                "accessCount": 0,
                "tags": [],
                "embedding": [0] * 63 + [1],
                "confidence": 1,
                "source": "js",
                "provenance": {"origin": "manual", "learnedAt": T0, "label": "js"},
                "domain": "general",
                "namespace": "general/notes",
                "entities": [],
                "relatedTo": [],
            },
            {
                "id": "mem-2",
                "content": "second js record",
                "type": "factual",
                "layer": "long_term",
                "timestamp": T0,
                "lastAccessed": T0,
                "accessCount": 3,
                "tags": ["x"],
                "embedding": [1] + [0] * 63,
                "confidence": 0.5,
                "source": "js",
                "provenance": {"origin": "manual", "learnedAt": T0, "label": "js"},
                "domain": "general",
                "namespace": "general/facts",
                "entities": [],
                "relatedTo": ["mem-1"],
                "supersededBy": "mem-1",
                "derivedFrom": ["mem-1"],
            },
        ],
    }
    (tmp_path / "state.json").write_text(json.dumps(js_state, indent=2) + "\n", encoding="utf-8")
    hmem = HMEM(clock=lambda: T0, persist_dir=tmp_path)
    m1, m2 = hmem.store.get("mem-1"), hmem.store.get("mem-2")
    assert m1 is not None and m1.confidence == 1.0 and m1.embedding[-1] == 1.0
    assert m2 is not None and m2.superseded_by == "mem-1" and m2.derived_from == ["mem-1"]

    hmem.store.persist()
    reloaded = HMEM(clock=lambda: T0, persist_dir=tmp_path)
    assert _dump(reloaded) == _dump(hmem)
    assert reloaded.add("third", source="t").id == "mem-3"
