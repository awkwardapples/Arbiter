CREATE NAMESPACE IF NOT EXISTS lightning.metastore
-- @@stmt
CREATE NAMESPACE IF NOT EXISTS lightning.metastore.arbiter
-- @@stmt
COMPILE USL IF NOT EXISTS vendor_risk DEPLOY NAMESPACE lightning.metastore.arbiter DDL
CREATE TABLE vendor (vendor_id varchar(12) NOT NULL PRIMARY KEY, legal_name varchar(200), trading_name varchar(200),
  category varchar(80), requested_service varchar(200), business_owner varchar(120), annual_spend_gbp decimal(14,2),
  criticality varchar(10), data_categories varchar(120), processing_countries varchar(120), clm_supplier_ref varchar(16),
  onboarding_status varchar(20), requested_at date);
CREATE TABLE vendor_alias (alias_id varchar(16) NOT NULL PRIMARY KEY, vendor_id varchar(12) FOREIGN KEY REFERENCES vendor(vendor_id), alias_lower varchar(200));
CREATE TABLE contract (contract_id varchar(16) NOT NULL PRIMARY KEY, supplier_ref varchar(16), status varchar(16), dpa_signed boolean,
  dpa_signed_date date, hosting_region_clause varchar(10), transfer_mechanism varchar(10), breach_notification_hours int,
  subprocessor_list_attached boolean, renewal_date date);
CREATE TABLE incident (incident_number varchar(16) NOT NULL PRIMARY KEY, opened_at date, vendor_name_raw varchar(200), severity varchar(4),
  category varchar(40), root_cause_tag varchar(40), status varchar(12), rca_completed boolean, closed_at date);
