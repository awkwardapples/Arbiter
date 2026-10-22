"""Service behaviour outside the conformance vectors: mining, reinjection, sleep, dreaming, conflicts."""

from __future__ import annotations

import asyncio

import pytest

from app.errors import ConfigError, NotFound, ValidationFailed
from app.memory.hmem import DAY_MS, HMEM, parse_strict_json_array

pytestmark = pytest.mark.p2a

T0 = 1_750_000_000_000


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('```json\n["remember the build uses pnpm"]\n```', ["remember the build uses pnpm"]),
        (
            'Sure! Here you go: ["alpha beta", "x", 3, "gamma delta"] hope it helps',
            ["alpha beta", "gamma delta"],
        ),
        ('{"a": "not an array"}', []),
        ("[NaN]", []),
        ("not json at all", []),
    ],
)
def test_parse_strict_json_array(raw: str, expected: list[str]) -> None:
    assert parse_strict_json_array(raw) == expected


def test_model_free_mining_is_short_term_and_filters_signal() -> None:
    hmem = HMEM(clock=lambda: T0)
    text = (
        "We always deploy with docker because it is reproducible. Short. The sky is blue today, nothing more."
    )
    mined = hmem.mine("chat_message", text, chat_id="c1")
    assert [m.content for m in mined] == ["We always deploy with docker because it is reproducible."]
    m = mined[0]
    assert (m.layer, m.type, m.source, m.chat_id) == (
        "short_term",
        "general",
        "interaction:chat_message",
        "c1",
    )
    assert m.provenance.origin == "chat_message" and m.tags == ["event:chat_message"]


def test_model_mining_sync_and_async() -> None:
    hmem = HMEM(clock=lambda: T0, miner_fn=lambda prompt: '["prefer short bullet answers"]')
    mined = hmem.mine("user_correction", "anything")
    assert [(m.content, m.layer, m.type) for m in mined] == [
        ("prefer short bullet answers", "working", "preference")
    ]

    async def miner(prompt: str) -> str:
        assert prompt.startswith("Extract durable memories from this file_save")
        return '["the api runs on port 8000"]'

    async_hmem = HMEM(clock=lambda: T0, miner_fn=miner)
    with pytest.raises(ConfigError):
        async_hmem.mine("file_save", "x")
    docs = asyncio.run(async_hmem.mining.amine_document("notes.md", "body"))
    assert [(d.source, d.tags) for d in docs] == [("document:notes.md", ["document", "file:notes.md"])]


def test_query_trace_context_and_chat_scope() -> None:
    hmem = HMEM(clock=lambda: T0)
    hmem.add("we deploy the api with docker", source="t", layer="long_term", chat_id="a")
    hmem.add("we deploy the api with docker on fridays", source="t", chat_id="b")
    res = hmem.query("deploy the api with docker", threshold=0, chat_id="a")
    assert [m.memory.id for m in res.memories] == ["mem-1"]
    assert res.trace.strategy == "minimal"
    assert res.trace.retrieval_reason == 'hybrid ranking for "deploy the api with docker" (domain: tech)'
    assert res.context.splitlines() == [
        "[MEMORY CONTEXT]",
        "## tech",
        "- [LT] we deploy the api with docker (entities: docker) <mem-1>",
        "[/MEMORY CONTEXT]",
    ]
    assert hmem.store.get("mem-1").access_count == 1
    assert [e.action for e in hmem.ledger.history("mem-1")] == ["create", "read"]


def test_enrichment_supersedes_and_related() -> None:
    hmem = HMEM(clock=lambda: T0)
    a = hmem.add("we deploy the api with docker on mondays", source="t")
    b = hmem.add("actually we deploy the api with docker on mondays", source="t")
    c = hmem.add("Docker images are rebuilt nightly by the api server", source="t")
    assert b.supersedes == a.id
    assert a.id in c.related_to and c.id in a.related_to


def test_sleep_execute_and_restore() -> None:
    now = [T0]
    hmem = HMEM(clock=lambda: now[0])
    st = hmem.add("short term note about lunch plans", source="t", layer="short_term")
    dup1 = hmem.add("the deploy window is monday morning", source="t", layer="long_term")
    dup2 = hmem.add("the deploy window is monday morning", source="t", layer="long_term")
    now[0] = T0 + 8 * DAY_MS
    preview = hmem.sleep.preview()
    assert preview.to_consolidate == [st.id]
    assert [dup1.id, dup2.id] in preview.to_synthesize
    report = hmem.sleep.execute(preview)
    assert report.consolidated == 1 and report.synthesized == 1
    assert hmem.store.get(dup1.id) is None
    merged = [m for m in hmem.store.all() if m.source == "sleep:synthesis"]
    assert len(merged) == 1 and merged[0].derived_from == [dup1.id, dup2.id]

    hmem.sleep.restore(report.backup_id)
    assert hmem.store.get(dup1.id) is not None and hmem.store.get(st.id).layer == "short_term"
    assert hmem.ledger.all()[-1].memory_id == "*"
    with pytest.raises(NotFound):
        hmem.sleep.restore("backup-999")


def test_dream_reject_and_domain_approval() -> None:
    hmem = HMEM(clock=lambda: T0)
    hmem.add("prefer short bullet answers", type="preference", source="t")
    hmem.add("prefer python for scripting", type="preference", source="t")
    proposals = hmem.dreaming.dream()
    hmem.dreaming.reject(proposals[0].id)
    assert proposals[0].status == "rejected"
    with pytest.raises(NotFound):
        hmem.dreaming.approve(proposals[0].id)

    m = hmem.add("tag says otherwise", tags=["tech:x"], source="t")
    hmem.store.update(m.id, domain="general")
    domain_props = [p for p in hmem.dreaming.dream() if p.type == "domain"]
    assert domain_props and domain_props[0].suggested_domain == "tech"
    assert hmem.dreaming.approve(domain_props[0].id) is None
    assert hmem.store.get(m.id).domain == "tech"


def test_conflict_queued_below_gate() -> None:
    hmem = HMEM(clock=lambda: T0)
    hmem.add("always enable telemetry uploads for diagnostics", confidence=0.7, source="t")
    hmem.add("never enable telemetry uploads for diagnostics", confidence=0.7, source="t")
    found = hmem.conflicts.scan()
    assert found and found[0].reason == "opposing phrase pair on similar content"
    assert hmem.conflicts.auto_resolve(found[0]) == "queued"
    assert hmem.conflicts.queue() == [found[0]]
    assert all(m.superseded_by is None for m in hmem.store.all())


def test_errors_are_typed() -> None:
    hmem = HMEM(clock=lambda: T0)
    with pytest.raises(ValidationFailed):
        hmem.add("x", source="   ")
    with pytest.raises(NotFound):
        hmem.feedback("mem-404", "helpful")
    m = hmem.add("record", source="t")
    with pytest.raises(ValidationFailed):
        hmem.store.update(m.id, not_a_field=1)
    with pytest.raises(ValidationFailed):
        hmem.feedback(m.id, "meh")  # type: ignore[arg-type]
