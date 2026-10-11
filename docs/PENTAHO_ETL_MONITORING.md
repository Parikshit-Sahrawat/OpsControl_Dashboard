# Sprint 3 — Pentaho ETL monitoring and investigation

Branch: `feature/sprint3-pentaho-monitoring`, based on Sprint 2's controlled infrastructure acceptance. This development slice polls Carte with read-only, authenticated, certificate-verified HTTPS and records scoped execution facts, schedule diagnoses, step results, sanitized opt-in logs and operational alert events. Genuine Carte acceptance is a separate, pending gate.

## Evidence and reproduction

The fixture is a **controlled Carte-shaped API, not a Pentaho installation**. It serves actual HTTPS requests with Basic authentication, an ephemeral trusted certificate, fixed GET paths and explicit mutation denial. The associated Linux collector observes a real local process; terminating and restarting that process produces native infrastructure health and alert evidence for ETL correlation.

Requires Python 3.12, Node 24, Docker, OpenSSL and Playwright/Chromium. Install backend provider/host requirements, frontend dependencies and isolated Playwright as described in [Sprint 2](INFRASTRUCTURE_MONITORING.md). Ports 11432, 18800 and 15174 must be free, along with TLS port 443 on the machine's private interface. Docker publishes the fixture only on that private interface, rather than requiring the Python worker to bind a privileged host port.

```bash
PLAYWRIGHT_MODULE=/workspace/.golden-tools/node_modules/playwright/index.mjs \
PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium \
  backend/.venv/bin/python scripts/etl-acceptance.py
```

Use `ETL_EVIDENCE_DIR` to keep test artifacts outside the checkout. Each run owns its PostgreSQL and Carte containers, API/Vite processes, disposable Linux target and private runtime directory. It never provisions AWS resources or accesses a production database. Successful cleanup removes ephemeral passwords and keys; failure retains private diagnostics at the printed path. Migration 0020 is exercised upgrade/downgrade/upgrade.

The gate drives No Run → Running → Long Running → SLA breach → Failed → poll unavailable → recovered on a new successful execution. These are controlled execution snapshots with distinct provider IDs, not evidence that a single live Pentaho job ran through these states. Repeated polls retain stable execution identity and append condition events only when their state changes. Actual Playwright sessions sign in through the password UI, open the drawer, inspect source details and host correlation, perform investigation actions, and verify another tenant sees no executions.

## Runtime and API contract

Create a Job Order with `POST /api/v1/etl/job-orders`: organization, hostname, job name, expected runtime, SLA, optional daily start/end window, grace period, IANA timezone and weekdays (Monday 0 through Sunday 6). The optional `host_data_source_id` must reference an infrastructure source in the same organization. Runtime/SLA thresholds are captured on each execution so historical evaluation does not depend on later Job Order settings. Window/grace/timezone evidence is captured with the observation. Daily windows support midnight crossing; arbitrary cron schedules are outside this slice.

Create a PENTAHO Data Source and a Collector through the existing scoped Resource Management APIs. Enabled local PENTAHO collection requires a platform administrator because its credential provider and egress policy belong to the deployment. Tenant administrators may prepare disabled collectors. Legacy Collector endpoints enforce the same permission, and the worker checks Job Order/source ownership before fetching secrets or contacting Carte.

The collector configuration is:

```json
{
  "url": "https://carte.example.test",
  "job_name": "Daily Warehouse",
  "job_order_id": "APPROVED_JOB_ORDER_UUID",
  "credential_ref": "APPROVED_SECRET_REFERENCE",
  "allowed_hosts": ["carte.example.test"],
  "allowed_cidrs": ["10.42.0.0/24"],
  "collect_logs": false
}
```

Without `execution_id`, the worker reads `/kettle/status/?xml=Y`, selects only the exact configured job name and reads `/kettle/jobStatus/?name=…&id=…&xml=Y` for retained executions. The fixed `execution_id` compatibility mode reads one execution and does not infer No Run. No execution, restart, stop, kill or job-edit endpoint is called. The worker's independent `OPSCONTROL_LOCAL_ALLOWED_HOSTS` / `OPSCONTROL_LOCAL_ALLOWED_CIDRS` policies must contain the collector's exact targets. DNS answers are checked and the connection pins the validated destination with hostname/certificate verification. HTTPS port 443, response size 64 KiB, inventory size 200 and entry count 100 are bounded. Oversized or unsafe XML fails closed; redirects are not followed.

Production credential references use exact AWS Secrets Manager ARN/region references with workload identity, as documented in the credential provider. Environment-backed references are development-only. Raw credentials and credentials in URLs are rejected by the configuration API. Logs require explicit opt-in, are bounded to 16 KiB and redact resolved credentials, common password/token assignments, authorization strings and URL credentials. This is pattern redaction, not a guarantee against every form of sensitive business data; operators must approve source-log collection and retention before genuine acceptance.

Carte version compatibility remains an explicit field test: the parser recognizes job-status/job_status, inventory jobname/id entries, jobentry_result/jobentry-result error facts, timezone-aware ISO start_date/end_date and plain log_text or base64/gzip logging_string. Missing or timezone-ambiguous source timestamps remain unavailable; detection time never substitutes for a source start/end. Unsupported log encoding is shown as unavailable. A genuine node's XML shape, timezone and logging format must be verified before accepting lifecycle rules.

