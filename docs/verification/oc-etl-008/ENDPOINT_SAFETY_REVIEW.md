# Read-only endpoint safety review

[Machine candidates](ENDPOINT_CANDIDATES.json). **Every endpoint is UNVERIFIED for every installed build.** No installed build, edition, repository implementation, API specification or provider target is available. The existing family catalogue8.3/9.3/9.4/10.2.x/11.0.x is a discovery of source declarations only, not provider discovery or compatibility proof.

| Candidate GET path | Authority / basis | Preconditions and limits |
|---|---|---|
| /kettle/status/ | Carte; existing READ_PATHS allowlist | Exact XML schema/build/epoch/auth review; inventory advisory/incomplete, not schedule or durable Job catalogue |
| /kettle/jobStatus/ | Carte; existing reader | Exact known native execution ID and independently linked Job; encoded bounded query; logs disabled unless separately approved/redacted |
| /kettle/transStatus/ | Carte; existing reader | Exact transformation execution ID and kind; same epoch and schema constraints |
| /pentaho/api/scheduler/jobs | Server; proposed review hypothesis only | Obtain matching vendor API spec first; may be unavailable/different. Scheduler visibility/tenant permissions/side effects/pagination/rate limits unresolved; never infer execution outcome |
| /pentaho/api/repo/files/{pathId}/properties | Server repository; proposed review hypothesis only | Obtain exact API/plugin/encoding specification first; review traversal/path authorization and native GUID/type fields. Path/name alone not durable identity |

The two Server candidates are **not implemented adapter endpoints** and are not asserted to exist. A version-specific reviewer may reject or replace them with an approved bounded read-only export. No GET candidate is automatically safe: Carte control operations can also use GET. The operational adapter allowlist is unchanged; no new path is enabled.

Prohibit all start/stop/remove/execute/run/retry/reschedule/create/delete/pause/resume/terminate/upload/import/control endpoints regardless of verb; no POST/PUT/PATCH/DELETE requests to providers. No credentials in URLs, arbitrary Authorization headers, redirects, disabled TLS verification, dynamic wildcard paths or unbounded inventory/log fetch. Do not use credentials in negative probes to unauthorized targets.

Review CA/hostname/expiry/rotation, exact host/CIDR/port and DNS pinning, rate/size/time limits, pagination completeness, response schema hashes, UTC clock, redaction and permissions before any request. Credentials must use the existing secure reference mechanism with a read-only account; this package neither creates nor tests one. API200/login HTML is not build, identity or authority proof.


**Offline preparation only. Genuine qualification BLOCKED / NOT RUN. CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
