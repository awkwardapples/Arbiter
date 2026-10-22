"""Rule-based claim extraction per questionnaire item. Pure; quotes are exact source sentences."""

from __future__ import annotations

import re
from collections.abc import Callable

from app.llm.prompts.schemas import ExtractedClaim
from app.schemas.common import TriState

EXTRACTOR_ID = "deterministic:v1"

_SENTENCE = re.compile(r"\S.*?(?:[.!?]+(?=\s|$)|$)", re.DOTALL)
_HEDGE = re.compile(
    r"\b(planned|plans? to|roadmap|next year|q[1-4]|in progress|aim to|will be|pilot(?:ing)?|"
    r"intend to|working towards|being rolled out|rolling out|next (?:quarter|month)|later this year)\b",
    re.IGNORECASE,
)
_VAGUE = re.compile(
    r"\b(industry[- ]standard|where appropriate|as needed|best practices?|appropriately|"
    r"reasonable measures|commercially reasonable)\b",
    re.IGNORECASE,
)
_DOUBLE_NEGATION = re.compile(
    r"\b(no longer (?:allow|permit|accept)\w*\s+password[- ]only|not only\b.*\bbut)\b",
    re.IGNORECASE,
)
_NEGATION = re.compile(
    r"\b(not|no|never|don't|do not|does not|doesn't|isn't|aren't|cannot|can't|won't|unable to)\b",
    re.IGNORECASE,
)
_NO_EXCEPTION = re.compile(r"\bno exceptions?\b|\bwithout exception\b", re.IGNORECASE)
_AFFIRM = re.compile(
    r"\b(yes|enforced|enforce[sd]?|required|requires?|mandatory|always|must|uses?|includes?|"
    r"encrypt(?:ed|s)?|minimum|disclosed?|publish(?:ed)?|list|sign(?:ed)?|commit(?:ted)?|"
    r"execut(?:e|ed|ing)|accept|agree|all|every)\b",
    re.IGNORECASE,
)

_MFA = r"\b(mfa|multi[- ]factor|2fa|two[- ]factor)\b"
# question id -> (key, topic regex for sentence selection, object regex required for TRUE)
_BOOLEAN: dict[str, tuple[str, str, str]] = {
    "Q01": ("mfa.admin_enforced", _MFA + r"|\b(admin\w*|privileged)\b", _MFA),
    "Q02": ("mfa.remote_enforced", _MFA + r"|\bremote\b", _MFA),
    "Q05": ("crypto.at_rest", r"\b(encrypt\w*|at rest|aes[- ]?\d*|stored)\b", r"\b(encrypt\w*|aes)"),
    "Q06": (
        "crypto.in_transit_tls12",
        r"\b(tls|transit|ssl|connections?|traffic|encrypt\w*)\b",
        r"\b(tls|encrypt\w*)",
    ),
    "Q12": ("subprocessors.disclosed_claimed", r"\bsub[- ]?processors?\b", r"\bsub[- ]?processors?\b"),
    "Q15": (
        "dpa.vendor_commits",
        r"\b(dpa|data processing agreement)\b",
        r"\b(dpa|data processing agreement)\b",
    ),
}

_WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fourteen": 14, "thirty": 30,
}  # fmt: skip
_NUMBER = r"(\d+|" + "|".join(_WORD_NUMBERS) + r")"
_PERIOD_DAYS = {"daily": 1, "weekly": 7, "monthly": 30, "quarterly": 90, "annually": 365, "yearly": 365}

_REGIONS: list[tuple[str, str, int]] = [
    ("EU", r"\b(EU|E\.U\.)\b", 0),
    ("EU", r"\b(european union|frankfurt|dublin|amsterdam|paris|ireland|germany)\b", re.IGNORECASE),
    ("UK", r"\b(UK|U\.K\.)\b", 0),
    ("UK", r"\b(united kingdom|london|great britain)\b", re.IGNORECASE),
    ("US", r"\b(US|USA|U\.S\.)\b", 0),
    ("US", r"\b(united states|virginia|oregon|ohio)\b", re.IGNORECASE),
]


