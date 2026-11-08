# Approved dependency-ordered Sprint1–10 backlog

Sprint0 review date:2026-11-08 Asia/Calcutta. Application baseline `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`, tested harness `d4c5e8e24b7c9d3c62fa35a5c6ea87ec75e43e79`.


This follows owner program v1 exactly, not an independently invented sprint order. The20 execution items in [CSV](SPRINTS_01_10_BACKLOG.csv)/[JSON](SPRINTS_01_10_BACKLOG.json) carry requirements/source references, dependencies, files, engineering/review roles, actual test-boundary obligations, acceptance prerequisites, risk and relative complexity (no calendar promises). Roles are proposed accountable functions, not fabricated person assignments/signoffs. No item is started or newly accepted. Known requirements are referenced; missing numbered journeys are not reconstructed.

|Sprint|Approved scope|Backlog IDs|Review dependency|
|---:|---|---|---|
|1|Resource Management|COMP-S01-01, COMP-S01-02|Sprint0 review and precise authority prerequisites|
|2|Windows/Linux collectors|COMP-S02-01, COMP-S02-02|Prior sprint review plus task dependencies|
|3|Telemetry ingestion and centralized PostgreSQL spool|COMP-S03-01, COMP-S03-02|Prior sprint review plus task dependencies|
|4|Host metrics, process/service inventory and selected processes|COMP-S04-01, COMP-S04-02|Prior sprint review plus task dependencies|
|5|Historical monitoring|COMP-S05-01, COMP-S05-02|Prior sprint review plus task dependencies|
|6|API and read-only Pentaho|COMP-S06-01, COMP-S06-02|Prior sprint review plus task dependencies|
|7|Background alerts, correlation/recovery, Email/PagerDuty|COMP-S07-01, COMP-S07-02|Prior sprint review plus task dependencies|
|8|Operational frontend/reports/administration/accessibility|COMP-S08-01, COMP-S08-02|Prior sprint review plus task dependencies|
|9|Security, reliability and performance hardening|COMP-S09-01, COMP-S09-02|Prior sprint review plus task dependencies|
|10|Full development closure and final owner integration review|COMP-S10-01, COMP-S10-02|Prior sprint review plus task dependencies|

Every sprint exits with real PostgreSQL/migrations/API/React/Playwright, security and applicable controlled failures under the global mandatory policy. Tests and artifacts are gathered during development; later formal UAT is separate. Mock-only/provider-unavailable cases remain explicitly NOT TESTED/BLOCKED. Approved architecture is not spool delivery evidence; Sprint3 coding requires reviewed exact transaction/recovery decisions. Current collector pin does not change implicitly. Sprint6 includes the newly supplied seven-day post-completion Pentaho raw-log default, prompt unrelated-data disposal, minimized longer-term structured evidence and governed holds/deletion; do not apply it destructively in Sprint0.

Sprint1 recommendation: review reusable PR82 resource/template changes and PR80 integration dependencies on an isolated development candidate, settle exact applicability/history and older-writer/migration contracts, then authorize a bounded implementation task. Do not merge the draft PRs blindly or merge any intermediate sprint into main. Required final development integration review and explicit approval precede any main merge. Stop at this Sprint0 checkpoint; Sprint1 NOT STARTED.


**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO · formal owner UAT PENDING · development closure NOT COMPLETE.**
