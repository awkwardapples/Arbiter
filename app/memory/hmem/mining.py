"""Acquisition pipeline (port of `reference/src/memoryMining.ts`).

The model-free fallback path is the DEFAULT: heuristic sentence extraction preserves capture
continuity with no model available. An optional `miner_fn` accepts an extraction prompt and
returns a strict JSON array of memory strings; its output is parsed robustly (markdown fences
stripped, format noise tolerated). `miner_fn` may be sync (use `mine_*`) or async (use
`amine_*`); the sync methods refuse an async miner rather than start a hidden event loop.
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Awaitable, Callable
from typing import Any

from app.errors import ConfigError
from app.memory.hmem.jsfmt import JS_WS_CLASS, js_json_loads, js_len, js_slice, js_trim
from app.memory.hmem.store import MemoryStoreService
from app.memory.hmem.types import MemoryLayer, MemoryRecord, MemoryType, MiningEventType, Provenance

MinerFn = Callable[[str], str | Awaitable[str]]

EVENT_TYPE_MAP: dict[str, MemoryType] = {
    "chat_message": "general",
    "user_correction": "preference",
    "file_save": "factual",
    "file_open": "general",
    "file_edit": "factual",
    "model_response": "factual",
    "plan_completion": "factual",
}

_SIGNAL = re.compile(
    r"\b(prefer|always|never|decided|chose|choose|use|because|instead|must|should|important|remember)\b",
    re.IGNORECASE | re.ASCII,
)
_SENTENCE_SPLIT = re.compile(rf"(?<=[.!?]){JS_WS_CLASS}+|\n+")
_FENCE_OPEN = re.compile(rf"^```(?:json)?{JS_WS_CLASS}*", re.IGNORECASE | re.ASCII)
_FENCE_CLOSE = re.compile(rf"```{JS_WS_CLASS}*\Z")
_DOCUMENT_WINDOW = 8000  # safe token window, in UTF-16 code units like JS slice()


class MemoryMiningService:
    def __init__(
        self,
        store: MemoryStoreService,
        clock: Callable[[], int],
        miner_fn: MinerFn | None = None,
    ) -> None:
        self._store = store
        self._clock = clock
        self._miner_fn = miner_fn

    def mine_interaction(
        self,
        event: MiningEventType,
        text: str,
        *,
        chat_id: str | None = None,
        layer: MemoryLayer | None = None,
    ) -> list[MemoryRecord]:
        candidates = self._mine_with_model(event, text) if self._miner_fn else self.mine_model_free(text)
        return self._store_interaction(event, candidates, chat_id, layer)

    async def amine_interaction(
        self,
        event: MiningEventType,
        text: str,
        *,
        chat_id: str | None = None,
        layer: MemoryLayer | None = None,
    ) -> list[MemoryRecord]:
        candidates = (
            await self._amine_with_model(event, text) if self._miner_fn else self.mine_model_free(text)
        )
        return self._store_interaction(event, candidates, chat_id, layer)

    def mine_document(self, file_name: str, text: str) -> list[MemoryRecord]:
        truncated = js_slice(text, 0, _DOCUMENT_WINDOW)
        candidates = (
            self._mine_with_model("file_save", truncated)
            if self._miner_fn
            else self.mine_model_free(truncated)
        )
        return self._store_document(file_name, candidates)

    async def amine_document(self, file_name: str, text: str) -> list[MemoryRecord]:
        truncated = js_slice(text, 0, _DOCUMENT_WINDOW)
        if self._miner_fn:
            candidates = await self._amine_with_model("file_save", truncated)
        else:
            candidates = self.mine_model_free(truncated)
        return self._store_document(file_name, candidates)

    def mine_model_free(self, text: str) -> list[str]:
        """Section 4.3 no-model fallback: concise direct summaries as short-term memories."""
        out: list[str] = []
        for part in _SENTENCE_SPLIT.split(text):
            s = js_trim(part)
            if 20 <= js_len(s) <= 300 and _SIGNAL.search(s):
                out.append(s)
        return out[:10]

    def _store_interaction(
        self, event: MiningEventType, candidates: list[str], chat_id: str | None, layer: MemoryLayer | None
    ) -> list[MemoryRecord]:
        default_layer: MemoryLayer = "working" if self._miner_fn else "short_term"
        return [
            self._store.add(
                content,
                type=EVENT_TYPE_MAP[event],
                layer=layer if layer is not None else default_layer,
                tags=[f"event:{event}"],
                source=f"interaction:{event}",
                provenance=Provenance(origin=event, learned_at=self._clock(), label=f"mined from {event}"),
                chat_id=chat_id,
            )
            for content in candidates
        ]

    def _store_document(self, file_name: str, candidates: list[str]) -> list[MemoryRecord]:
        return [
            self._store.add(
                content,
                type="factual",
                layer="working",
                tags=["document", f"file:{file_name}"],
                source=f"document:{file_name}",
            )
            for content in candidates
        ]

    @staticmethod
    def _prompt(event: MiningEventType, text: str) -> str:
        return f"Extract durable memories from this {event} as a strict JSON array of strings:\n\n{text}"

    def _mine_with_model(self, event: MiningEventType, text: str) -> list[str]:
        assert self._miner_fn is not None
        raw: Any = self._miner_fn(self._prompt(event, text))
        if inspect.isawaitable(raw):
            if inspect.iscoroutine(raw):
                raw.close()
            raise ConfigError("H-MEM: miner_fn is async; call the amine_* methods instead")
        return parse_strict_json_array(raw)

    async def _amine_with_model(self, event: MiningEventType, text: str) -> list[str]:
        assert self._miner_fn is not None
        raw: Any = self._miner_fn(self._prompt(event, text))
        if inspect.isawaitable(raw):
            raw = await raw
        return parse_strict_json_array(raw)


def parse_strict_json_array(raw: str) -> list[str]:
    """Robust parsing: strip markdown fences, tolerate minor noise (section 4.1 step 3)."""
    cleaned = js_trim(_FENCE_CLOSE.sub("", _FENCE_OPEN.sub("", js_trim(raw), count=1), count=1))
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    try:
        parsed = js_json_loads(cleaned)
    except ValueError:
        return []
    if not isinstance(parsed, list):
        return []
    return [x for x in parsed if isinstance(x, str) and js_len(js_trim(x)) >= 5]
