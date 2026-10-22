CREATE LIGHTNING DATABASE ARBITER_PUB DESCRIBE BY "Arbiter public KEV feed"
-- @@stmt
CREATE LIGHTNING REST TABLE kev_raw FROM ARBITER_PUB REQUEST(
    endpoint "{KEV_URL}",
    method "get",
    response_type "json",
    http_encoding "URLENCODED"
) HEADER () BODY ()
-- @@stmt
CACHE TABLE arbiter_pub.kev_raw
-- @@stmt
CREATE SCHEMASTORE CONTAINER arbiter
-- @@stmt
CREATE SCHEMASTORE VIEW kev_vuln_v WITH CONTAINER arbiter AS
SELECT v.`cveID` AS cve_id, v.`vendorProject` AS vendor_project, v.product AS product,
  v.`vulnerabilityName` AS vulnerability_name, CAST(v.`dateAdded` AS DATE) AS date_added,
  CAST(v.`dueDate` AS DATE) AS due_date, v.`knownRansomwareCampaignUse` AS ransomware_use
FROM arbiter_pub.kev_raw
LATERAL VIEW explode(vulnerabilities) AS v
