# Real component and controlled failure scope

Sprint0 review date:2026-11-08 Asia/Calcutta. Application baseline `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`, tested harness `d4c5e8e24b7c9d3c62fa35a5c6ea87ec75e43e79`.


|Boundary/scenario|Executed evidence|Limitation / certification status|
|---|---|---|
|PostgreSQL schema/transactions/tenancy|Real PG17 migrations,552 backend executions, actual authenticated HTTP and scope hooks|550pass/2binary skips; counts include imported fixture overlap, not every requirement accepted|
|FastAPI/React/browser|Real running loopback API/Vite, Chromium; pipeline8-step, RBAC5 groups, resource CRUD/pagination/themes/help|Some legacy UI remains excluded by new scope; PASS old behavior not approved scope compliance|
|DB commit/partial failure/audit|Actual transaction rollback/commit, immutable audit, retention rollback and constraints|Not a full centralized spool implementation or all crash cuts|
|Replica process termination/restart|release_runtime_probe.py bounded_concurrency uses real subprocess termination and claim persistence|Controlled adapter/real DB boundary; not actual Contrib queue crash/restart qualification|
|Replay/duplicates/token/lease negatives|Real remote protocol HTTP/PostgreSQL/TLS fixture and worker revocation tests|Synthetic transport/source and some controlled resolver/adapter hooks; no genuine provider certificate|
|Alert/in-app delivery|Real persisted alert recovery/in-app leased delivery|Email sender tests can mock transport; no actual SMTP/PagerDuty durable delivery certification|
|Backup/restore/corruption|100tables/1191rows/499constraints; content hashes, FKs/checks, audit triggers; checksum/corrupt/nonempty target refusal|No production PITR/RPO/RTO or old-binary/converged PR80 certificate|
|Pinned binary five methods/scrape/rotation|NOT TESTED:2 explicit skips, binary not configured|No pin/guard change or synthetic-success substitution|
|Stock saturated queue/central spool failures|NOT RUN by Sprint0; CHK001 FAIL/CHK002 BLOCKED|Full independent IDs, crashes at commit/ack/queue boundaries, backpressure and recovery belong to approved Sprint3/9 tasks after prerequisite review|
|Genuine Windows/Linux/Pentaho/SMTP/PD|NOT QUALIFIED|No real endpoints, credentials or provider operations authorized/executed|

Sources:raw/postgres-http-browser/ownership.txt, api.json, sprint08-http.json, sprint08-browser.json; raw/security-restore-faults/report.json/probes.log/remote-telemetry.json and source release_runtime_probe.py/remote_telemetry_acceptance_probe.py/alert_notification_acceptance_probe.py. Some existing release test setup uses ENVIRONMENT=production to exercise denial/non-owner settings against its own loopback synthetic DB/TLS fixture: no production deployment or shared data access.


**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO · formal owner UAT PENDING · development closure NOT COMPLETE.**