CREATE TABLE watchlist_entry (entry_id varchar(16) NOT NULL PRIMARY KEY, entity_name varchar(200), list_name varchar(60), country varchar(4), added_on date, reason varchar(200));
CREATE TABLE submission (submission_id varchar(16) NOT NULL PRIMARY KEY, vendor_id varchar(12) FOREIGN KEY REFERENCES vendor(vendor_id), submitted_at date, patch_sla_critical_days int, contact_role varchar(60));
CREATE TABLE submission_answer (answer_id varchar(20) NOT NULL PRIMARY KEY, submission_id varchar(16) FOREIGN KEY REFERENCES submission(submission_id), vendor_id varchar(12), question_id varchar(4), question varchar(300), answer_text varchar(4000));
CREATE TABLE submission_document (doc_id varchar(16) NOT NULL PRIMARY KEY, submission_id varchar(16) FOREIGN KEY REFERENCES submission(submission_id), vendor_id varchar(12), doc_type varchar(40), title varchar(200), issued_on date, expires_on date, doc_text varchar(12000));
CREATE TABLE vendor_component (component_id varchar(16) NOT NULL PRIMARY KEY, vendor_id varchar(12) FOREIGN KEY REFERENCES vendor(vendor_id), vendor_project varchar(120), product varchar(200), version varchar(60));
CREATE TABLE kev_vuln (cve_id varchar(24) NOT NULL PRIMARY KEY, vendor_project varchar(200), product varchar(300), vulnerability_name varchar(400), date_added date, due_date date, ransomware_use varchar(16))
-- @@stmt
UPDATE USL lightning.metastore.arbiter.vendor_risk SET DESCRIPTION 'Governed vendor-risk model for third-party onboarding. Procurement, contracts, incidents, the watchlist, the trust portal, and the public CISA KEV catalogue.'
-- @@stmt
UPDATE USL lightning.metastore.arbiter.vendor_risk.vendor SET TABLE DESCRIPTION 'One row per vendor onboarding request from procurement; tier inputs and the CLM supplier reference.'
-- @@stmt
UPDATE USL lightning.metastore.arbiter.vendor_risk.vendor_alias SET TABLE DESCRIPTION 'Other names procurement holds for a vendor, used to match incidents and watchlist entries.'
-- @@stmt
UPDATE USL lightning.metastore.arbiter.vendor_risk.contract SET TABLE DESCRIPTION 'The CLM contract for the supplier: DPA, hosting region, breach notice window, and renewal.'
-- @@stmt
UPDATE USL lightning.metastore.arbiter.vendor_risk.incident SET TABLE DESCRIPTION 'An ITSM incident whose raw vendor name is matched to a procurement alias.'
-- @@stmt
UPDATE USL lightning.metastore.arbiter.vendor_risk.watchlist_entry SET TABLE DESCRIPTION 'A sanctions or restricted-party name from the GRC watchlist.'
-- @@stmt
UPDATE USL lightning.metastore.arbiter.vendor_risk.submission SET TABLE DESCRIPTION 'The trust-portal submission header, including the critical patch SLA.'
-- @@stmt
UPDATE USL lightning.metastore.arbiter.vendor_risk.submission_answer SET TABLE DESCRIPTION 'One answer to a fixed questionnaire question on a submission.'
-- @@stmt
UPDATE USL lightning.metastore.arbiter.vendor_risk.submission_document SET TABLE DESCRIPTION 'An assurance document uploaded with a submission, with issue and expiry dates.'
-- @@stmt
UPDATE USL lightning.metastore.arbiter.vendor_risk.vendor_component SET TABLE DESCRIPTION 'A software component the vendor declared, joined to CISA KEV.'
-- @@stmt
UPDATE USL lightning.metastore.arbiter.vendor_risk.kev_vuln SET TABLE DESCRIPTION 'One entry in the CISA Known Exploited Vulnerabilities catalogue.'
-- @@stmt
ACTIVATE USL TABLE lightning.metastore.arbiter.vendor_risk.vendor AS SELECT COALESCE(vendor_id, '') AS vendor_id, legal_name, trading_name, category, requested_service, business_owner, CAST(annual_spend_gbp AS DECIMAL(14,2)) AS annual_spend_gbp, criticality, data_categories, processing_countries, clm_supplier_ref, onboarding_status, CAST(requested_at AS DATE) AS requested_at FROM arbiter.vendor_v
-- @@stmt
ACTIVATE USL TABLE lightning.metastore.arbiter.vendor_risk.vendor_alias AS SELECT COALESCE(alias_id, '') AS alias_id, vendor_id, alias_lower FROM arbiter.vendor_alias_v
-- @@stmt
ACTIVATE USL TABLE lightning.metastore.arbiter.vendor_risk.contract AS SELECT COALESCE(contract_id, '') AS contract_id, supplier_ref, status, CAST(dpa_signed AS BOOLEAN) AS dpa_signed, CAST(dpa_signed_date AS DATE) AS dpa_signed_date, hosting_region_clause, transfer_mechanism, CAST(breach_notification_hours AS INT) AS breach_notification_hours, CAST(subprocessor_list_attached AS BOOLEAN) AS subprocessor_list_attached, CAST(renewal_date AS DATE) AS renewal_date FROM arbiter.contract_v
-- @@stmt
ACTIVATE USL TABLE lightning.metastore.arbiter.vendor_risk.incident AS SELECT COALESCE(incident_number, '') AS incident_number, CAST(opened_at AS DATE) AS opened_at, vendor_name_raw, severity, category, root_cause_tag, status, CAST(rca_completed AS BOOLEAN) AS rca_completed, CAST(closed_at AS DATE) AS closed_at FROM arbiter.incident_v
-- @@stmt
ACTIVATE USL TABLE lightning.metastore.arbiter.vendor_risk.watchlist_entry AS SELECT COALESCE(entry_id, '') AS entry_id, entity_name, list_name, country, CAST(added_on AS DATE) AS added_on, reason FROM arbiter.watchlist_entry_v
-- @@stmt
ACTIVATE USL TABLE lightning.metastore.arbiter.vendor_risk.submission AS SELECT COALESCE(submission_id, '') AS submission_id, vendor_id, CAST(submitted_at AS DATE) AS submitted_at, CAST(patch_sla_critical_days AS INT) AS patch_sla_critical_days, contact_role FROM arbiter.submission_v
-- @@stmt
ACTIVATE USL TABLE lightning.metastore.arbiter.vendor_risk.submission_answer AS SELECT COALESCE(answer_id, '') AS answer_id, submission_id, vendor_id, question_id, question, answer_text FROM arbiter.submission_answer_v
-- @@stmt
ACTIVATE USL TABLE lightning.metastore.arbiter.vendor_risk.submission_document AS SELECT COALESCE(doc_id, '') AS doc_id, submission_id, vendor_id, doc_type, title, CAST(issued_on AS DATE) AS issued_on, CAST(expires_on AS DATE) AS expires_on, text AS doc_text FROM arbiter.submission_document_v
-- @@stmt
ACTIVATE USL TABLE lightning.metastore.arbiter.vendor_risk.vendor_component AS SELECT COALESCE(component_id, '') AS component_id, vendor_id, vendor_project, product, version FROM arbiter.vendor_component_v
-- @@stmt
ACTIVATE USL TABLE lightning.metastore.arbiter.vendor_risk.kev_vuln AS SELECT COALESCE(cve_id, '') AS cve_id, vendor_project, product, vulnerability_name, CAST(date_added AS DATE) AS date_added, CAST(due_date AS DATE) AS due_date, ransomware_use FROM arbiter.kev_vuln_v
-- @@stmt
REGISTER DQ dq_contract_dpa_date TABLE lightning.metastore.arbiter.vendor_risk.contract AS dpa_signed = false OR dpa_signed_date IS NOT NULL
-- @@stmt
REGISTER DQ dq_contract_breach_hours TABLE lightning.metastore.arbiter.vendor_risk.contract AS breach_notification_hours IS NULL OR (breach_notification_hours >= 1 AND breach_notification_hours <= 720)
-- @@stmt
REGISTER DQ dq_document_dates TABLE lightning.metastore.arbiter.vendor_risk.submission_document AS expires_on IS NULL OR expires_on >= issued_on
-- @@stmt
REGISTER DQ dq_incident_rca TABLE lightning.metastore.arbiter.vendor_risk.incident AS status <> 'closed' OR rca_completed IS NOT NULL
-- @@stmt
REGISTER DQ dq_vendor_spend TABLE lightning.metastore.arbiter.vendor_risk.vendor AS annual_spend_gbp >= 0
-- @@stmt
RUN DQ TABLE lightning.metastore.arbiter.vendor_risk.contract
-- @@stmt
RUN DQ TABLE lightning.metastore.arbiter.vendor_risk.submission_document
-- @@stmt
RUN DQ TABLE lightning.metastore.arbiter.vendor_risk.incident
-- @@stmt
RUN DQ TABLE lightning.metastore.arbiter.vendor_risk.vendor
