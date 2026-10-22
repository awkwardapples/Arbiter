"""P3-T2: rule-based extractor, ≥ 4 cases per rules-table row; every quote is a substring of the source."""

from __future__ import annotations

from typing import Any

import pytest

from app.extract.deterministic import extract

pytestmark = pytest.mark.p3


def _claims(qid: str, text: str) -> dict[str, Any]:
    claims = extract(qid, text)
    for claim in claims:
        assert claim.question_id == qid
        assert claim.quote and claim.quote in text, (claim.quote, text)
    return {c.key: c for c in claims}


def _state(qid: str, text: str, key: str) -> str:
    found = _claims(qid, text).get(key)
    return "UNKNOWN" if found is None else found.state


BOOLEAN_CASES = [
    # Q01 / Q02: MFA
    ("Q01", "Yes, MFA is enforced via Okta for every admin role.", "mfa.admin_enforced", "TRUE"),
    ("Q01", "All privileged users must use MFA.", "mfa.admin_enforced", "TRUE"),
    ("Q01", "We do not currently require MFA for administrators.", "mfa.admin_enforced", "FALSE"),
    ("Q01", "Admin MFA is not enforced today.", "mfa.admin_enforced", "FALSE"),
    (
        "Q01",
        "MFA is enforced for engineers; admin accounts are on our Q1 roadmap.",
        "mfa.admin_enforced",
        "FALSE",
    ),
    ("Q01", "MFA for admins planned for Q1 next year.", "mfa.admin_enforced", "FALSE"),
    (
        "Q01",
        "Industry-standard security controls are applied where appropriate.",
        "mfa.admin_enforced",
        "UNKNOWN",
    ),
    ("Q01", "We implement recognized admin access practices.", "mfa.admin_enforced", "UNKNOWN"),
    ("Q01", "We no longer allow password-only admin logins; MFA is mandatory.", "mfa.admin_enforced", "TRUE"),
    ("Q01", "Not only admins but all staff must use MFA.", "mfa.admin_enforced", "TRUE"),
    ("Q02", "Every remote login uses MFA.", "mfa.remote_enforced", "TRUE"),
    ("Q02", "Remote workforce authentication includes MFA.", "mfa.remote_enforced", "TRUE"),
    ("Q02", "MFA is not enforced for remote users.", "mfa.remote_enforced", "FALSE"),
    ("Q02", "Remote MFA pilot is in progress in one region.", "mfa.remote_enforced", "FALSE"),
    # Q05 / Q06: encryption
    ("Q05", "Yes, customer data is encrypted at rest with AES-256.", "crypto.at_rest", "TRUE"),
    ("Q05", "We encrypt stored customer data with AES-256.", "crypto.at_rest", "TRUE"),
    ("Q05", "Customer data at rest is not encrypted.", "crypto.at_rest", "FALSE"),
    ("Q05", "Encryption at rest will be enabled next year.", "crypto.at_rest", "FALSE"),
    ("Q05", "Data is protected using industry-standard methods.", "crypto.at_rest", "UNKNOWN"),
    ("Q06", "Data in transit is encrypted with TLS 1.2+.", "crypto.in_transit_tls12", "TRUE"),
    ("Q06", "TLS 1.2 is the minimum for all external traffic.", "crypto.in_transit_tls12", "TRUE"),
    ("Q06", "We do not enforce TLS for every connection.", "crypto.in_transit_tls12", "FALSE"),
    ("Q06", "Connections are secured appropriately.", "crypto.in_transit_tls12", "UNKNOWN"),
    # Q12: sub-processors
    ("Q12", "Yes, sub-processors are disclosed in our register.", "subprocessors.disclosed_claimed", "TRUE"),
    (
        "Q12",
        "Our subprocessor list is published on the trust page.",
        "subprocessors.disclosed_claimed",
        "TRUE",
    ),
    ("Q12", "We don't disclose sub-processors.", "subprocessors.disclosed_claimed", "FALSE"),
    ("Q12", "Sub-processors are shared as needed.", "subprocessors.disclosed_claimed", "UNKNOWN"),
    # Q15: DPA
    ("Q15", "Yes, we will sign your Data Processing Agreement.", "dpa.vendor_commits", "TRUE"),
    ("Q15", "We commit to executing a DPA.", "dpa.vendor_commits", "TRUE"),
    ("Q15", "We will not sign the proposed DPA.", "dpa.vendor_commits", "FALSE"),
    ("Q15", "DPA terms are negotiable through legal.", "dpa.vendor_commits", "UNKNOWN"),
]


@pytest.mark.parametrize(("qid", "text", "key", "expected"), BOOLEAN_CASES)
def test_p3_t2_boolean_rules(qid: str, text: str, key: str, expected: str) -> None:
    assert _state(qid, text, key) == expected
    claim = _claims(qid, text).get(key)
    if claim is not None and claim.state != "UNKNOWN":
        assert claim.value is (claim.state == "TRUE")


@pytest.mark.parametrize(
    ("text", "days", "vaulted"),
    [
        ("Keys are rotated every 90 days and stored in HashiCorp Vault.", 90, "TRUE"),
        ("Secrets rotate quarterly in AWS Secrets Manager.", 90, "TRUE"),
        ("Credentials rotate monthly and live in Azure Key Vault.", 30, "TRUE"),
        ("Keys are kept in an HSM and rotated every 30 days.", 30, "TRUE"),
        ("Passwords are rotated annually.", 365, "UNKNOWN"),
        ("Signing keys live in our KMS and rotate yearly.", 365, "TRUE"),
    ],
)
def test_p3_t2_q03_rotation_and_vault(text: str, days: int, vaulted: str) -> None:
    claims = _claims("Q03", text)
    assert claims["creds.rotation_days"].value == days
    assert _state("Q03", text, "creds.vaulted") == vaulted