def sentences(text: str) -> list[str]:
    return [m.group(0).strip() for m in _SENTENCE.finditer(text) if m.group(0).strip()]


def _num(token: str) -> int:
    return int(token) if token.isdigit() else _WORD_NUMBERS[token.lower()]


def _first(text: str, pattern: str, flags: int = re.IGNORECASE) -> str | None:
    for sentence in sentences(text):
        if re.search(pattern, sentence, flags):
            return sentence
    return None


def _claim(qid: str, key: str, value: object, state: TriState, quote: str) -> ExtractedClaim:
    return ExtractedClaim(question_id=qid, key=key, value=value, state=state, quote=quote)  # type: ignore[arg-type]


def boolean_state(sentence: str, object_pattern: str) -> TriState:
    if _HEDGE.search(sentence):
        return "FALSE"
    if _VAGUE.search(sentence):
        return "UNKNOWN"
    if _DOUBLE_NEGATION.search(sentence):
        return "TRUE"
    if _NEGATION.search(_NO_EXCEPTION.sub("", sentence)):
        return "FALSE"
    if re.search(object_pattern, sentence, re.IGNORECASE) and _AFFIRM.search(sentence):
        return "TRUE"
    return "UNKNOWN"


def _boolean(qid: str, text: str) -> list[ExtractedClaim]:
    key, topic, obj = _BOOLEAN[qid]
    sentence = _first(text, topic)
    if sentence is None:
        return []
    state = boolean_state(sentence, obj)
    value = None if state == "UNKNOWN" else state == "TRUE"
    return [_claim(qid, key, value, state, sentence)]


def _interval_days(sentence: str) -> int | None:
    m = re.search(r"\bevery\s+" + _NUMBER + r"\s+(day|week|month)s?\b", sentence, re.IGNORECASE)
    if m:
        unit = {"day": 1, "week": 7, "month": 30}[m.group(2).lower()]
        return _num(m.group(1)) * unit
    m = re.search(r"\b(" + "|".join(_PERIOD_DAYS) + r")\b", sentence, re.IGNORECASE)
    if m:
        return _PERIOD_DAYS[m.group(1).lower()]
    return None


def _q03(qid: str, text: str) -> list[ExtractedClaim]:
    out: list[ExtractedClaim] = []
    for sentence in sentences(text):
        days = _interval_days(sentence)
        if days is not None:
            out.append(_claim(qid, "creds.rotation_days", days, "TRUE", sentence))
            break
    vault = _first(text, r"\b(vault|secrets? manager|key vault|kms|hsm)\b")
    if vault is not None:
        out.append(_claim(qid, "creds.vaulted", True, "TRUE", vault))
    return out


def _q04(qid: str, text: str) -> list[ExtractedClaim]:
    for sentence in sentences(text):
        days = _interval_days(sentence)
        if days is not None:
            return [_claim(qid, "access.review_interval_days", days, "TRUE", sentence)]
    return []


def _q07(qid: str, text: str) -> list[ExtractedClaim]:
    sentence = _first(text, r"\b(soc\s?2|iso|certif\w*|attest\w*|bridge letter|audit\w*|report)")
    if sentence is None:
        return []
    found = []
    if re.search(r"\bsoc\s?2\s+type\s+(ii|2)\b", text, re.IGNORECASE):
        found.append("SOC 2 Type II")
    if re.search(r"\biso(/iec)?\s?27001\b", text, re.IGNORECASE):
        found.append("ISO 27001")
    return [_claim(qid, "assurance.claimed", sorted(found), "TRUE", sentence)]


