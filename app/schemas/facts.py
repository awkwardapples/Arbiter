"""Canonical fact keys for policy and registry validation."""

from __future__ import annotations

FACT_KEYS = frozenset(
    {
        "vendor.data_categories",
        "contract.status",
        "mfa.admin_enforced",
        "mfa.remote_enforced",
        "creds.vaulted",
        "creds.rotation_days",
        "access.review_interval_days",
        "crypto.at_rest",
        "crypto.in_transit_tls12",
        "assurance.claimed",
        "assurance.soc2_type2_current",
        "assurance.iso27001_current",
        "assurance.bridge_letter_current",
        "incidents.vendor_reported_24m",
        "incidents.itsm_vendor_related_24m",
        "incidents.material_unremediated_24m",
        "breach.notify_hours",
        "breach.notify_hours_claimed",
        "breach.notify_hours_contract",
        "dpa.signed",
        "dpa.vendor_commits",
        "residency.regions",
        "residency.regions_claimed",
        "residency.regions_contract",
        "transfer.mechanism",
        "transfer.mechanism_claimed",
        "subprocessors.disclosed",
        "subprocessors.disclosed_claimed",
        "sanctions.watchlist_matches",
        "sanctions.near_matches",
        "vuln.components_declared",
        "vuln.kev_matches",
        "vuln.patch_sla_critical_days",
        "pentest.interval_months",
    }
)
