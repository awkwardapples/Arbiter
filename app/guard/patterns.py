"""Deterministic Scout-style injection pattern detectors."""

from __future__ import annotations

import re
from typing import Any, NamedTuple

# Scores at or above this value block; benign look-alikes stay below 0.7.
BLOCK_THRESHOLD = 0.7
AMBIGUOUS_LOW = 0.3


class PatternHit(NamedTuple):
    kind: str
    score: float
    evidence_meta: dict[str, Any]


_SNAKE = re.compile(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b")

_INSTRUCTION_STRONG = re.compile(
    r"(?i)\b("
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|rules|guidance)"
    r"|disregard\s+(the\s+)?(rules|instructions|guidance)\s+above"
    r"|forget\s+(all\s+)?(previous|prior)\s+(instructions|rules)"
    r"|you\s+are\s+now"
    r"|unrestricted\s+mode"
    r")\b"
)

_INSTRUCTION_WEAK = re.compile(r"(?i)\bignore\b.{0,40}\b(previous|prior|earlier)\b")

_BENIGN_SUPERSEDE = re.compile(
    r"(?i)\bignore\b.{0,60}\b(previous|prior|earlier)\b.{0,60}\b("
    r"versions?|policy|superseded|deprecated|release)"
)

_ROLE = re.compile(r"(?i)(</?system>|</?user>|\[INST\]|pretend\s+to\s+be\s+the\s+system)")

_HIDDEN = re.compile(
    r"(<!--|display\s*:\s*none|[\u200b-\u200d\ufeff]|[\u202a-\u202e\ufeff]|[\u2066-\u2069])",
    re.UNICODE,
)
_LITERAL_ESCAPES = re.compile(r"\\u(200[B-D]|2060|202[A-E]|206[6-9])", re.IGNORECASE)

_ADMIN_TOOL = re.compile(r"(?i)\b(internal_admin_panel|admin\s+panel|grant\s+me)\b")

_USER_OVERRIDE = re.compile(
    r"(?i)\b(disregard|ignore)\s+the\s+user\b"
    r"|\b(disregard|ignore)\s+(all|any)\s+(prior|earlier)\s+(guidance|direction)\b"
)

_SECRET_EXFIL = re.compile(
    r"(?i)\b(reveal|dump|print|show|list|send)\b.{0,80}\b("
    r"credentials|api\s+keys?|secrets?|tokens?|passwords?)\b"
)

_ADDRESSED_AI = re.compile(r"(?i)(note\s+to\s+ai\s+reviewers|\bassistant\s*:|^LLM\s*:)")


def _tool_reference_score(text: str, capabilities: set[str]) -> PatternHit | None:
    for match in _SNAKE.finditer(text):
        name = match.group(1)
        if name in capabilities:
            continue
        if name.endswith("_panel") or name.startswith("internal_") or "admin" in name:
            return PatternHit(
                "out_of_band_tool",
                0.85,
                {"token": name, "reason": "admin_like_tool"},
            )
        if name in {"approve_vendor", "grant_admin", "dump_secrets", "export_all_data"}:
            return PatternHit("out_of_band_tool", 0.82, {"token": name})
    if _ADMIN_TOOL.search(text):
        return PatternHit("out_of_band_tool", 0.85, {"reason": "admin_phrase"})
    return None


def scan(text: str, *, capabilities: set[str]) -> list[PatternHit]:
    hits: list[PatternHit] = []
    if _INSTRUCTION_STRONG.search(text):
        hits.append(PatternHit("instruction_override", 0.92, {"layer": "strong"}))
    elif _BENIGN_SUPERSEDE.search(text):
        hits.append(PatternHit("instruction_override", 0.25, {"layer": "benign_supersede"}))
    elif _INSTRUCTION_WEAK.search(text):
        hits.append(PatternHit("instruction_override", 0.55, {"layer": "weak"}))

    if _ROLE.search(text):
        hits.append(PatternHit("role_confusion", 0.9, {}))

    if _HIDDEN.search(text) or _LITERAL_ESCAPES.search(text):
        hits.append(PatternHit("hidden_markup", 0.88, {}))

    tool = _tool_reference_score(text, capabilities)
    if tool:
        hits.append(tool)

    if _USER_OVERRIDE.search(text):
        hits.append(PatternHit("user_role_override", 0.85, {}))

    if _SECRET_EXFIL.search(text):
        hits.append(PatternHit("secret_exfiltration", 0.88, {}))

    if _ADDRESSED_AI.search(text):
        hits.append(PatternHit("addressed_to_ai", 0.75, {}))

    # Literal bidi escape without decoded char (Scout inj-control-bytes-001)
    if re.search(r"\\u202[eE]", text) and re.search(r"(?i)(ignore|grant|admin)", text):
        hits.append(PatternHit("hidden_markup", 0.9, {"literal_unicode_escape": True}))

    if (
        re.search(r"(?i)grant\s+admin", text)
        and "hidden_markup" not in {h.kind for h in hits}
        and "\\u202" in text.lower()
    ):
        hits.append(PatternHit("hidden_markup", 0.88, {"combo": "bidi_admin"}))

    return hits


def max_score(hits: list[PatternHit]) -> float:
    if not hits:
        return 0.0
    return max(h.score for h in hits)
