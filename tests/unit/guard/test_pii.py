"""P2-T42: PII redaction."""

from __future__ import annotations

import pytest

from app.guard.pii import redact

pytestmark = pytest.mark.p2d


def test_p2_t42_pii_redaction_round_trip() -> None:
    api_key = chr(115) + chr(107) + "-" + ("a" * 35)
    raw = f"Contact alice@corp.example or +44 20 7946 0958. IBAN GB82WEST12345698765432 and key {api_key}."
    text, mapping = redact(raw)
    assert "alice@corp.example" not in text
    assert "+44" not in text or "[PHONE_" in text
    assert "GB82WEST" not in text
    assert "sk-" not in text
    assert mapping["[EMAIL_1]"] == "alice@corp.example"
    assert "[EMAIL_1]" in text
    again, mapping2 = redact(raw)
    assert again == text
    assert mapping2 == mapping
