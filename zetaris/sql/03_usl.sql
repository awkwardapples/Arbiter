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
CREATE TABLE submission_document (doc_id varchar(16) NOT NULL PRIMARY KEY, submission_id varchar(16) FOREIGN KEY REFERENCES submission(submission_id), vendor_id varchar(12), doc_type varchar(40), title varchar(200), issued_on date, expires_on date, text varchar(12000));
CREATE TABLE vendor_component (component_id varchar(16) NOT NULL PRIMARY KEY, vendor_id varchar(12) FOREIGN KEY REFERENCES vendor(vendor_id), vendor_project varchar(120), product varchar(200), version varchar(60));
CREATE TABLE kev_vuln (cve_id varchar(24) NOT NULL PRIMARY KEY, vendor_project varchar(200), product varchar(300), vulnerability_name varchar(400), date_added date, due_date date, ransomware_use varchar(16))
-- @@stmt
ACTIVATE USL TABLE vendor AS SELECT vendor_id, legal_name, trading_name, category, requested_service, business_owner, annual_spend_gbp, criticality, data_categories, processing_countries, clm_supplier_ref, onboarding_status, requested_at FROM arbiter.vendor_v
-- @@stmt
ACTIVATE USL TABLE vendor_alias AS SELECT alias_id, vendor_id, alias_lower FROM arbiter.vendor_alias_v
-- @@stmt
ACTIVATE USL TABLE contract AS SELECT contract_id, supplier_ref, status, dpa_signed, dpa_signed_date, hosting_region_clause, transfer_mechanism, breach_notification_hours, subprocessor_list_attached, renewal_date FROM arbiter.contract_v
-- @@stmt
ACTIVATE USL TABLE incident AS SELECT incident_number, opened_at, vendor_name_raw, severity, category, root_cause_tag, status, rca_completed, closed_at FROM arbiter.incident_v
-- @@stmt
ACTIVATE USL TABLE watchlist_entry AS SELECT entry_id, entity_name, list_name, country, added_on, reason FROM arbiter.watchlist_entry_v
-- @@stmt
ACTIVATE USL TABLE submission AS SELECT submission_id, vendor_id, submitted_at, patch_sla_critical_days, contact_role FROM arbiter.submission_v
-- @@stmt
ACTIVATE USL TABLE submission_answer AS SELECT answer_id, submission_id, vendor_id, question_id, question, answer_text FROM arbiter.submission_answer_v
-- @@stmt
ACTIVATE USL TABLE submission_document AS SELECT doc_id, submission_id, vendor_id, doc_type, title, issued_on, expires_on, text FROM arbiter.submission_document_v
-- @@stmt
ACTIVATE USL TABLE vendor_component AS SELECT component_id, vendor_id, vendor_project, product, version FROM arbiter.vendor_component_v
-- @@stmt
ACTIVATE USL TABLE kev_vuln AS SELECT cve_id, vendor_project, product, vulnerability_name, date_added, due_date, ransomware_use FROM arbiter.kev_vuln_v
-- @@stmt
REGISTER DQ dq_contract_dpa_date TABLE contract AS dpa_signed = false OR dpa_signed_date IS NOT NULL
-- @@stmt
REGISTER DQ dq_contract_breach_hours TABLE contract AS breach_notification_hours IS NULL OR (breach_notification_hours >= 1 AND breach_notification_hours <= 720)
-- @@stmt
REGISTER DQ dq_document_dates TABLE submission_document AS expires_on IS NULL OR expires_on >= issued_on
-- @@stmt
REGISTER DQ dq_incident_rca TABLE incident AS status <> 'closed' OR rca_completed IS NOT NULL
-- @@stmt
REGISTER DQ dq_vendor_spend TABLE vendor AS annual_spend_gbp >= 0
-- @@stmt
RUN DQ TABLE vendor
-- @@stmt
RUN DQ TABLE contract
-- @@stmt
RUN DQ TABLE submission_document
-- @@stmt
RUN DQ TABLE incident