def _q08(qid: str, text: str) -> list[ExtractedClaim]:
    sentence = _first(text, r"\b(incidents?|breach(?:es)?)\b")
    if sentence is None:
        return []
    key = "incidents.vendor_reported_24m"
    if re.search(r"\b(no|none|zero|nil)\b", sentence, re.IGNORECASE):
        return [_claim(qid, key, 0, "TRUE", sentence)]
    plural = r"\s+(?:[\w-]+\s+){0,3}(?:incidents?|breach(?:es)?)\b"
    m = re.search(r"\b" + _NUMBER + plural, sentence, re.IGNORECASE)
    if m:
        return [_claim(qid, key, _num(m.group(1)), "TRUE", sentence)]
    if re.search(r"\b(a|an|one)\s+(?:[\w-]+\s+){0,3}(?:incident|breach)\b", sentence, re.IGNORECASE):
        return [_claim(qid, key, 1, "TRUE", sentence)]
    return [_claim(qid, key, None, "UNKNOWN", sentence)]


def _q09(qid: str, text: str) -> list[ExtractedClaim]:
    for sentence in sentences(text):
        m = re.search(r"\b" + _NUMBER + r"\s*(hours?|hrs?|h|days?)\b", sentence, re.IGNORECASE)
        if m:
            hours = _num(m.group(1)) * (24 if m.group(2).lower().startswith("d") else 1)
            return [_claim(qid, "breach.notify_hours_claimed", hours, "TRUE", sentence)]
    return []


def regions_in(text: str) -> list[str]:
    found = {name for name, pattern, flags in _REGIONS if re.search(pattern, text, flags)}
    return sorted(found)


def _q10(qid: str, text: str) -> list[ExtractedClaim]:
    matched = [s for s in sentences(text) if regions_in(s)]
    if not matched:
        return []
    start = text.index(matched[0])
    end = text.index(matched[-1], start) + len(matched[-1])
    quote = text[start:end]
    return [_claim(qid, "residency.regions_claimed", regions_in(quote), "TRUE", quote)]


def _q11(qid: str, text: str) -> list[ExtractedClaim]:
    for pattern, value in (
        (r"\b(sccs?|standard contractual clauses)\b", "SCCs"),
        (r"\bidta\b", "IDTA"),
        (r"\b(none|not applicable|n/a)\b", "NONE"),
    ):
        sentence = _first(text, pattern)
        if sentence is not None:
            return [_claim(qid, "transfer.mechanism_claimed", value, "TRUE", sentence)]
    return []


def _q13(qid: str, text: str) -> list[ExtractedClaim]:
    key = "vuln.patch_sla_critical_days"
    for sentence in sentences(text):
        m = re.search(r"\b" + _NUMBER + r"\s+(business|working)\s+days?\b", sentence, re.IGNORECASE)
        if m:
            return [_claim(qid, key, round(_num(m.group(1)) * 1.4), "TRUE", sentence)]
        m = re.search(r"\b" + _NUMBER + r"\s+(days?|weeks?)\b", sentence, re.IGNORECASE)
        if m:
            factor = 7 if m.group(2).lower().startswith("w") else 1
            return [_claim(qid, key, _num(m.group(1)) * factor, "TRUE", sentence)]
    return []


def _q14(qid: str, text: str) -> list[ExtractedClaim]:
    key = "pentest.interval_months"
    rules = (
        (r"\b(twice a year|semi-?annual\w*|every six months|every 6 months)\b", 6),
        (r"\bquarterly\b", 3),
        (r"\b(annual\w*|yearly|every year|once a year|every 12 months)\b", 12),
    )
    for sentence in sentences(text):
        for pattern, months in rules:
            if re.search(pattern, sentence, re.IGNORECASE):
                return [_claim(qid, key, months, "TRUE", sentence)]
    return []


_RULES: dict[str, Callable[[str, str], list[ExtractedClaim]]] = {
    **dict.fromkeys(_BOOLEAN, _boolean),
    "Q03": _q03,
    "Q04": _q04,
    "Q07": _q07,
    "Q08": _q08,
    "Q09": _q09,
    "Q10": _q10,
    "Q11": _q11,
    "Q13": _q13,
    "Q14": _q14,
}


def extract(question_id: str, answer_text: str) -> list[ExtractedClaim]:
    rule = _RULES.get(question_id)
    if rule is None or not answer_text.strip():
        return []
    return rule(question_id, answer_text)
