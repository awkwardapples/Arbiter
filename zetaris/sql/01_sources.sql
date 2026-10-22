CREATE LIGHTNING DATABASE ARBITER_SRC DESCRIBE BY "Arbiter synthetic enterprise systems"
-- @@stmt
CREATE SCHEMASTORE CONTAINER arbiter
-- @@stmt
CREATE LIGHTNING REST TABLE procurement_vendors_raw FROM ARBITER_SRC REQUEST(
    endpoint "{URL:procurement_vendors_raw}",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER () BODY ()
-- @@stmt
CREATE LIGHTNING REST TABLE procurement_vendor_aliases_raw FROM ARBITER_SRC REQUEST(
    endpoint "{URL:procurement_vendor_aliases_raw}",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER () BODY ()
-- @@stmt
CREATE LIGHTNING REST TABLE clm_contracts_raw FROM ARBITER_SRC REQUEST(
    endpoint "{URL:clm_contracts_raw}",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER () BODY ()
-- @@stmt
CREATE LIGHTNING REST TABLE itsm_incidents_raw FROM ARBITER_SRC REQUEST(
    endpoint "{URL:itsm_incidents_raw}",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER () BODY ()
-- @@stmt
CREATE LIGHTNING REST TABLE grc_watchlist_raw FROM ARBITER_SRC REQUEST(
    endpoint "{URL:grc_watchlist_raw}",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER () BODY ()
-- @@stmt
CREATE LIGHTNING REST TABLE trust_submissions_raw FROM ARBITER_SRC REQUEST(
    endpoint "{URL:trust_submissions_raw}",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER () BODY ()
-- @@stmt
CREATE LIGHTNING REST TABLE trust_answers_raw FROM ARBITER_SRC REQUEST(
    endpoint "{URL:trust_answers_raw}",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER () BODY ()
-- @@stmt
CREATE LIGHTNING REST TABLE trust_documents_raw FROM ARBITER_SRC REQUEST(
    endpoint "{URL:trust_documents_raw}",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER () BODY ()
-- @@stmt
CREATE LIGHTNING REST TABLE trust_components_raw FROM ARBITER_SRC REQUEST(
    endpoint "{URL:trust_components_raw}",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER () BODY ()
-- @@stmt
CREATE SCHEMASTORE VIEW vendor_v WITH CONTAINER arbiter AS
SELECT r.vendor_id, r.legal_name, r.trading_name, r.category, r.requested_service, r.business_owner,
  CAST(r.annual_spend_gbp AS DECIMAL(14,2)) AS annual_spend_gbp, r.criticality, r.data_categories,
  r.processing_countries, r.clm_supplier_ref, r.onboarding_status, CAST(r.requested_at AS DATE) AS requested_at
FROM arbiter_src.procurement_vendors_raw
LATERAL VIEW explode(records) AS r
-- @@stmt
CREATE SCHEMASTORE VIEW vendor_alias_v WITH CONTAINER arbiter AS
SELECT r.alias_id, r.vendor_id, r.alias_lower
FROM arbiter_src.procurement_vendor_aliases_raw
LATERAL VIEW explode(records) AS r
-- @@stmt
CREATE SCHEMASTORE VIEW contract_v WITH CONTAINER arbiter AS
SELECT r.contract_id, r.supplier_ref, r.status, r.dpa_signed, CAST(r.dpa_signed_date AS DATE) AS dpa_signed_date,
  r.hosting_region_clause, r.transfer_mechanism, CAST(r.breach_notification_hours AS INT) AS breach_notification_hours,
  r.subprocessor_list_attached, CAST(r.renewal_date AS DATE) AS renewal_date
FROM arbiter_src.clm_contracts_raw
LATERAL VIEW explode(records) AS r
-- @@stmt
CREATE SCHEMASTORE VIEW incident_v WITH CONTAINER arbiter AS
SELECT r.incident_number, CAST(r.opened_at AS DATE) AS opened_at, r.vendor_name_raw, r.severity, r.category,
  r.root_cause_tag, r.status, r.rca_completed, CAST(r.closed_at AS DATE) AS closed_at
FROM arbiter_src.itsm_incidents_raw
LATERAL VIEW explode(records) AS r
-- @@stmt
CREATE SCHEMASTORE VIEW watchlist_entry_v WITH CONTAINER arbiter AS
SELECT r.entry_id, r.entity_name, r.list_name, r.country, CAST(r.added_on AS DATE) AS added_on, r.reason
FROM arbiter_src.grc_watchlist_raw
LATERAL VIEW explode(records) AS r
-- @@stmt
CREATE SCHEMASTORE VIEW submission_v WITH CONTAINER arbiter AS
SELECT r.submission_id, r.vendor_id, CAST(r.submitted_at AS DATE) AS submitted_at,
  CAST(r.patch_sla_critical_days AS INT) AS patch_sla_critical_days, r.contact_role
FROM arbiter_src.trust_submissions_raw
LATERAL VIEW explode(records) AS r
-- @@stmt
CREATE SCHEMASTORE VIEW submission_answer_v WITH CONTAINER arbiter AS
SELECT r.answer_id, r.submission_id, r.vendor_id, r.question_id, r.question, r.answer_text
FROM arbiter_src.trust_answers_raw
LATERAL VIEW explode(records) AS r
-- @@stmt
CREATE SCHEMASTORE VIEW submission_document_v WITH CONTAINER arbiter AS
SELECT r.doc_id, r.submission_id, r.vendor_id, r.doc_type, r.title,
  CAST(r.issued_on AS DATE) AS issued_on, CAST(r.expires_on AS DATE) AS expires_on, r.text
FROM arbiter_src.trust_documents_raw
LATERAL VIEW explode(records) AS r
-- @@stmt
CREATE SCHEMASTORE VIEW vendor_component_v WITH CONTAINER arbiter AS
SELECT r.component_id, r.vendor_id, r.vendor_project, r.product, r.version
FROM arbiter_src.trust_components_raw
LATERAL VIEW explode(records) AS r
