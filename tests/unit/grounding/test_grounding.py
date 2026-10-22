"""P3-T3: grounding is normalised substring matching at word boundaries; paraphrase fails."""

from __future__ import annotations

import pytest

from app.grounding import is_grounded

pytestmark = pytest.mark.p3

SOURCE = (
    "We confirm that MFA is mandatory for admin access. "
    "Data stays EU\u2013only; it\u2019s \u201cencrypted\u201d."
)


@pytest.mark.parametrize(
    "quote",
    [
        "MFA is mandatory for admin access.",
        "MFA   is\nmandatory  for admin access",
        "mfa IS MANDATORY for ADMIN access",
        "Data stays EU-only",
        "Data stays EU\u2014only",
        'it\'s "encrypted"',
        "it\u2019s \u201cencrypted\u201d",
    ],
)
def test_p3_t3_variants_pass(quote: str) -> None:
    assert is_grounded(quote, SOURCE)


@pytest.mark.parametrize(
    "quote",
    [
        "Admins must use MFA.",
        "MFA is required for admin access.",
        "andatory for admin",
        "MF",
        "mandatory for admin acc",
        "",
        "   ",
    ],
)
def test_p3_t3_paraphrase_and_partial_words_fail(quote: str) -> None:
    assert not is_grounded(quote, SOURCE)