## Evaluation, alerts and investigation

- No Run requires a successfully read complete inventory after the daily expected window plus grace. Known run starts, including late arrivals, resolve the condition. Unknown source start times suppress absence inference. Carte must retain executions across the evaluation window; clearing entries can defeat absence inference and is a genuine acceptance prerequisite.
- Long Running begins at expected runtime; SLA breach begins at the SLA threshold. Both need an actual source start. Unknown timing reports UNKNOWN rather than invented durations. The collector may be healthy while the monitored job fails.
- Failed transport/authentication leaves execution facts and condition events untouched, while the collector shows ERROR. A failed poll creates a CollectorRun failure, not an ETL failure or a fabricated No Run.
- ETL conditions use stable Job Order/condition references in append-only `AlertIncidentEvent` OPEN/RESOLVED events. They are distinct from metric-based infrastructure AlertState rows and do not yet send external notifications. No Run, Long Running, SLA and job failure each retain their own history.
- Source failures remain FAILED when a later execution succeeds. Terminal facts reject stale contradictory status polls. Recovery resolves job-level conditions; it does not resolve an operator investigation automatically.
- A failure automatically correlates tenant-scoped host metrics and infrastructure alerts using the explicit host association and a bounded time window. Correlation describes supporting evidence, not a confirmed root cause. Operators can rerun analysis; version count and evidence are visible.
- Investigation GET is read-only. Operators/admins create investigations through transitions/notes; viewers read them. The authenticated actor replaces a submitted operator name, transitions follow the allowed lifecycle, and HTTP actions are audited.

`GET /api/v1/etl/executions?latest_only=true` supplies current executions to the UI; the unfiltered endpoint retains history. Current means the most recently detected record per Job Order. The execution detail and `/evidence` endpoints provide steps, logs, timeline, same-job history and condition events. The ETL screen reports collector freshness/error alongside job status and the drawer links older executions for continued investigation after recovery. Browser timestamps explicitly use Asia/Kolkata. Evidence/history lists are bounded; database retention and large-fleet query optimization remain Sprint 5 work.

## Genuine Carte acceptance — pending

Use an approved disposable Carte node, its version, exact hostname/CIDR, trusted CA, read-only credential reference and known Job Order/execution identities. Confirm source timestamps/timezone, retained inventory coverage, step/log encoding and denied mutation before running the lifecycle. Capture runtime evidence with origin `GENUINE_CARTE` separately from this fixture report. No live endpoint or credential is required for the controlled sprint gate, and none is committed here.

## Validation record

Local cloud run on 2026-10-11: **PASS**. Seven runtime phases retained six JobOrderHistory records, two entries for each of the five source executions, and eight transitions across four stable condition references. Two failed polls left the failed source execution unchanged. Twenty-two successful requests used authenticated GETs on the two fixed Carte paths. The report records 142 redacted audit events.

| Check | Verified result |
|---|---|
| Source/runtime | Authenticated pinned HTTPS, stable provider IDs, No Run/grace, Running, Long Running, runtime SLA breach, job failure, poll blindness and new-run recovery |
| Database | Migration 0020 upgrade/downgrade/upgrade; six deduplicated histories; immutable detection/source end on stale contradictory polls; no source timestamps invented |
| Host correlation | Real Linux process loss creates native infrastructure alert evidence; ETL failure automatically records scoped metric/alert correlation |
| Investigation | API and browser transitions/notes; authenticated operator attribution; invalid transition denied; recovery preserves investigation and failed history |
| Security | Anonymous and cross-org denial, viewer write denial, privileged local collector changes denied, foreign host association denied before collection, XML/egress/log redaction checks, unknown timing/grace negatives, existing authentication/security/remote-worker probes |
| Frontend | Production build; all ETL phase checks and historical-failure drill-down; 11 actual Playwright screenshots, including other-tenant empty view |
| Regression | Sprint 1 actual HTTPS detection/recovery and Sprint 2 controlled infrastructure lifecycle/browser gates passed; [reassessment ledger](SPRINT_REASSESSMENT.md) |
| Genuine Carte / remote CI / review / merge | **PENDING** |

[Redacted runtime report](screenshots/etl/report.json) and actual browser captures:

| State | Screenshot |
|---|---|
| Configured, no observations | [Configured](screenshots/etl/configured.png) |
| Expected window missed | [No Run](screenshots/etl/no-run.png) |
| Source running | [Running](screenshots/etl/running.png) |
| Expected runtime exceeded | [Long Running](screenshots/etl/long-running.png) |
| Runtime SLA threshold reached | [SLA breach](screenshots/etl/sla-breach.png) |
| Source entry failure | [Failed](screenshots/etl/failed.png) |
| Carte unavailable, source facts preserved | [Poll failed](screenshots/etl/poll-failed.png) |
| Operator investigation | [Investigation](screenshots/etl/investigation.png) |
| New successful execution | [Recovered](screenshots/etl/recovered.png) |
| Older failure remains investigable | [Historical failure](screenshots/etl/historical-failure.png) |
| Other tenant sees no executions | [Other tenant](screenshots/etl/other-tenant.png) |

The [CI workflow](../.github/workflows/etl-acceptance.yml) repeats this controlled gate; adding a workflow is not evidence that remote CI ran. Review, merge and production acceptance require their own evidence.
