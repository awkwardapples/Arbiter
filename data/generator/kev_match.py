"""KEV component match rule (shared by generator asserts and Q_COMPONENT_KEV SQL)."""

from __future__ import annotations


def kev_matches(
    *,
    kev_vendor_project: str,
    kev_product: str,
    component_vendor_project: str,
    component_product: str,
) -> bool:
    return (
        kev_vendor_project.lower() == component_vendor_project.lower()
        and component_product.lower() in kev_product.lower()
    )