@pytest.mark.parametrize(
    ("text", "days"),
    [
        ("Access reviews occur every 60 days.", 60),
        ("User access is reviewed quarterly.", 90),
        ("Access rights are reviewed monthly.", 30),
        ("We review entitlements annually.", 365),
    ],
)
def test_p3_t2_q04_review_interval(text: str, days: int) -> None:
    assert _claims("Q04", text)["access.review_interval_days"].value == days


@pytest.mark.parametrize(
    ("text", "claimed"),
    [
        ("We hold a current SOC 2 Type II report.", ["SOC 2 Type II"]),
        ("We are ISO 27001 certified and hold a SOC 2 Type II report.", ["ISO 27001", "SOC 2 Type II"]),
        ("We hold ISO/IEC 27001 certification.", ["ISO 27001"]),
        ("SOC2 Type II audited annually.", ["SOC 2 Type II"]),
        ("We currently hold a SOC 2 bridge letter only.", []),
    ],
)
def test_p3_t2_q07_assurance_claimed(text: str, claimed: list[str]) -> None:
    claim = _claims("Q07", text)["assurance.claimed"]
    assert sorted(claim.value) == claimed


@pytest.mark.parametrize(
    ("text", "count"),
    [
        ("No security incidents affecting customer data in the last 24 months.", 0),
        ("We had no customer-data security incidents in 24 months.", 0),
        ("Zero customer-impacting security incidents in 24 months.", 0),
        ("We had two security incidents last year.", 2),
        ("There were 3 incidents affecting customer data.", 3),
        ("A customer data security incident occurred recently.", 1),
    ],
)
def test_p3_t2_q08_incidents(text: str, count: int) -> None:
    assert _claims("Q08", text)["incidents.vendor_reported_24m"].value == count


def test_p3_t2_q08_vague_gives_no_count() -> None:
    assert (
        _state("Q08", "We manage incidents according to our policy.", "incidents.vendor_reported_24m")
        == "UNKNOWN"
    )


@pytest.mark.parametrize(
    ("text", "hours"),
    [
        ("We notify within 72 hours.", 72),
        ("Notification within 48h of discovery.", 48),
        ("Customers are told within 3 days.", 72),
        ("We notify within 24 hours of confirmation.", 24),
    ],
)
def test_p3_t2_q09_hours(text: str, hours: int) -> None:
    assert _claims("Q09", text)["breach.notify_hours_claimed"].value == hours


@pytest.mark.parametrize(
    ("text", "regions"),
    [
        ("Data is hosted and processed in the EU only.", ["EU"]),
        ("Our hosting is EU-only for your data.", ["EU"]),
        ("Processing stays within EU regions.", ["EU"]),
        ("Primary hosting in Frankfurt with backups in London.", ["EU", "UK"]),
        ("Data may be processed in the US.", ["US"]),
        ("We use Virginia and Dublin data centres.", ["EU", "US"]),
    ],
)
def test_p3_t2_q10_regions(text: str, regions: list[str]) -> None:
    assert sorted(_claims("Q10", text)["residency.regions_claimed"].value) == regions


def test_p3_t2_q10_no_place_gives_no_claim() -> None:
    assert _state("Q10", "Hosting follows contractual commitments.", "residency.regions_claimed") == "UNKNOWN"


@pytest.mark.parametrize(
    ("text", "mechanism"),
    [
        ("Standard Contractual Clauses apply.", "SCCs"),
        ("We rely on SCCs for transfers.", "SCCs"),
        ("Transfers use the UK IDTA.", "IDTA"),
        ("Not applicable, data never leaves the UK.", "NONE"),
        ("None.", "NONE"),
    ],
)
def test_p3_t2_q11_transfer(text: str, mechanism: str) -> None:
    assert _claims("Q11", text)["transfer.mechanism_claimed"].value == mechanism


@pytest.mark.parametrize(
    ("text", "days"),
    [
        ("Critical patches within 14 days.", 14),
        ("Critical patches within 30 days.", 30),
        ("We patch critical issues within two weeks.", 14),
        ("Critical fixes ship within 10 business days.", 14),
        ("Critical patches within 5 business days.", 7),
    ],
)
def test_p3_t2_q13_patch_sla(text: str, days: int) -> None:
    assert _claims("Q13", text)["vuln.patch_sla_critical_days"].value == days


@pytest.mark.parametrize(
    ("text", "months"),
    [
        ("Pen tests annually.", 12),
        ("We run independent penetration tests twice a year.", 6),
        ("Penetration testing happens quarterly.", 3),
        ("An external firm pen-tests us annually.", 12),
    ],
)
def test_p3_t2_q14_pentest(text: str, months: int) -> None:
    assert _claims("Q14", text)["pentest.interval_months"].value == months


def test_p3_t2_quote_is_the_topic_sentence() -> None:
    text = "We take security seriously. Remote access requires MFA for all users. Thanks."
    claim = _claims("Q02", text)["mfa.remote_enforced"]
    assert claim.quote == "Remote access requires MFA for all users."


def test_p3_t2_context_only_question_yields_nothing() -> None:
    assert extract("Q16", "We use secure SDLC with code review and CI scanning.") == []
