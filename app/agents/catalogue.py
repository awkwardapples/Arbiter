"""Static domain knowledge the agents share: questionnaire, screen set and control → verify-query map."""

from __future__ import annotations

# The fixed questionnaire (01 §3): question texts, allowed fact keys per question, and their control.
QUESTION_TEXTS: dict[str, str] = {
    "Q01": "Is MFA enforced for all administrative and privileged accounts?",
    "Q02": "Is MFA enforced for all remote and employee access to systems processing our data?",
    "Q03": "How often are credentials, keys and secrets rotated, and how are they stored?",
    "Q04": "How often are user access rights reviewed?",
    "Q05": "Is customer data encrypted at rest? Which standard?",
    "Q06": "Is data encrypted in transit (TLS 1.2+)?",
    "Q07": "Which independent certifications or attestations do you hold?",
    "Q08": "Have you had any security incidents affecting customer data in the last 24 months?",
    "Q09": "Within how many hours will you notify us of a personal-data breach?",
    "Q10": "Where will our data be hosted and processed?",
    "Q11": "What mechanism governs international transfers?",
    "Q12": "Do you disclose all sub-processors?",
    "Q13": "What is your patch SLA for critical vulnerabilities?",
    "Q14": "How often do you run independent penetration tests?",
    "Q15": "Will you sign our Data Processing Agreement?",
    "Q16": "Describe your secure development lifecycle.",
}
QUESTION_KEYS: dict[str, tuple[str, ...]] = {
    "Q01": ("mfa.admin_enforced",),
    "Q02": ("mfa.remote_enforced",),
    "Q03": ("creds.rotation_days", "creds.vaulted"),
    "Q04": ("access.review_interval_days",),
    "Q05": ("crypto.at_rest",),
    "Q06": ("crypto.in_transit_tls12",),
    "Q07": ("assurance.claimed",),
    "Q08": ("incidents.vendor_reported_24m",),
    "Q09": ("breach.notify_hours_claimed",),
    "Q10": ("residency.regions_claimed",),
    "Q11": ("transfer.mechanism_claimed",),
    "Q12": ("subprocessors.disclosed_claimed",),
    "Q13": ("vuln.patch_sla_critical_days",),
    "Q14": ("pentest.interval_months",),
    "Q15": ("dpa.vendor_commits",),
    "Q16": (),
}
_KEY_CONTROL_PREFIX: tuple[tuple[str, str], ...] = (
    ("vendor.", "TIER"),
    ("contract.", "TIER"),
    ("mfa.", "C01"),
    ("creds.", "C02"),
    ("access.", "C03"),
    ("crypto.", "C04"),
    ("assurance.", "C05"),
    ("incidents.", "C06"),
    ("breach.", "C07"),
    ("dpa.", "C08"),
    ("residency.", "C09"),
    ("transfer.", "C09"),
    ("subprocessors.", "C10"),
    ("sanctions.", "C11"),
    ("vuln.", "C12"),
    ("pentest.", "C12"),
)


def control_for_key(key: str) -> str:
    for prefix, control in _KEY_CONTROL_PREFIX:
        if key.startswith(prefix):
            return control
    return "OTHER"


# Iteration 1 ("screen"). The vendor profile is loaded at INTAKE.
SCREEN_QUERIES: tuple[str, ...] = (
    "Q_VENDOR_ALIASES",
    "Q_WATCHLIST_SCREEN",
    "Q_WATCHLIST_ALL",
    "Q_SUBMISSION",
    "Q_SUBMISSION_ANSWERS",
    "Q_SUBMISSION_DOCUMENTS",
    "Q_VENDOR_COMPONENTS",
)
SCREEN_QUERIES_INLINE: tuple[str, ...] = (
    "Q_WATCHLIST_ALL",
    "Q_SUBMISSION",
    "Q_SUBMISSION_ANSWERS",
    "Q_SUBMISSION_DOCUMENTS",
    "Q_VENDOR_COMPONENTS",
)

# Control → system-of-record query that can verify (or contradict) a vendor claim.
VERIFY_QUERIES: dict[str, tuple[str, ...]] = {
    "C05": ("Q_SUBMISSION_DOCUMENTS",),
    "C06": ("Q_VENDOR_INCIDENTS",),
    "C07": ("Q_VENDOR_CONTRACT",),
    "C08": ("Q_VENDOR_CONTRACT",),
    "C09": ("Q_VENDOR_CONTRACT",),
    "C10": ("Q_VENDOR_CONTRACT",),
    "C11": ("Q_WATCHLIST_SCREEN", "Q_WATCHLIST_ALL"),
    "C12": ("Q_COMPONENT_KEV",),
}
VERIFY_QUERIES_INLINE: dict[str, tuple[str, ...]] = {
    "C05": ("Q_SUBMISSION_DOCUMENTS",),
    "C06": ("Q_INCIDENTS_BY_NAME",),
    "C11": ("Q_WATCHLIST_ALL",),
    "C12": ("Q_KEV_BY_PRODUCTS",),
}
CONTRACT_QUERIES = frozenset({"Q_VENDOR_CONTRACT"})
DQ_QUERY = "Q_DQ_INVALID"
INCIDENT_WINDOW_DAYS = 730

# Queries whose rows carry vendor text that must pass the guard before any model sees it.
TEXT_QUERIES = {"Q_SUBMISSION_ANSWERS": "answer_text", "Q_SUBMISSION_DOCUMENTS": "text"}

# The system of record behind each query, for provenance.
QUERY_SYSTEM: dict[str, str] = {
    "Q_VENDOR_PROFILE": "procurement",
    "Q_VENDOR_ALIASES": "procurement",
    "Q_VENDOR_CONTRACT": "clm",
    "Q_VENDOR_INCIDENTS": "itsm",
    "Q_INCIDENTS_BY_NAME": "itsm",
    "Q_WATCHLIST_SCREEN": "grc_watchlist",
    "Q_WATCHLIST_ALL": "grc_watchlist",
    "Q_SUBMISSION": "trust_portal",
    "Q_SUBMISSION_ANSWERS": "trust_portal",
    "Q_SUBMISSION_DOCUMENTS": "trust_portal",
    "Q_VENDOR_COMPONENTS": "trust_portal",
    "Q_COMPONENT_KEV": "cisa_kev",
    "Q_KEV_BY_PRODUCTS": "cisa_kev",
    "Q_DQ_INVALID": "data_quality",
}
# Primary key column per query, for record keys like `contract_id=CTR-…`.
QUERY_PK: dict[str, str] = {
    "Q_VENDOR_PROFILE": "vendor_id",
    "Q_VENDOR_ALIASES": "alias_id",
    "Q_VENDOR_CONTRACT": "contract_id",
    "Q_VENDOR_INCIDENTS": "incident_number",
    "Q_INCIDENTS_BY_NAME": "incident_number",
    "Q_WATCHLIST_SCREEN": "entry_id",
    "Q_WATCHLIST_ALL": "entry_id",
    "Q_SUBMISSION": "submission_id",
    "Q_SUBMISSION_ANSWERS": "answer_id",
    "Q_SUBMISSION_DOCUMENTS": "doc_id",
    "Q_VENDOR_COMPONENTS": "component_id",
    "Q_COMPONENT_KEV": "cve_id",
    "Q_KEV_BY_PRODUCTS": "cve_id",
    "Q_DQ_INVALID": "record_key",
}


def record_key(query_id: str, row: dict[str, object]) -> str | None:
    pk = QUERY_PK.get(query_id)
    if pk is None or row.get(pk) is None:
        return None
    return f"{pk}={row[pk]}"
