# [PRODUCT_NAME] Complete Enterprise Documentation and Agreements

Full text of seven documents. Fill the placeholders and follow the adoption gates in README.md before publication or execution.



---

# [PRODUCT_NAME] Product Feature Overview

Company: [COMPANY_NAME]  
Document owner: [PRODUCT_OWNER]  
Effective date: [EFFECTIVE_DATE]  
Technical baseline: OpsControl Dashboard main, commit bdc14d5c0633e1a534f4f7d0204cd66233aaee9a  
Product and procurement contact: [CONTACT_EMAIL]

## 1. Executive overview

[PRODUCT_NAME] is an organization-scoped observability and operational monitoring platform for site reliability engineers, DevOps teams, system administrators, and incident operators. It connects resource configuration, versioned monitoring policies, collector execution, stored health evidence, alerts, investigations, and reports. Its purpose is to help operators determine what was observed, when it was observed, which resources are affected, and whether a monitored condition recovered.

The platform provides modular dashboards with a Bento-style visual hierarchy, persistent dark and light themes, interactive status counts, organization filters, and resource drill-downs. Its operational views include Overview, ETL Jobs, VM Health, APIs, Incidents, Reports, Resource Management, and Monitoring Setup. Access Management is available to authorized platform administrators. These views use backend evidence rather than invented production metrics.

The current implementation is a development release with controlled runtime and browser evidence. Independent production security review, production-scale performance acceptance, operator UAT, and genuine provider acceptance remain separate prerequisites. A customer's purchase or deployment does not convert controlled fixture results into production acceptance. Commercial availability, hosting region, capacity, support, and contractual service levels must be specified in an executed Order Form.

## 2. Telemetry and collection architecture

A Data Source identifies the application, host, provider scope, or ETL service to be monitored. Monitoring definitions describe measurements and collection intervals. Versioned templates and rule catalogs provide reusable configuration. Explicit activation resolves pinned versions and produces supported collector assignments. Registering an agent or attaching a template alone does not establish collection or healthy status.

Supported observations include HTTPS availability and response timing, host CPU/memory/disk/process evidence, infrastructure discovery and selected provider metrics, and read-only Pentaho Carte execution evidence. The remote HTTPS protocol uses organization-scoped worker identities, approved network destinations, leased jobs, authenticated result submissions, and idempotent replay handling. It does not provide arbitrary remote command execution.

Real-time operation means repeated scheduled collection and refresh of accepted evidence. The product does not currently provide an unrestricted push-metrics endpoint, a public generic ingestion SDK, general OTLP ingestion, or a guaranteed streaming update interval. OTEL installation metadata is registration information; there is no supported OTEL runtime adapter merely because an OTEL collector record exists.

## 3. Interactive dashboards and investigations

Overview emphasizes current health, active conditions, and navigation to affected resources. VM Health presents host observations, collector freshness, alerts, filters, and infrastructure details. APIs presents monitored service evidence and HTTP history. ETL Jobs presents lifecycle status, execution history, available step failures and logs, and host-health correlation. Incidents connects alert episodes, operational condition recovery, investigation notes, and authorized operator lifecycle actions.

Reports offers supported observation windows, sampled HTTP success, mean observed HTTP latency, ETL runtime SLA evaluation, operational history, and JSON export. Sampled success is a ratio of recorded observations and is not a time-weighted uptime calculation. Missing observations, exclusions, and bounded history must remain visible when interpreting reports.

Available customization comprises themes, organization selection, supported search/filter controls, report windows, and drill-down navigation. A drag-and-drop dashboard composer, arbitrary custom widgets, user-authored query panels, and complete distributed-trace visualization are not included in the current baseline. Correlation uses available resource, execution, incident, and log evidence; it must not be represented as a complete distributed tracing engine.

## 4. Alerting and lifecycle controls

Operators configure authorized metric/log rules and activate their applicable versions. Threshold conditions can require consecutive breaches to reduce transient noise. A continuing breach updates the existing alert episode rather than creating a new incident for every observation. Accepted recovery evidence resolves the alert condition. Closing an operator investigation remains a separate authorized action and preserves operational history.

ServiceNow integration supports controlled validation of incident creation, retry, correlation, recovery, and resolution using a leased outbox and validated HTTPS responses. Genuine ServiceNow permissions, required fields, close codes, routing, and destination ownership must be accepted before real delivery is enabled. Detection is rule-based; machine-learning anomaly detection is not an implemented product claim.

## 5. Synthetic testing and evidence provenance

Disposable acceptance labs exercise actual TLS connections, HTTP healthy/failure/recovery transitions, native local Linux telemetry, PostgreSQL writes, tenant-negative tests, and real browser journeys. AWS SDK responses, selected Kubernetes/Windows behavior, Carte lifecycle responses, and ServiceNow-shaped delivery can be controlled fixtures. Every report must identify its evidence origin. Read-only EKS discovery imports cluster inventory with unknown health and no fabricated collector or workload measurements.

Synthetic acceptance is useful for validating integration behavior and release regressions. It does not establish genuine account IAM, native Windows installation, a customer's Carte instance, regional failover, sustained-load capacity, or a production recovery-time objective.

## 6. Tenant access and security model

Backend authorization and scoped database access enforce organization boundaries. The organization selector selects an authorized view; it does not grant access. Platform administration, organization administration, operator actions, and read-only viewing have different permissions. Human session tokens and worker credentials are separate identities and must not be interchanged.

Worker credentials are returned once and stored as digests by the control plane. Monitored Basic-auth credentials are represented by approved secret references, not plaintext passwords in collector configuration. Production secret resolution requires the supported managed-secret mechanism and scoped workload identity. Worker heartbeat timestamps represent collector liveness; they do not establish that the monitored target is healthy. Production deployment requires verified TLS, restricted database identities, trusted-proxy configuration, network-layer egress controls, and audited secret rotation.

## 7. Current technical specifications

| Item | Implemented behavior | Interpretation |
|---|---|---|
| Human session lifetime | Twelve hours from issuance in the current implementation | Revocation and account/membership changes may terminate access earlier. |
| Worker credential lifetime | Thirty-day default; creation accepts one through ninety days | Expiry is not automatic secret rotation. |
| Remote lease | Ninety seconds; exclusive claim and fenced completion | A lease is not a collection-latency SLA. |
| Accepted result time | Timezone-aware timestamp within five minutes of server time | Synchronize agent clocks with an approved time service. |
| Worker request body | Maximum 8,192 bytes; JSON and valid Content-Length required | Oversized submissions are rejected, not partially ingested. |
| Worker result model | One result for an assigned leased job; extra fields rejected | This is not a general-purpose metric batch API. |
| Measured response size | Up to 65,536 bytes | Raw response bodies are not included in accepted remote probe evidence. |
| Network policy size | Up to sixty-four hostnames and thirty-two CIDR entries | Both control-plane and local agent policies must permit the destination. |
| Login failure throttle | Ten failures per normalized username or thirty per client IP in a fifteen-minute window | A throttled login receives HTTP 429 with a fifteen-minute Retry-After. |
| Local collector concurrency | Default four; supported configuration range one through sixteen | Actual throughput depends on adapters, database capacity, and target latency. |
| Reports | Supported windows of one, seven, thirty, and ninety days | Operational history displays a bounded latest-event list, currently one hundred events. |
| Inventory | VM/API inventory supports server-backed pagination; some management lists remain bounded | A loaded-row count must not be described as a complete fleet total. |

There is no verified universal ingestion rate in events per second and no universal request-per-minute ingestion throttle in this baseline. Contract limits must be set as [INGESTION_REQUESTS_PER_MINUTE], [INGESTION_EVENTS_PER_DAY], [MAX_CONCURRENT_WORKERS], and [CONTRACTED_STORAGE_GB], tested under the customer's workload, and enforced at the appropriate gateway and application layers before the corresponding plan is sold. HTTP 429 behavior described for login must not be advertised as an implemented global ingestion limiter.

## 8. Latency objectives and availability commitments

No production ingestion-to-dashboard latency SLA is established by the repository. A commercial Order Form may specify a target of [P95_ACCEPTANCE_TO_QUERYABLE_SECONDS] seconds for the ninety-fifth percentile and [P99_ACCEPTANCE_TO_QUERYABLE_SECONDS] seconds for the ninety-ninth percentile under [ACCEPTED_WORKLOAD_PROFILE]. Measurement begins when a valid submission is durably accepted and ends when the corresponding evidence is queryable through the contracted API. Collection interval, remote queue delay, dashboard refresh, and external notification delivery are measured separately. A target becomes binding only after technical acceptance and explicit incorporation into the signed agreement.

The proposed hosted-service availability commitment is 99.9% per calendar month, subject to the complete SLA in the Terms of Service. It is a contractual offer template, not a claim that the current development build has achieved this availability. Customer-hosted software and preview services have no provider-operated uptime commitment unless an Order Form expressly provides one.

## 9. Retention behavior and proposed commercial policy

Metric definitions currently default to 365 days of raw evidence retention. Log sources currently default to thirty days. These values are configuration defaults, not a guarantee that automatic deletion runs. Bounded maintenance must be scheduled by an authorized operator. Evidence linked to correlations or investigations is excluded from ordinary raw-evidence cleanup.

Audit records, collector runs, incidents, and ETL histories presently remain retained until an approved archive/deletion policy is implemented. Customer-facing claims of finite deletion, storage expiry, or immediate erasure must not be made for these categories in the current baseline.

Before a hosted production launch, adopt and validate the Privacy Policy retention schedule, including active data, correlated evidence, historical audit/run records, backups, deletion requests, and lawful holds. The relevant Order Form must state the purchased retention period. Changes to retention must preserve necessary integrity controls and lawful preservation duties while satisfying applicable privacy and deletion obligations.

## 10. Procurement and deployment acceptance

An enterprise deployment requires an executed Order Form, the applicable license/Terms, a completed DPA, a verified subprocessor and transfer register, approved hosting regions, a tested retention/deletion program, agreed capacity, production security approval, genuine provider acceptance where required, and an operator UAT record. Material limitations and unsupported features must appear in the customer-facing scope. Marketing imagery, illustrative charts, or roadmap items do not expand contractual functionality.

Questions concerning implementation or a proposed enterprise deployment should be directed to [CONTACT_EMAIL]. Security incidents should be reported to [SECURITY_CONTACT_EMAIL], and privacy requests to [PRIVACY_CONTACT_EMAIL].


---

# [PRODUCT_NAME] User Manual

Provider: [COMPANY_NAME]  
Effective date: [EFFECTIVE_DATE]  
Support: [CONTACT_EMAIL]  
Applicable baseline: OpsControl Dashboard main bdc14d5c0633e1a534f4f7d0204cd66233aaee9a

## 1. Purpose, prerequisites, and operator responsibilities

This manual covers the implemented dashboard and monitoring workflow. An account with the appropriate organization membership is required. Platform administration is needed for worker enrollment and platform-controlled catalogs. Organization configuration requires the corresponding administrative permission. Investigation changes require an authorized operator or administrator. Viewers must not be given service credentials to bypass these distinctions.

Before connecting a target, obtain authorization from its owner, identify the permitted monitoring endpoints and network ranges, agree the collection frequency, and approve the required secret references. The deployment must provide trusted TLS, correct time synchronization, and network-layer restrictions. Never place production passwords, session tokens, worker tokens, raw private response bodies, or customer personal data in screenshots, tickets, example configuration, or source control.

## 2. Start the local fictional environment

Install Git, Docker Engine or Docker Desktop with Compose and BuildKit, Python 3, and Bash. On Windows, use WSL2 for the supplied shell commands. Ensure local ports 8000 and 5173 are free.

```bash
git clone https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard.git
cd OpsControl_Dashboard
git switch main
git pull --ff-only origin main
bash scripts/demo-up.sh
docker compose -f docker-compose.demo.yml ps
```

The command builds the frontend/API containers, starts private PostgreSQL, applies migrations, and creates a fictional organization and demo administrator. Open `http://127.0.0.1:5173`. Sign in as `demo-admin` using the generated password stored in `.demo-private/admin-password`. Read this private file locally; do not publish its contents. The expected organization code is `DEMO-LAB`.

```bash
curl -fsS http://127.0.0.1:8000/openapi.json >/dev/null
curl -fsS http://127.0.0.1:5173/ >/dev/null
docker compose -f docker-compose.demo.yml exec -T api alembic current
```

The migration head should be `0024_notification_leases`. HTTP responses alone do not prove a successful authenticated setup; confirm the organization in Resource Management after login. The initial demo may have no observations. Unknown health is expected until collection actually occurs.

Stop using `bash scripts/demo-down.sh`; resume using `bash scripts/demo-up.sh`. Stopping preserves the database and generated password. Do not remove volumes unless deletion is intentional and authorized. This profile is loopback-only development software. A hosted enterprise deployment must follow the production deployment runbook instead of exposing these containers publicly.

## 3. Create access and select an organization

Sign in with the account provided by your administrator. Check the organization selector before creating resources or investigating incidents. If the expected organization is absent, request the correct membership; changing a URL or guessing a resource ID does not grant access.

An authorized platform administrator uses Access Management to manage accounts, active status, roles, and organization membership. Use individual accounts and least privilege. Membership changes and session revocation may invalidate existing access. Sign out after work on a shared machine. Current human sessions expire after twelve hours unless revoked earlier.

## 4. Generate the supported service credential

There is no general-purpose user API-key generator in the current baseline. The implemented service credential is an organization-scoped worker token issued once to an authorized platform administrator. It authenticates the worker protocol only and is not a substitute for a human administrative session.

Using a protected API client and an authenticated platform-admin session, submit:

```http
POST /api/v1/auth/workers
Content-Type: application/json
Authorization: Bearer [ADMIN_SESSION_TOKEN]

{"organization_id":"[ORGANIZATION_UUID]","name":"[WORKER_NAME]","expires_in_days":30}
```

Store the returned `worker_token` immediately in an approved secret manager or an operating-system-protected deployment secret. The response is a one-time disclosure. Use the returned worker identifier for assignments and policy configuration. Do not save an unredacted response in a ticket or shell history. The platform stores a token digest rather than a retrievable worker secret. If the token is lost or exposed, revoke the worker through the authorized worker-management controls, enroll a replacement, and update its assignments and deployment secret. Expiry defaults to thirty days and cannot exceed ninety days when created through this API.

## 5. Create a Data Source and monitoring policy

Open Resource Management and add a Data Source in the intended organization. Provide a meaningful name, an approved endpoint or host identity, environment, and relevant workload metadata. Use fictional targets only in the local demo. The metadata must identify ownership and purpose without embedding credentials.

Choose or create authorized Metric, Log, and Alert Rules and commit their supported versions. Attach an applicable versioned template to the Data Source. Record the version identifiers and any resource-specific overrides. Do not assume that choosing an agent-install option makes a collector executable.

Open Monitoring Setup, preview the resolved configuration, review warnings, select a supported collector and worker arrangement, and activate the approved configuration. Confirm the resulting collector assignment and rule versions. An OTEL registration remains inactive because general OTLP collection is not implemented. EKS imports are discovery-only and remain unmonitored; use an approved Kubernetes monitoring arrangement for actual workload health.

## 6. Approve remote HTTPS network access

A platform administrator installs the control-plane policy for the enrolled worker:

```http
PUT /api/v1/remote-probes/workers/[WORKER_UUID]/network-policy
Content-Type: application/json
Authorization: Bearer [ADMIN_SESSION_TOKEN]

{"allowed_hosts":["portal.example.test"],"allowed_cidrs":["10.20.0.0/16"]}
```

The example hostname and subnet are placeholders. Replace them with explicitly approved targets. Review DNS A and AAAA answers and the intended private routes before approval. Remote probes permit HTTPS GET on port 443 with hostname/certificate validation and an approved pinned destination. Redirects are not followed. Metadata endpoints, link-local destinations, unsupported ports, embedded URL credentials, and prohibited request-target forms are denied.

Bind the supported collector to the worker:

```http
PUT /api/v1/remote-probes/collectors/[COLLECTOR_UUID]/assignment
Content-Type: application/json
Authorization: Bearer [ADMIN_SESSION_TOKEN]

{"worker_id":"[WORKER_UUID]"}
```

An assignment does not install the private-network agent. The agent must independently enforce its locally approved host and CIDR policy. A broader server policy cannot authorize destinations outside that local policy.

## 7. Install and run the agent

Install the approved source revision on a hardened, unprivileged machine within the permitted target network. Use the approved production runtime image or the reviewed source installation. Do not invent or install a package named `[PRODUCT_NAME]-sdk`; no generic public ingestion SDK is shipped in this baseline.

For a reviewed source installation:

```bash
cd OpsControl_Dashboard/backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-providers.txt -r requirements-hosts.txt
```

Configure the following non-secret variables in the service deployment:

```bash
export OPSCONTROL_SERVER_URL=https://monitoring.example.test
export OPSCONTROL_ALLOWED_HOSTS=portal.example.test
export OPSCONTROL_ALLOWED_CIDRS=10.20.0.0/16
python -m scripts.run_remote_agent
```

Replace the example domains and network ranges. Inject `OPSCONTROL_WORKER_TOKEN` through the approved runtime secret mechanism; it is intentionally omitted from the command block. Install trusted internal CAs using supported trust configuration. Enforce network-layer egress to the control-plane endpoint and approved targets. Do not disable TLS verification or use the insecure local control-plane flag with real infrastructure.

Run the scheduler as a separate managed service on the approved control-plane host:

```bash
cd OpsControl_Dashboard/backend
source .venv/bin/activate
python -m scripts.run_remote_scheduler
```

Monitor process restart, worker expiry, queue age, and secret rotation through the approved operating procedures. Linux native monitoring must execute on the intended host; Windows collection requires a genuine Windows worker. Local Docker demonstration startup does not automatically start these worker services.

## 8. Forward and verify telemetry

The agent sends an authenticated heartbeat, claims an assigned leased job, performs the permitted check, and submits structured evidence. A heartbeat updates worker liveness only. It does not create a health sample for the monitored service.

The result schema contains `event_id`, `job_id`, `lease_nonce`, `outcome`, `observed_at`, and applicable HTTP status/timing/size fields. Optional `auth_mode` identifies supported Basic-auth compatibility. Operational evidence views in the current UI display IST (Asia/Kolkata); the navigation clock can show a selected timezone. API evidence timestamps remain timezone-aware and should be normalized to UTC for cross-system investigation. The result must correspond to an assigned job with a valid lease, belong to the same organization, have a timezone-aware timestamp within five minutes of server time, and fit the 8 KiB worker request limit. Do not fabricate jobs, nonces, or measurements. Replaying the same accepted event is idempotent; a conflicting replay is rejected.

Confirm the collector's run history, accepted metric samples, observation timestamps, and current alert condition in Monitoring Setup and the appropriate operational tab. If only the heartbeat updates, investigate scheduling, assignment, queue state, target policy, and credential resolution rather than reporting the service healthy.

For HTTPS Basic authentication, configure only the supported `credential_ref` and the relevant Basic-auth mode. Install the worker's exact `OPSCONTROL_ALLOWED_CREDENTIAL_REFS` list. Production references must use the supported managed-secret format and workload identity permissions. Do not add username/password values to Data Source JSON or the job evidence.

## 9. Customize the operational view

Select Dark or Light in the navigation header; the preference is stored locally. Use the organization selector, available search controls, health/collector filters, and clickable KPI cards to narrow the investigation. Open a resource or incident drill-down to inspect evidence and history. The layout is a maintained Bento-style interface, not a drag-and-drop dashboard builder.

In Reports, choose a supported one-, seven-, thirty-, or ninety-day window. Review observation coverage and exclusions before interpreting percentages. Export report JSON when authorized and apply your organization's data-handling policy to the downloaded file. A sampled availability ratio is not proof of continuous uptime. The operational history view is bounded and does not promise an unpaginated complete historical export.

## 10. Configure and validate alert rules

Choose the correct measurement, resource scope, operator, threshold, severity, and supported breach count. Review collection interval and metric units; a threshold of 80 is not interchangeable between percent, milliseconds, and bytes. Commit the rule version and activate its applicable template/configuration. Keep the activation preview and version identifiers in the change record.

Use an approved synthetic target to generate normal observations, the required consecutive failing observations, and recovery observations. Confirm one continuing alert episode during repeated breaches and correct recovery evidence afterward. Inspect the incident separately: condition recovery and operator closure are distinct. Configure a real external destination only after its authentication, field requirements, authorization, routing, and failure behavior are accepted. Never use a live paging destination for unannounced synthetic testing.

## 11. Troubleshooting matrix

| Symptom | Likely cause | Operator action |
|---|---|---|
| HTTP 401 | Missing, expired, revoked, or wrong credential type | Re-authenticate the human session or replace the worker credential through authorized enrollment. Do not retry a revoked secret indefinitely. |
| HTTP 403 | Insufficient permission or forbidden action | Check the account role and approved workflow. Ask the responsible administrator; do not elevate a service token into a user credential. |
| HTTP 404 or empty organization result | Unknown resource or intentionally hidden other-tenant resource | Check the organization and resource identifier. Do not infer that another tenant's data is available. |
| HTTP 409 | Duplicate source, conflicting replay, or incompatible state transition | Compare existing identity/state and use the intended idempotent workflow. Do not create duplicate incidents to work around conflict. |
| HTTP 411 | Worker request has no valid Content-Length | Use the supported agent or a client that sends the complete JSON body with its correct length. |
| HTTP 413 | Worker JSON exceeds 8 KiB | Remove unsupported content; submit only the supported structured observation for the claimed job. |
| HTTP 415 | Worker submission is not JSON | Set the correct content type and use the supported protocol. |
| HTTP 422 | Invalid schema, timestamp, lease, unsupported activation, or unexpected fields | Compare the protected request against the current OpenAPI schema and the assigned job. Correct the specific validation failure without broadening policies. |
| Login HTTP 429 | Username/IP failure threshold reached | Follow Retry-After, check the real client address and forgotten credentials, and use authorized account recovery. |
| TLS_ERROR or denied probe | Untrusted certificate, hostname mismatch, DNS/egress violation, or redirect | Correct trust or the approved endpoint. Do not disable TLS, permit metadata addresses, or automatically follow redirects. |
| NETWORK_ERROR or TIMEOUT | Target routing, firewall, endpoint outage, or timeout | Confirm approved connectivity and service ownership. Preserve the error as monitoring evidence; do not change it to success. |
| Worker alive, no samples | Missing assignment, stopped scheduler, expired lease, unsupported collector, or absent metric mapping | Inspect assignment, supported adapter, scheduler status, current jobs, run history, and active metric definitions. |
| Alert does not open | Incorrect units/scope, inactive rule, breach count not reached, or missing valid samples | Confirm the pinned rule, resource mapping, accepted timestamps, units, and required consecutive observations. |
| Alert recovered but incident open | Investigation not yet closed | Verify recovery evidence, complete operator review, and use the authorized incident action. |
| External notification pending/failed | Destination authentication, invalid response, required provider fields, retry/lease state, or missing opening incident | Inspect sanitized outbox status and provider correlation through authorized tooling. Do not paste provider credentials or raw sensitive responses into a ticket. |
| Report appears incomplete | Bounded history, wrong window/org, excluded executions, or absent evidence | Narrow the window and scope, inspect coverage/exclusions, and use approved API pagination/export capabilities where available. |
| Docker dependency certificate failure | Trusted enterprise inspection CA absent in build | Use a reviewed ephemeral BuildKit CA secret override. Keep package and TLS verification enabled. |

## 12. Query and performance guidelines

Begin with the correct organization and a short relevant time window. Use supported server-side pagination rather than repeatedly loading a complete fleet. Avoid simultaneous broad refreshes from many operator sessions. Increase report windows only when needed and note bounded histories and retention gaps. Use stable resource and execution identifiers to correlate records instead of searching every log for unstructured fragments.

A production query or index change requires measured evidence, an execution plan, migration review, and representative load tests. Operators must not run ad hoc destructive SQL, disable tenant scope, drop indexes, or bypass audit triggers to improve a dashboard response. If the supported interface cannot answer an investigation, request an approved diagnostic export with least-privilege access.

## 13. Support escalation

Provide the affected organization identifier, resource/collector identifiers, UTC incident interval, product revision, sanitized HTTP error category, and relevant non-secret event or correlation identifiers. State whether evidence is genuine or synthetic. Attach redacted screenshots and sanitized logs. Send security-sensitive reports to [SECURITY_CONTACT_EMAIL] and privacy-sensitive requests to [PRIVACY_CONTACT_EMAIL]. Do not include tokens, passwords, private dumps, or unrelated tenants' data.


---

# [PRODUCT_NAME] User Training Guide

Organization: [COMPANY_NAME]  
Effective date: [EFFECTIVE_DATE]  
Training owner: [TRAINING_OWNER]  
Training contact: [CONTACT_EMAIL]

## 1. Training purpose and outcomes

This guide prepares SREs, DevOps engineers, and system administrators to configure authorized monitoring, distinguish collector health from target health, investigate high-severity conditions, and preserve reliable incident evidence. Completion demonstrates competence in a controlled environment; it is not production deployment approval or a professional certification.

A trained operator should be able to identify the correct organization, find an affected resource, determine evidence freshness, explain a pinned rule version, distinguish breach/recovery/closure, correlate available logs and metrics, protect credentials, and escalate an unresolved condition with a reproducible evidence package.

## 2. Prerequisites and training environment

Use the local fictional Docker environment or an explicitly approved staging tenant. Obtain individual accounts with the roles required for the exercises. An administrator must approve the synthetic targets and network policy. Use a private training notification sink instead of a real paging or ServiceNow destination. Do not use customer personal data or production credentials.

Read the User Manual and the incident policy before beginning. Confirm the expected migration head and organization. Confirm that the environment is labeled synthetic and that any failure injected during the exercise cannot affect production. Record the product revision and the origin of each observation.

## 3. Role-based onboarding path

### 3.1 Common operator foundation

Sign in, identify the current organization, and locate Overview, VM Health, APIs, ETL Jobs, Incidents, Reports, Resource Management, and Monitoring Setup. Change the theme and verify that status remains readable. Open a KPI and explain which screen it navigates to. Find an unknown resource and explain why missing evidence cannot be treated as healthy.

Inspect a resource's collector, last observation, and last worker heartbeat. Explain that a heartbeat proves only that the worker contacted the control plane. Identify the responsible service owner and the recorded configuration version. Sign out and confirm that protected actions require authentication.

### 3.2 SRE path

Review the monitored service's actual observation coverage, configured thresholds, breach count, and sampling interval. Inspect failure and recovery history. Explain why HTTP sampled success differs from continuous time-weighted availability. Inspect a high-severity incident's evidence and write a concise operational hypothesis without treating correlation as proof of causation.

Practice recognizing monitoring gaps, collector errors, target failures, stale observations, and genuine recovery. Confirm a recovery sample before recommending closure. Produce an evidence-backed handoff for the next on-call engineer.

### 3.3 DevOps engineer path

Create or review a fictional Data Source, attach the approved template version, preview effective configuration, and activate a supported collector. Record the resulting version and assignment. Review approved target hostnames, CIDRs, secret references, and scheduler deployment.

Deploy the reviewed agent with protected worker credentials. Observe heartbeat, claim, accepted result, metric sample, and alert evaluation. Test credential revocation and a denied destination without broadening the policy. Explain how to roll back an application image without destructively downgrading preserved schema or leaving incompatible agent configurations active.

### 3.4 System administrator path

Verify host CPU, memory, disk, process observations, and collector location. Explain why host telemetry must run in the intended host context and why native Windows acceptance requires a Windows worker. Inspect worker expiry, service restart behavior, firewall rules, system time, and trusted certificate configuration.

Verify a populated backup and a restoration into an isolated empty database under the approved runbook. Explain retention defaults, maintenance scheduling, pinned evidence, and historical categories whose finite deletion program remains unimplemented. Do not disable audit enforcement or remove evidence to satisfy an exercise.

## 4. Guided exercise: establish a monitored HTTPS service

Enroll an approved worker, install both server and local network policies, and create the fictional HTTPS Data Source. Attach approved metric and alert definitions. Preview and activate the pinned policy. Start the reviewed remote scheduler and agent services.

Observe a valid healthy sample and record its observation time, HTTP status, collector run identifier, and metric value. Confirm that the dashboard reflects the accepted evidence. Record the worker heartbeat separately. If the sample does not appear, use the troubleshooting matrix and stop before injecting a failure.

The exercise passes when the expected organization can see the evidence, another organization cannot read it, the collector has a valid run, the metric has an accepted sample, and configuration/audit history identifies the authorized actions. A successful login or running process alone is insufficient.

## 5. Guided exercise: triage a high-severity incident

### Step 1: acknowledge operational ownership

Open Incidents, select the high-severity episode, and confirm its organization and affected resource. Use the authorized investigation action supported by the installed UI to begin or acknowledge work under your organization's incident procedure. Record the on-call owner, incident identifier, severity, and the earliest known impact time. Do not downgrade severity merely to suppress notifications.

### Step 2: establish evidence freshness and collection health

Inspect the latest target observation, collector run status, queue/assignment context if authorized, and worker heartbeat. Determine whether the condition is a measured service failure, a monitoring failure, or an absence of evidence. Confirm that clocks and timestamps are comparable. Preserve the distinction in the incident note.

If evidence is stale or the collector cannot reach its approved target, state that the target's present health is unknown. A collector's liveness does not override failed or missing service measurements.

### Step 3: determine the triggering rule

Identify the pinned alert rule version, measurement, threshold, severity, scope, and consecutive breach count. Review the accepted samples that satisfied the rule. Check metric units and the expected HTTP status. Determine whether repeated failures update the same condition episode. Record the evidence identifiers rather than copying an entire sensitive response body.

### Step 4: correlate available logs and metrics

Open the resource drill-down and inspect available logs, HTTP timings, host CPU/memory/disk/process observations, and related ETL executions over a narrow interval around the first breach. Where recorded, use correlation identifiers and stable resource/execution IDs to connect events. Look for changes in timing, resource pressure, process status, or job-step failure that precede or coincide with the service condition.

Use the same interval and time basis when comparing observations. Current operational evidence views display IST (Asia/Kolkata); API timestamps should be normalized to UTC, and the navigation clock selection is separate. Distinguish an absent measurement from a normal measurement. Describe a temporal association as a hypothesis until independent evidence supports causation. For example, disk pressure followed by an ETL write error and an API failure may justify investigation of a shared host; it does not by itself prove that disk pressure caused the API outage.

The current platform does not offer a complete distributed-trace explorer. A metric/history deep-dive is supported; a trace/span deep-dive must be performed in an approved external tracing tool if that capability is required. If an external trace identifier is available, record it and its source without inventing spans or presenting an illustrative diagram as captured trace evidence.

### Step 5: form and test a safe hypothesis

Write a short hypothesis, the supporting observations, an alternative explanation, and the next authorized diagnostic action. Prefer read-only checks. Obtain change authority before restarting production services, modifying infrastructure, widening network policy, or sending external notifications. Monitoring operators must not use the agent as a remote shell.

During training, switch only the approved synthetic endpoint from its healthy response to the configured failure response. Observe the required consecutive breaches and confirm one continuing alert episode. Restore the synthetic endpoint and wait for accepted recovery evidence. Do not manually forge a successful measurement to end the incident.

### Step 6: verify recovery and notification correlation

Confirm that the target returned the expected status and the relevant metric recovered. Check that the alert condition resolved with stored evidence. Inspect external delivery state only through approved tooling. A controlled ServiceNow exercise must update the same correlated external incident rather than create another incident for every retry.

A recovered condition does not automatically prove all user impact has ended. Check observation coverage, related resources, and the approved operational criteria. If the evidence is incomplete, record the limitation and retain the investigation.

### Step 7: close and hand off correctly

Complete the authorized operator closure only after the incident procedure's requirements are met. Preserve the distinction between condition recovery and investigation closure. Record the impact interval, evidence, changes performed, residual risk, follow-up owner, and required validation. Keep historical failures visible and do not rewrite them as healthy results.

Prepare a handoff that identifies the incident, current condition, last valid sample, working hypothesis, completed actions, outstanding checks, next owner, and any temporary restrictions. Use approved channels; never include a credential or unrelated tenant's data.

## 6. Guided ETL investigation

Find an approved synthetic Carte execution. Inspect its lifecycle, timeline, available logs, and step-level failure. Distinguish No Run from a failed run, and Long Running from an execution that completed beyond its runtime SLA. Inspect excluded executions and missing start/end times before interpreting report denominators.

Correlate the ETL evidence with host resource observations over the same interval. Identify whether a historical failure remains preserved after the current execution recovers. Add a sanitized investigation note and export only the authorized evidence needed for the exercise. Genuine Carte authentication, version compatibility, and operational history must be separately accepted against the customer's system.

## 7. Reports and operational communication

Choose a supported report window and the correct organization. Explain the sample count, missing/unknown observations, ETL exclusions, and bounded history. Use the JSON export when authorized. State that a sampled success percentage is not a contractual uptime calculation and that the product's own hosted-service SLA is defined by the applicable agreement.

A useful incident communication states what is affected, the evidence supporting that conclusion, the current uncertainty, the owner, and the next action. Avoid statements such as “all systems are healthy” when only one synthetic endpoint was observed. Do not claim AWS, Windows, Carte, or regional failover acceptance from controlled responses.

## 8. Assessment and completion criteria

The trainer must observe the trainee complete an authorized configuration, verify accepted telemetry, explain worker-versus-target health, trigger and recover a synthetic alert, correlate available evidence, preserve tenant boundaries, and produce a redacted incident handoff. The trainee must identify the absence of generic SDK/OTLP and complete distributed-trace support rather than invent an installation step.

Record the trainee's name, role, training tenant, product revision, exercise date, evidence identifiers, outcome, remedial work, and trainer approval. Any unauthorized action, exposed credential, fabricated sample, cross-tenant disclosure, or unapproved live notification fails the exercise and must be addressed under the security procedure.

## 9. Continuing practice and escalation

Repeat controlled exercises after material changes to authentication, policies, collectors, incidents, retention, or deployment. Review relevant release notes and known limitations before each upgrade. Escalate security issues to [SECURITY_CONTACT_EMAIL], privacy matters to [PRIVACY_CONTACT_EMAIL], and product/training questions to [CONTACT_EMAIL]. Production access and release acceptance remain governed by the customer's formal operating and approval procedures.


---

# [PRODUCT_NAME] End-User License Agreement and Terms of Service

Effective date: [EFFECTIVE_DATE]  
Provider: [COMPANY_NAME], organized under the laws of [COMPANY_JURISDICTION], with its principal address at [COMPANY_ADDRESS]  
Contract notices: [CONTACT_EMAIL]

**Execution status.** This is a complete agreement template for customization and legal review. It becomes the Provider's binding agreement only through the acceptance mechanism below and an authorized commercial release. A development deployment, marketing image, or unsigned template does not establish a hosted production SLA, a subscription, certification, or acceptance of unimplemented functionality.

## 1. Parties, acceptance, and documents

This Agreement is between [COMPANY_NAME] (the “Provider”) and the legal entity identified in an accepted Order Form or authorized business-account registration (the “Customer”). A person accepting for an entity represents that the person has authority to bind that entity. An individual without that authority may not accept on its behalf. Authorized Users access the Service through Customer and do not receive an independent ownership interest.

An Order Form becomes effective when executed by authorized representatives or accepted through an expressly identified electronic contracting process that makes this Agreement available before acceptance and records affirmative assent. Browsewrap access alone is not the intended acceptance method. The Order Form must identify the purchased deployment, subscription term, fees, support plan, hosting region where relevant, capacity, retention, and any negotiated terms.

The Agreement consists of the Order Form, these Terms, the applicable Software license provisions, the Data Processing Addendum (“DPA”), the SLA where applicable, and expressly incorporated schedules. The mandatory Standard Contractual Clauses prevail for their regulated subject matter. Otherwise, the DPA controls personal-data processing conflicts; a signed negotiated Order Form controls other conflicts; these Terms control standard documentation and marketing materials. A purchase-order form does not amend this Agreement unless Provider expressly signs the amendment.

## 2. Definitions

“Service” means the hosted [PRODUCT_NAME] components expressly purchased in an Order Form. “Software” means Provider software supplied for Customer installation under that Order Form, including an approved agent or customer-hosted deployment. “Documentation” means the applicable published operating documentation for the purchased version. “Customer Data” means information submitted, collected, or stored on Customer's behalf, including telemetry, logs, resource metadata, configurations, and investigation content. “Authorized User” means a person Customer authorizes within its purchased entitlement. “Usage Limits” means the objective limits in the Order Form and applicable technical specifications. “Subscription Term” means the purchased period. “Preview” means a trial, beta, experimental, development, or expressly non-production offering. “Confidential Information” is defined in Section 11. “Personal Data” has the meaning applicable under the DPA.

## 3. Hosted access and Software license

Subject to this Agreement and payment of undisputed fees, Provider grants Customer a non-exclusive, non-transferable right during the Subscription Term to access and use the purchased Service through its Authorized Users for Customer's internal business operations, including monitoring systems Customer is legally authorized to monitor. Customer may allow its contractors to act for Customer within the purchased entitlement and remains responsible for them. Affiliate rights exist only if the Order Form identifies the covered Affiliates.

For purchased Software, Provider grants Customer a non-exclusive license to install and execute the approved Software in the number and type of environments specified in the Order Form, and to make reasonable backup copies. The license lasts for the term stated in the Order Form. Source-code rights, perpetual rights, redistribution, OEM embedding, and transfer to an Affiliate or successor are included only if expressly granted. If the Order Form grants a perpetual paid-up license, expiration of support does not revoke that license; hosted access and subscription-only features still expire as agreed.

Except to the extent applicable law prohibits the restriction or an applicable open-source license permits the activity, Customer shall not distribute Provider's proprietary Software to third parties, remove proprietary notices, circumvent entitlement or security controls, or reverse engineer it to obtain protected source code or trade secrets. These restrictions do not prohibit legally protected interoperability, security research conducted under an authorized policy, or exercising applicable open-source rights.

Open-source and third-party components remain governed by their applicable licenses and notices. This Agreement does not convert those components into Provider-owned proprietary material, override permissive or copyleft rights, or establish rights Provider has not obtained. Provider must maintain the required notices and fulfill applicable source-disclosure obligations before distribution. Customer retains rights independently granted by those licenses.

## 4. Customer responsibilities and acceptable use

Customer shall maintain account security, assign appropriate roles and organization memberships, protect service credentials, review destination allowlists, obtain target-owner authorization, and ensure a lawful basis for Customer Data processing. Customer shall configure collection and retention to minimize unnecessary personal and sensitive data. Customer shall not submit credentials as telemetry, use the Service to monitor systems without permission, or knowingly collect data that infringes third-party rights.

Customer shall not use the Service to distribute malware, conduct denial-of-service attacks, evade network restrictions, exfiltrate data, conduct unlawful surveillance, attempt cross-tenant access, impersonate another customer, or materially interfere with Service integrity. Customer shall not intentionally bypass Usage Limits, replay conflicting measurements, forge health evidence, or present synthetic observations as genuine production measurements.

Unless the parties sign an appropriate regulated-use addendum, Customer shall not submit payment-card authentication data, medical records requiring a health-data processing agreement, classified information, or other data whose processing requires protections not included in the purchased Service. Ordinary infrastructure identifiers and appropriately minimized operational personal data may be processed under the DPA. This paragraph does not transfer Provider's independent privacy obligations to Customer.

## 5. Technical scope, API limits, and changes

Provider shall describe the purchased functionality and material restrictions in the Order Form and Documentation. Monitoring results depend on authorized collectors, configurations, network access, accepted evidence, and external systems. Unknown or missing evidence is not a representation that a target is healthy. A worker heartbeat is not a target-health assertion. Sampled success reports are not a continuous uptime guarantee. Roadmap statements and illustrative marketing assets are not purchased features unless expressly incorporated.

The Order Form shall specify [INGESTION_REQUESTS_PER_MINUTE], [INGESTION_EVENTS_PER_DAY], [MAX_CONCURRENT_WORKERS], [CONTRACTED_STORAGE_GB], purchased retention, and any burst policy. These limits must be operationally validated and enforced before Provider sells the corresponding capacity. The current worker protocol separately requires valid assigned leased jobs, JSON requests, and a maximum 8 KiB request body; this limit is not a general OTLP batch quota. No generic ingestion SDK is included unless expressly supplied and identified.

Provider may throttle, queue, or reject requests exceeding agreed or documented limits and shall provide appropriate error information where technically practicable. Where HTTP 429 and Retry-After apply, Customer shall honor the retry instruction with bounded backoff. Provider shall not impose undisclosed retrospective usage charges or require unlimited retries. Temporary protective limits may be applied proportionately to an active security or availability threat; Provider shall notify Customer where feasible and work to restore normal service.

Provider shall not materially reduce purchased functionality during a paid Subscription Term without an agreed remedy. Material API deprecations shall have at least ninety days' notice where reasonably practicable. Urgent security changes may take effect sooner with prompt notice and migration guidance. Customer-hosted versions and agents must follow the supported compatibility matrix; Provider need not support an indefinitely outdated or modified deployment unless expressly contracted.

## 6. Availability, support, and external systems

The 99.9% monthly availability commitment in Schedule A applies only to an accepted production hosted Service expressly covered by the Order Form. It does not apply to Preview, local Docker demonstrations, customer-hosted uptime, monitored target uptime, or third-party incident-delivery availability. Contracted latency objectives, if any, must be separately stated with their measurement method and workload assumptions; none arise merely from the term “real-time.”

Provider shall supply the support plan purchased in the Order Form. Priority-one support response target is [P1_RESPONSE_TIME]; other priorities and business hours are [SUPPORT_SCHEDULE]. A response target is not a guaranteed resolution time. The parties shall maintain emergency contacts and reasonable escalation procedures.

Third-party integrations require Customer-authorized accounts and provider permissions. Provider shall protect credentials and validate supported integration responses as required by the DPA and security schedule. Provider does not warrant a third party's continued API availability or compatibility, but shall use commercially reasonable efforts to maintain expressly supported integrations. Provider's own hosting subcontractors remain its responsibility under this Agreement and are not treated as unrelated customer-selected third parties.

## 7. Subscription, fees, billing, and taxes

The Subscription Term, fees, currency, billing frequency, committed capacity, and any usage charges are stated in the Order Form. Unless the Order Form provides otherwise, undisputed invoices are payable within thirty days of receipt. Provider shall give an itemized basis for measurable overage charges. Overage rates require agreement before the relevant usage is charged.

Customer shall notify Provider of a good-faith invoice dispute within thirty days after receipt, describe the disputed amount and reason, and pay the undisputed portion when due. The parties shall promptly investigate. Provider shall not suspend service solely for a disputed amount while Customer cooperates in good faith. Late charges on overdue undisputed amounts shall not exceed the lesser of one percent per month or the maximum lawful rate, following written notice.

Fees exclude applicable transaction taxes, which Customer shall pay except taxes on Provider's net income, employment, or property. Provider shall accept valid exemption documentation. Required withholding shall be handled under applicable law, with lawful receipts and cooperation; any gross-up obligation must be expressly specified in the Order Form.

A subscription renews automatically only if the Order Form expressly states the renewal term and cancellation mechanism. Otherwise it expires at the stated end date. For agreed automatic renewal, either party may give non-renewal notice at least thirty days before expiration. Provider shall disclose any renewal price change at least sixty days before renewal. In-term price changes require written agreement except pre-agreed measured overage charges.

## 8. Ownership and permitted data use

Customer retains ownership and applicable rights in Customer Data, Customer marks, and Customer-owned configurations and content. Customer grants Provider the limited right to process Customer Data only to provide, secure, support, and maintain the purchased Service, comply with documented instructions, and meet applicable law. Personal Data processing is governed by the DPA. Provider shall not sell Customer Data, use it for unrelated advertising, or train a general-purpose model on it without a separate explicit written agreement and a lawful basis.

Provider retains ownership of its independently developed platform, Documentation, service methods, and improvements, subject to applicable third-party and open-source rights. No assignment of Customer's intellectual property arises merely because it is processed in the Service. Provider may use genuinely deidentified or aggregated operational information for service planning only if it cannot reasonably identify Customer or an individual, is not reidentified, and does not reveal Customer Confidential Information. A contractual label alone does not make identifiable information anonymous.

Customer may provide voluntary feedback. Provider may use that feedback without payment to improve its products, provided it does not disclose Customer Confidential Information or appropriate Customer Data. No transfer of a disclosed patent right arises without an express written license or assignment.

## 9. Security, privacy, and data processing

Provider shall implement the technical and organizational measures in the executed DPA/security schedule and maintain an appropriate security program. Provider shall notify and assist Customer with Personal Data breaches as required by the DPA. Provider shall not advertise a certification, independent audit, or compliance status unless the relevant scope and evidence have been verified.

The Privacy Policy governs Provider's independent processing of account, contact, website, and support information. The DPA governs processing of Customer Personal Data on Customer's behalf. Provider shall not use a change to a public Privacy Policy to expand the agreed processor purposes or override the DPA. Customer shall not disable security controls or share administrative credentials to obtain unsupported access.

## 10. Warranties and disclaimers

Each party warrants that it has authority to enter into this Agreement. Provider warrants that it has the rights necessary to grant the licenses it actually supplies, will perform professional services with reasonable skill and care, and will cause the purchased Service to perform materially in accordance with the applicable Documentation during the paid term. Customer shall promptly report a reproducible material nonconformity. Provider shall use commercially reasonable efforts to correct it. If Provider cannot correct a material nonconformity within thirty days after sufficient notice and cooperation, Customer may terminate the affected service and receive a prorated refund of prepaid unused fees.

Except for express warranties and mandatory rights that cannot lawfully be excluded, the Service and Software are provided without additional implied warranties, including implied merchantability, fitness for a particular purpose, or error-free operation. Monitoring is an operational aid and does not replace Customer's incident response, safety systems, backups, or independent decision-making. This disclaimer does not negate the express SLA, security obligations, or infringement indemnity.

Preview offerings are supplied for evaluation without a production availability commitment or a warranty of complete functionality. Preview conditions shall be identified clearly and do not waive mandatory privacy/security duties or justify negligent handling of Customer Data.

## 11. Confidentiality

“Confidential Information” means non-public information disclosed by one party to the other that is marked confidential or reasonably should be understood as confidential, including Customer Data, security findings, credentials, source code, business plans, pricing, and non-public technical information. Information is excluded to the extent the receiving party proves it was lawfully known without restriction, becomes public without breach, is independently developed without use of the disclosing party's information, or is lawfully received without confidentiality obligations.

The receiving party shall use Confidential Information only to perform or exercise rights under this Agreement, protect it using at least reasonable care, and disclose it only to personnel and authorized advisers who need it and are bound by appropriate confidentiality duties. Legally compelled disclosure is permitted after lawful advance notice where allowed and reasonable efforts to limit the disclosure. Neither party shall prevent protected legal reporting or impose an unlawful confidentiality restriction.

These obligations survive for five years after termination, except trade secrets remain protected while legally qualifying as trade secrets, and Personal Data/credentials remain protected for as long as retained. Return or deletion is subject to the DPA, lawful holds, and permitted inaccessible backup retention. Confidentiality does not authorize indefinite retention of unnecessary Personal Data.

## 12. Provider infringement indemnity

Provider shall defend Customer against a third-party claim that the purchased, unmodified Service or Software, used as authorized, infringes that third party's patent, copyright, trademark, or trade secret rights, and shall pay damages and reasonable settlement amounts finally awarded or approved by Provider. Customer shall promptly notify Provider, allow Provider to control the defense, and provide reasonable cooperation at Provider's expense. Delayed notice excuses responsibility only to the extent Provider is materially prejudiced.

Provider has no obligation to the extent a claim arises from Customer Data, an unauthorized Customer modification, a combination not supplied or reasonably contemplated by Provider when the claim would not otherwise arise, or use after Provider supplies a non-infringing replacement of materially equivalent function with reasonable migration assistance. Provider may obtain rights, modify or replace the affected component without material loss of contracted function, or, if those remedies are not commercially reasonable, terminate the affected component and refund prepaid unused fees. Provider may not settle a claim by admitting Customer fault or imposing a non-monetary obligation on Customer without its reasonable written consent.

## 13. Customer indemnity

Customer shall defend Provider against a third-party claim arising from Customer Data that Customer lacked the right or lawful authority to submit, or Customer's unlawful monitoring or intentional prohibited use, and shall pay damages and reasonable settlement amounts finally awarded or approved by Customer. Provider shall give prompt notice, allow Customer to control the defense, and reasonably cooperate at Customer's expense. Customer has no obligation for a claim to the extent caused by Provider's breach, unauthorized processing, negligence, or willful misconduct. Customer may not impose an admission or non-monetary obligation on Provider without its reasonable written consent.

## 14. Liability allocation

To the maximum extent permitted by applicable law, neither party is liable for indirect, special, exemplary, or consequential damages, or lost profits, arising from this Agreement. This exclusion does not prevent recovery of amounts payable to a third party under an express indemnity or reasonably foreseeable direct costs of investigation, notification, restoration, and mitigation of a covered confidentiality or Personal Data breach.

Each party's aggregate liability arising from the Agreement shall not exceed fees paid or payable for the affected services during the twelve months before the first event giving rise to the claim. The cap for breach of confidentiality or the DPA/security obligations, and express indemnification obligations, is twice that amount. Amounts properly owed by Customer for purchased services are payment obligations and are not reduced by this liability cap.

The exclusions and caps do not apply to fraud, willful misconduct, liability for death or personal injury caused by negligence where non-excludable, or any other liability that applicable law does not permit the parties to limit. Nothing limits a regulator's powers or an individual's mandatory privacy rights. Regulatory fines are reimbursable between the parties only to the extent lawfully transferable and attributable under applicable law; this Agreement does not purport to eliminate statutory accountability.

## 15. Suspension, termination, and data return

Provider may suspend affected access only to the extent reasonably necessary for an actual security threat, unlawful use, material interference, or overdue undisputed payment remaining uncured fifteen days after written notice. Where practicable, Provider shall notify Customer before suspension, identify the affected functions, permit remediation, and avoid unnecessary interruption of unaffected services. Protective suspension does not authorize destruction of Customer Data.

Either party may terminate for material breach not cured within thirty days after written notice identifying the breach. A breach that cannot reasonably be cured may justify immediate termination as permitted by law. Either party may terminate if the other enters insolvency proceedings to the extent applicable law permits. Customer may exercise the additional remedies in the warranty and SLA provisions.

At termination, subscription access and term-limited licenses end. Provider shall make Customer Data available through supported export or an agreed assisted export for thirty days, subject to lawful security restrictions and agreed reasonable assistance charges. Provider shall then return or delete Customer Personal Data as required by the DPA and verified retention schedule. Historical/audit categories lacking a compliant deletion mechanism must be remediated before Provider accepts that contractual obligation; Provider may not conceal such a limitation behind an unsigned policy. Customer-hosted data remains Customer's responsibility unless managed deletion is purchased.

If Customer terminates for Provider's uncured material breach or a stated SLA termination right, Provider shall refund prepaid unused affected-service fees. Customer shall pay earned undisputed fees through termination. Ownership, confidentiality, accrued payment, indemnity, liability, data-protection obligations while data remains held, and dispute provisions survive as their nature requires.

## 16. Export, sanctions, and legal compliance

Each party shall comply with export controls and sanctions applicable to its activities. Customer shall not knowingly provide access to a prohibited destination or person, or use the Service for a prohibited end use. Provider shall not require Customer to violate an applicable blocking statute or lawful local restriction; the parties shall address conflicts through a lawful contractual solution. Customer remains responsible for authorization to monitor its targets; Provider remains responsible for its own legal duties.

## 17. General terms

This Agreement is governed by [GOVERNING_LAW], excluding conflict-of-law rules, without limiting applicable mandatory law or the DPA transfer provisions. The courts located in [EXCLUSIVE_FORUM] have jurisdiction over disputes unless the Order Form includes a mutually agreed arbitration clause. Before litigation, senior representatives shall attempt good-faith resolution for thirty days; either party may seek urgent relief where permitted without waiting for that period.

Neither party is liable for delay caused by an event beyond its reasonable control if it promptly notifies the other, mitigates the effects, and resumes performance. Ordinary capacity shortages, avoidable security failures, or failure to maintain agreed continuity measures are not automatically force majeure. If the event materially prevents performance for thirty days, the affected party may terminate the affected service and receive a refund of prepaid unused fees.

Neither party may assign the Agreement without the other's reasonable consent, except to an Affiliate or in a merger, reorganization, or sale of substantially all relevant assets if the successor assumes the obligations and the transfer does not materially increase privacy/security risk. The assigning party shall give notice. A subprocessor appointment remains subject to the DPA and is not exempt because it is affiliated.

Notices shall be sent to the contract addresses in the Order Form and [CONTACT_EMAIL]. Material legal notices are effective on confirmed delivery or the next business day after documented electronic receipt; incidental support messages are not a substitute. A failure to enforce a clause is not a waiver. If a provision is unenforceable, the remainder survives to the extent lawful; this clause does not authorize rewriting an illegal restraint to obtain a prohibited result. The parties are independent contractors. This Agreement is the entire agreement for its subject matter. Amendments must be agreed in writing; a material online change does not retroactively alter a paid term without Customer consent.

## Schedule A. Production hosted-service SLA

### A1. Scope and commencement

The SLA applies to the production hosted control-plane components identified in the Order Form after [PRODUCTION_ACCEPTANCE_DATE]. Covered components are authenticated UI access, contracted API read/write operations, and valid assigned-worker result acceptance in [CONTRACTED_REGIONS]. Preview features, customer-hosted availability, third-party monitored targets, and customer-selected external notification endpoints are excluded. Provider shall deploy measurement, incident, and credit procedures before promising this SLA.

### A2. Availability calculation

Monthly Availability Percentage equals `100 × (Eligible Minutes − Unavailable Minutes) / Eligible Minutes`. Eligible Minutes are the calendar-month minutes during the covered paid service period minus valid excluded minutes. Unavailable Minutes are non-overlapping eligible one-minute intervals when the contracted core operation cannot be completed by a valid authorized request within thirty seconds because of a Provider-controlled failure, confirmed by monitoring or credible Customer evidence. Failure of a covered UI component is assessed according to the Order Form's component scope, not dismissed solely because a health endpoint responds.

Overlapping incidents count once. Provider shall not exclude its own hosting/cloud/CDN subcontractor outage simply because a third party supplied the infrastructure. Where multiple contracted regions or components have separate availability terms, the Order Form shall identify the weighting and affected fees before measurement begins. Monitoring coverage gaps shall not automatically be treated as available minutes.

### A3. Commitment and exclusions

Provider commits to Monthly Availability Percentage of at least **99.9%**. A thirty-day month has 43.2 minutes of unavailability allowance before applying valid exclusions; this illustration does not alter the formula.

Exclusions are Customer-caused configuration or credential failures, Customer-controlled infrastructure/network failures outside Provider's responsibility, unauthorized use directly causing the failure, an expressly applicable force-majeure event despite reasonable mitigation, and scheduled maintenance notified at least forty-eight hours in advance and limited to two hours per month. Maintenance exceeding that allowance counts unless Customer expressly agrees otherwise. Emergency security maintenance is excluded only to the extent genuinely necessary, promptly notified, and reasonably minimized; a routine defect correction is not automatically emergency maintenance.

### A4. Credits and claim process

If Monthly Availability is at least 99.0% but below 99.9%, the credit is ten percent of the affected monthly recurring hosted-service fee. If availability is at least 95.0% but below 99.0%, the credit is twenty-five percent. If availability is below 95.0%, the credit is fifty percent. Total availability credits for a month shall not exceed fifty percent of that affected monthly recurring fee. One-time fees, taxes, and unrelated components are excluded from the credit base.

Customer shall submit a claim to [SLA_CONTACT_EMAIL] within thirty days after the affected month, identifying the account, component, interval, and reasonably available evidence. Provider shall acknowledge and investigate within ten business days and provide its decision and calculation within thirty days after sufficient information is received. Provider shall not demand access to unrelated Customer data. Approved credits apply to the next invoice or are refunded if no further invoice is due. Timely credible evidence may establish downtime where Provider monitoring failed.

### A5. Repeated failure and remedies

Customer may terminate the affected hosted service if it fails the 99.9% commitment in three months within any rolling six-month period, by notice within thirty days after the third failure. Provider shall refund prepaid unused affected-service fees. Service credits are the monetary remedy for ordinary availability failures alone; they do not extinguish independent claims for breach of confidentiality, the DPA, indemnity, fraud, willful misconduct, or mandatory legal rights. Customer shall not receive duplicate compensation for the same loss.

## Schedule B. Order Form and signature record

Customer legal name: [CUSTOMER_LEGAL_NAME]  
Customer address: [CUSTOMER_ADDRESS]  
Purchased deployment and version: [DEPLOYMENT_AND_VERSION]  
Subscription start/end: [SUBSCRIPTION_START_DATE] / [SUBSCRIPTION_END_DATE]  
Production acceptance date: [PRODUCTION_ACCEPTANCE_DATE]  
Fees, currency, and billing: [FEES_CURRENCY_BILLING]  
Capacity, burst, region, and retention: [CAPACITY_REGION_RETENTION_SCHEDULE]  
Support schedule and emergency contacts: [SUPPORT_SCHEDULE_AND_CONTACTS]  
Renewal election: [RENEWAL_TERMS_OR_NO_AUTOMATIC_RENEWAL]  
Negotiated amendments: [NEGOTIATED_AMENDMENTS_OR_NONE]  
DPA and security schedule version: [DPA_SECURITY_VERSION]

For [COMPANY_NAME]: [AUTHORIZED_SIGNATORY_NAME], [TITLE], signature [SIGNATURE], date [SIGNATURE_DATE].

For Customer: [AUTHORIZED_SIGNATORY_NAME], [TITLE], signature [SIGNATURE], date [SIGNATURE_DATE].


---

# [COMPANY_NAME] Enterprise Privacy Policy

Product: [PRODUCT_NAME]  
Effective date: [EFFECTIVE_DATE]  
Policy activation for the covered hosted service: [POLICY_ACTIVATION_DATE]  
Privacy contact: [PRIVACY_CONTACT_EMAIL]  
Postal address: [COMPANY_ADDRESS]  
General contact: [CONTACT_EMAIL]

**Publication condition.** This notice must be completed against actual processing records, suppliers, locations, legal bases, retention/deletion capability, and applicable-law commencement before publication. It does not certify GDPR, CCPA/CPRA, or India's DPDP compliance. The current self-hosted development implementation and the intended hosted policy are distinguished below so that a future operational commitment is not represented as an implemented fact.

## 1. Scope and responsibility

This Policy explains how [COMPANY_NAME] handles Personal Information in connection with the covered [PRODUCT_NAME] hosted service, company account administration, support, and the website identified as [COVERED_WEBSITE]. “Personal Information” includes information relating to an identified or identifiable person and the equivalent concepts under applicable privacy law.

For business account contacts, billing administration, company website activity, and Provider-directed support/security administration, [COMPANY_NAME] generally determines processing purposes and acts as controller or the equivalent responsible business/Data Fiduciary. For personal information contained in customer-configured telemetry, logs, resource metadata, and investigations processed solely on Customer's documented instructions, the Customer generally determines the purposes and we act as processor or service provider. The DPA governs that processing. The actual roles depend on the purpose and facts, not a label in a contract.

For customer-hosted installations, Customer operates the environment and controls the data unless a separately agreed managed-service or support arrangement provides us access. Installing Software does not automatically transmit the customer-hosted database to [COMPANY_NAME]. This Policy does not replace Customer's employee, application-user, or monitoring notices. Individuals whose information appears in a Customer's telemetry should ordinarily contact that Customer for rights requests; we assist it under the DPA.

## 2. Information collected and sources

We collect the information necessary for the selected deployment and configured processing. The categories below must be confirmed against the actual service and website before activation.

| Category | Examples and sources | Purposes |
|---|---|---|
| Account and business contact information | Name, business email, employer, role, username, account status, and authorized organization membership supplied by a user or Customer administrator | Account creation, access administration, contract communications, and support |
| Authentication and security information | Password hashes, token digests, session records, credential identifiers, timestamps, security events, and originating IP addresses | Authentication, revocation, abuse prevention, audit, and incident investigation |
| Operational telemetry and resource metadata | Service/host identifiers, IP addresses, resource names, timing, availability, CPU/memory/disk/process measurements, provider inventory, and job state supplied by configured collectors | Monitoring, correlation, health history, reporting, and Customer-directed investigation |
| Customer-configured logs and investigation content | Log messages, execution/step details, timestamps, available correlation IDs, notes, and attachments if supported | Operational troubleshooting, incident lifecycle, and authorized evidence export |
| Infrastructure and access logs | Request route, status, time, system identifiers, user/worker identity references, and network information produced by service operations | Reliability, security, audit, and debugging |
| Support communications | Contact details, issue descriptions, sanitized diagnostics, and information a Customer voluntarily supplies | Resolving requests, maintaining the service, and documenting agreed changes |
| Billing and contract records | Business billing contact, invoice details, transaction references, plan, and purchase history; payment information handled by the approved payment provider where used | Payment, financial reporting, tax, contract performance, and disputes |
| Browser preferences and website activity | Theme preferences, necessary session storage, and website events only where actually deployed and disclosed in the cookie register | Necessary operation, saved preferences, and lawfully authorized website measurement |

Log content may contain Personal Information even if the intended measurement is technical. Customers must minimize collection and exclude unnecessary credentials, authentication headers, private response bodies, employee content, and regulated data. We do not request that customers submit secrets as telemetry. Secret references identify credentials; they are not permission to include the credential value in a log.

The implemented remote HTTPS result protocol accepts sanitized outcome, status, timing, size, and related job identifiers. It does not forward raw target response bodies, cookies, passwords, or arbitrary target logs through that protocol. Other adapters and authorized support access may process configured data separately and require their own inventory.

## 3. Purposes and restrictions

We use Personal Information to provide and secure the covered service, administer authorized accounts, perform the contract, respond to support and privacy requests, maintain operational integrity, investigate misuse, and meet applicable legal obligations. Customer telemetry is processed on the Customer's instructions and within the DPA's permitted purposes.

We do not sell Customer telemetry, share it for cross-context behavioral advertising, or train a general-purpose model on it under the standard service terms. Any optional materially different use requires a separate explicit agreement, an appropriate lawful basis, and an updated notice before processing. We do not treat acceptance of product terms as universal consent for unrelated marketing.

We may use truly deidentified or aggregated information for reliability and capacity planning if it cannot reasonably identify an individual or Customer, is not reidentified, and does not disclose confidential information. Pseudonymized identifiers and hashed values may remain Personal Information; hashing alone does not remove privacy obligations.

## 4. GDPR and other European privacy provisions

Where the GDPR applies to our controller processing, the applicable bases are contract performance under Article 6(1)(b) for necessary account/service interactions with a contracting individual; legitimate interests under Article 6(1)(f) for proportionate business-contact administration, security, reliability, and abuse prevention after a documented balancing assessment; legal obligation under Article 6(1)(c) for applicable financial or regulatory duties; and consent under Article 6(1)(a) for optional processing requiring consent. If the contracting party is an organization rather than the individual, we do not automatically characterize every employee-contact use as contract performance with that employee.

Where sensitive categories under Article 9 or criminal-offense information under Article 10 are involved, processing requires the separate applicable condition and safeguards. The standard service is not intended to accept these categories without an approved arrangement. We shall not rely on a generic contract clause to satisfy those conditions.

Individuals may request access, correction, erasure, restriction, portability where applicable, and objection. They may object at any time to direct marketing. Where processing relies on consent, they may withdraw it without affecting the lawfulness of earlier processing. Rights are subject to lawful exceptions, including necessary security, legal duties, other individuals' rights, and defense of legal claims. We shall explain an applicable restriction rather than ignore the request.

We respond to GDPR rights requests without undue delay and ordinarily within one month. Where legally permitted due to complexity or number, we may extend by up to two further months and explain the extension within the first month. We use proportionate identity verification and do not routinely demand excessive identity documents. An authorized representative may act where the law permits.

Individuals may complain to the supervisory authority for their habitual residence, workplace, or alleged infringement and may seek available judicial remedies. Our applicable establishment, lead authority, EU representative, and Data Protection Officer, if legally required or appointed, are [EU_ESTABLISHMENT_AND_AUTHORITY], [EU_REPRESENTATIVE_CONTACT], and [DPO_CONTACT]. These fields must reflect the actual arrangement; an arbitrary selected authority does not establish one-stop-shop eligibility.

## 5. California CCPA/CPRA provisions

Where the CCPA as amended by the CPRA applies and we act as a covered business, California residents may request disclosure of the categories and specific pieces of Personal Information collected, the categories of sources, purposes, and recipients; deletion subject to exceptions; correction; and applicable information about sale or sharing. They may opt out of sale or sharing where it occurs and limit the use/disclosure of Sensitive Personal Information where the statutory right applies. They may not be discriminated against for exercising protected rights.

In the preceding twelve months, the applicable categories for the covered service are identifiers, employment/business-contact information, commercial information, internet/network activity, and technical information that may identify a person, to the extent actually collected as described above. Account credentials and other information may constitute Sensitive Personal Information under applicable definitions. We do not collect precise geolocation merely because an IP address is recorded, and we do not claim that a category is collected if it is not present in the actual processing register.

We disclose necessary information to the contractual recipients in Section 8 for service delivery, support, security, billing, or legal purposes. Under the standard service we do not sell Personal Information or share it for cross-context behavioral advertising, and we have no actual knowledge of selling/sharing information of persons under sixteen. There are no financial incentives offered in exchange for Personal Information under this Policy. If the website or a later feature changes these facts, the notice, controls, and contracts must be updated before deployment.

Submit a request through [PRIVACY_REQUEST_PORTAL] or [PRIVACY_CONTACT_EMAIL], or through [CALIFORNIA_REQUEST_TELEPHONE] if required for our business. We acknowledge verifiable requests within the legally required period, ordinarily ten business days, and respond within forty-five calendar days where applicable. A lawful extension may provide up to an additional forty-five days with timely notice. Authorized agents may submit requests subject to permitted verification and proof of authority. We do not charge or demand verification contrary to applicable regulations.

We honor legally required recognized opt-out preference signals, including Global Privacy Control where applicable to sale/sharing, and do not require an unnecessary account to exercise an opt-out right. Implementation of the applicable signal, request, and Sensitive Personal Information controls must be tested before a covered practice is enabled. When we act as a service provider or contractor for Customer information, we process under the applicable restrictions and assist Customer in responding rather than assert a business's independent right to repurpose that information.

## 6. India Digital Personal Data Protection provisions

For processing within the territorial and material scope of the Digital Personal Data Protection Act, 2023, and rules and commencement provisions applicable at the relevant time, we identify the responsible Data Fiduciary and the permitted basis and purposes before processing. A website notice does not itself establish a lawful basis. Processing requiring consent shall follow a clear, accessible notice and a freely given, specific, informed, unconditional, and unambiguous indication by clear affirmative action. Where a legally permitted legitimate use applies, we shall document that use rather than treat it as general permission for all processing.

The Indian framework includes phased commencement and implementing requirements that must be verified against current official notifications before publication and operation. This template does not assert that every provision of the Act or implementing rules is already operative on [EFFECTIVE_DATE]. The obligations below apply when legally applicable and may be offered voluntarily as service procedures before then without misrepresenting statutory commencement.

Individuals may request the legally applicable summary of processing and disclosures, correction, completion, updating, and erasure; withdraw consent through an accessible mechanism; use the grievance procedure; and nominate a person to exercise rights in the legally specified circumstances. We shall stop consent-based processing following withdrawal within a reasonable period as required, except processing that another applicable law authorizes or requires. Withdrawal shall not be made materially harder than giving consent.

Submit requests and grievances to [INDIA_GRIEVANCE_CONTACT_NAME] at [INDIA_GRIEVANCE_EMAIL] or [PRIVACY_REQUEST_PORTAL]. We target a response within thirty calendar days unless the applicable law requires sooner, and never later than the applicable legal maximum. A stated service target is not a claim that the Act universally imposes a thirty-day deadline. Individuals may use the Data Protection Board or other competent remedy when available under operative law and after applicable grievance procedures. Any legally required language options, notices, contact publication, and accessibility must be operationally provided before deployment.

We shall apply reasonable security safeguards, processor contracts, accuracy obligations where relevant, lawful erasure, and legally required breach notifications. If designated as a Significant Data Fiduciary, we shall fulfill the additional applicable obligations, including required local DPO arrangements, independent audits, and impact assessments. We do not claim such a designation or compliance without evidence. Cross-border processing shall comply with operative restrictions and other applicable Indian sectoral law.

## 7. Browser storage, cookies, and operational analytics

The current application stores a human bearer session token in browser sessionStorage and theme and selected navigation-clock timezone preferences in localStorage. The baseline does not use a cookie-based login or an installed advertising tracker. Session storage is distinct from a cookie but still requires privacy and security consideration. Clearing the session token signs the user out; clearing preference storage resets the relevant preferences. Stored browser tokens expire or can be revoked through the server's authentication controls.

Any additional website cookies, pixels, SDKs, replay tools, or optional analytics must be listed in [COOKIE_AND_STORAGE_REGISTER] with provider, purpose, duration, recipient, and consent category. Necessary storage shall be limited to necessary purposes. Optional storage or tracking requiring consent shall remain disabled until valid consent is obtained, and withdrawal shall be available through [COOKIE_PREFERENCE_CONTROL]. We do not deploy session replay that captures credentials or customer telemetry under this standard notice. Provider-directed analytics must not be silently added to a customer-hosted build.

## 8. Recipients and subprocessors

We disclose Personal Information only as necessary to approved hosting/infrastructure providers, contracted support/security providers, billing processors, professional advisers, legally authorized authorities, and recipients Customer instructs or authorizes. Each relevant processor/subprocessor must be bound by appropriate confidentiality, security, purpose, transfer, and deletion terms. Customer-enabled integrations, such as a customer's own ServiceNow tenant, may be independent recipients selected by Customer rather than our own subprocessors; the actual relationship must be recorded.

The live subprocessor register is [SUBPROCESSOR_REGISTER_URL]. Before activation it must contain each actual legal entity, service, processing purpose, data categories, hosting/access locations, and transfer safeguard. At minimum, complete the following records; a blank row is not disclosure:

| Legal entity | Role and purpose | Data processed | Hosting/access country | Safeguard and contact |
|---|---|---|---|---|
| [HOSTING_PROVIDER_LEGAL_NAME] | [HOSTING_PURPOSE] | [HOSTING_DATA_CATEGORIES] | [HOSTING_COUNTRIES] | [HOSTING_TRANSFER_SAFEGUARD] |
| [SUPPORT_PROVIDER_LEGAL_NAME_OR_NONE] | [SUPPORT_PURPOSE] | [SUPPORT_DATA_CATEGORIES] | [SUPPORT_COUNTRIES] | [SUPPORT_TRANSFER_SAFEGUARD] |
| [PAYMENT_PROVIDER_LEGAL_NAME_OR_NONE] | [BILLING_PURPOSE] | [BILLING_DATA_CATEGORIES] | [BILLING_COUNTRIES] | [BILLING_ROLE_AND_SAFEGUARD] |
| [OTHER_SUBPROCESSOR_LEGAL_NAME_OR_NONE] | [OTHER_PURPOSE] | [OTHER_DATA_CATEGORIES] | [OTHER_COUNTRIES] | [OTHER_TRANSFER_SAFEGUARD] |

We do not infer that AWS, a particular cloud region, or a payment processor is in use merely because the code contains a connector. Corporate transfers may involve Personal Information only with appropriate safeguards, purpose continuity, and notice where required. We shall not authorize an acquiring party to disregard applicable privacy rights.

## 9. International transfers and residency

The contracted hosting region is [HOSTING_REGION]. Remote support and subprocessors may create additional access locations listed in the register; hosting location alone is not a complete transfer analysis. We use applicable adequacy decisions or valid contractual mechanisms with necessary supplementary measures for regulated European transfers. Where required, the executed DPA incorporates the appropriate EU Standard Contractual Clauses, UK Addendum or other valid UK mechanism, and Swiss modifications.

We assess transfer risks and government-access conditions where legally required, minimize access, and challenge unlawful or disproportionate demands where appropriate and permitted. We do not promise that an arbitrary region selection satisfies every localization requirement. India and other jurisdiction-specific restrictions and sectoral obligations must be reviewed for the actual deployment before transfer.

## 10. Retention, deletion, and preservation

We retain information only for identified purposes and lawful duties, apply the agreed retention schedule, and distinguish live systems, archives, correlated evidence, and backups. The intended hosted schedule below must be validated before Policy activation. An Order Form may provide a shorter lawful telemetry period. A longer period requires a recorded purpose, lawful basis, and agreed scope; Customer cannot order us to ignore a mandatory deletion duty.

| Category | Intended hosted retention and trigger |
|---|---|
| Raw metric samples | 365 days from observation unless the Order Form specifies another approved period |
| Raw log events | Thirty days from observation unless the Order Form specifies another approved period |
| Investigation-linked evidence | While the investigation requires it, then up to 365 days after closure, subject to a documented legal/security preservation requirement |
| Incident, ETL, and collector-run histories | Up to 365 days after closure or run completion, subject to the contracted lawful schedule |
| Security/audit events | Up to 365 days after the event unless a documented legal/security need requires a different period |
| Active account and membership records | During authorized service use, then deletion or deidentification within thirty days after closure except separately necessary records |
| Expired human sessions and short-lived throttling state | Removed through scheduled bounded maintenance; no later than seven days after expiry/purpose completion in the intended hosted operation |
| Support tickets and diagnostics | Up to twenty-four months after ticket closure; unnecessary sensitive attachments are removed earlier |
| Billing and tax records | [STATUTORY_ACCOUNTING_RETENTION_PERIOD] from the legally applicable trigger; limited to records necessary for that duty |
| Routine backups | Rolling thirty-five-day period; deleted live information becomes inaccessible for ordinary use and expires with the backup cycle |

Routine deletion jobs shall execute within seven days after the applicable retention trigger in the intended hosted operation, except the shorter account/request deadlines expressly agreed or required by law. On a lawful legal hold, preserve only the necessary categories, restrict access and ordinary use, record the reason and owner, and review the hold at least every ninety days. At hold release, apply the otherwise applicable deletion period. A vague indefinite “business need” is not a sufficient preservation reason.

The current self-hosted development code defaults raw metrics to 365 days and logs to thirty days, requires authorized maintenance scheduling, and excludes correlated evidence from ordinary cleanup. Audit, collector-run, incident, and ETL history currently lack an approved finite archive/deletion mechanism and remain retained until such a mechanism is implemented. This is a production launch blocker for the intended finite hosted commitments above, not an undisclosed exception to them. Do not publish the intended schedule as accomplished behavior until tested.

Backups retained after live deletion must not be used for unrelated purposes. If restoration is necessary, reapply deletion requests and retention controls before ordinary processing resumes. Data-subject erasure may be limited by a lawful preservation duty; we shall explain the applicable reason and scope. Termination export and deletion follow the DPA and executed service agreement.

## 11. Security and breach response

We implement the measures described in the executed security schedule, including authenticated access, organization scope, protected credentials, appropriate TLS, least-privilege database roles, secure deployment configuration, and incident procedures. Certifications and independent reviews shall be disclosed only when obtained and applicable to the actual service scope. No security measure guarantees that all incidents are impossible.

We shall assess suspected incidents promptly, contain and investigate them, preserve appropriate evidence, and give legally required notices to responsible Customers, individuals, and authorities. Under GDPR controller obligations, supervisory-authority notice is required without undue delay and, where feasible, within seventy-two hours after awareness when the statutory threshold is met; processor notice to the controller is without undue delay. High-risk individual notice is assessed separately. Indian and other notice timing/content follow the operative law and applicable rules rather than automatically copying the GDPR deadline.

## 12. Children and account eligibility

The service is designed for business users and is not directed to children. We do not knowingly establish accounts for persons under eighteen under the standard account policy. Customer telemetry can nevertheless contain information about individuals of different ages; Customer must identify and authorize any permitted child-data processing rather than rely on the account-age statement.

Where applicable Indian child-data provisions apply, verifiable parental consent and statutory restrictions on detrimental processing, tracking, behavioral monitoring, and targeted advertising shall be respected, subject only to legally applicable exceptions. Customer must not configure child-directed surveillance or submit children's information requiring unsupported safeguards. If unauthorized child-data processing is identified, contact [PRIVACY_CONTACT_EMAIL] so that the responsible parties can assess and lawfully remove or restrict it.

## 13. Requests, complaints, and policy changes

Use [PRIVACY_REQUEST_PORTAL], [PRIVACY_CONTACT_EMAIL], or the contact method provided by the Customer controlling your information. We shall authenticate requests proportionately, protect other individuals' information, document the outcome, and provide an explanation and available complaint route when a request is restricted. We shall not charge a fee unless the applicable law permits it and the required conditions are satisfied.

We may update this Policy to reflect processing or legal changes. We shall display the effective date, retain an appropriate prior version, and provide material-change notice through [POLICY_NOTICE_METHOD]. New consent shall be obtained where required. A Policy update does not amend an executed DPA or authorize incompatible processing of previously collected information. Questions, accessibility requests, and privacy complaints may be sent to [PRIVACY_CONTACT_EMAIL] or [COMPANY_ADDRESS].


---

# Proprietary Information and Inventions Agreement

Effective date: [EFFECTIVE_DATE]

This Proprietary Information and Inventions Agreement (“Agreement”) is between [COMPANY_NAME], of [COMPANY_ADDRESS] (“Company”), and [CONTRIBUTOR_LEGAL_NAME], of [CONTRIBUTOR_ADDRESS] (“Contributor”). Contributor is engaged as [EMPLOYEE_CONTRACTOR_OR_CONSULTANT] under [EMPLOYMENT_OR_SERVICES_AGREEMENT] beginning [ENGAGEMENT_START_DATE].

This Agreement protects legitimate confidentiality and intellectual-property interests without requiring assignment of unrelated personal work, rights Contributor does not own, or rights protected from assignment by mandatory law. Company shall complete the schedules and applicable local notices before signature. No clause is intended to create an enforceable global non-compete where the governing law prohibits it.

## 1. Consideration and relationship

In consideration of employment or services, agreed compensation under the engagement agreement, access to Company information, and additional consideration of [ADDITIONAL_CONSIDERATION_IF_REQUIRED], Contributor agrees as follows. If executed after an engagement has begun, the parties shall provide fresh consideration or use a legally effective execution form where required; this document does not assume that past compensation alone is sufficient in every jurisdiction.

Contractor classification does not determine legal employment status contrary to applicable law. This Agreement does not vary lawful compensation, benefits, termination protections, collective rights, or mandatory employee-invention compensation. An entity providing consultants shall execute an appropriate entity assignment and procure consistent agreements from the individual creators; an entity's signature alone does not transfer rights its personnel have retained.

## 2. Definitions and covered contributions

“Company Work Product” means code, software, algorithms, databases and database structures, APIs, agent/SDK implementations, tests, scripts, infrastructure definitions, architectures, configurations, Documentation, designs, interface assets, graphics, training material, inventions, discoveries, improvements, patentable subject matter, trade secrets, and other protectable materials that Contributor creates, authors, conceives, develops, or reduces to practice, alone or with others, in performing assigned services or duties for Company, or otherwise within a scope validly assignable under applicable law.

“Background Materials” means identifiable pre-existing materials or rights Contributor owns before the engagement, and lawful independently developed materials outside Company Work Product. “Company Confidential Information” includes non-public source code, architecture, security controls, credentials, telemetry, customer information, supplier terms, product plans, commercial information, and protected information Company receives from others. “Third-Party Materials” includes open-source software, stock assets, external datasets, licensed tools, and material owned by another employer or client.

Unrelated past work and all future work merely because it is software or design are not automatically Company Work Product. Existing contributions intended for retrospective assignment must be specifically identified in Schedule A. Future assignment applies to defined Company Work Product, not to every invention Contributor may create for life.

## 3. Present assignment of existing and future Company Work Product

Contributor hereby irrevocably assigns to Company all of Contributor's right, title, and interest in and to the existing Company Work Product identified in Schedule A and, to the fullest extent a present assignment of future rights is legally effective, all Company Work Product created during the engagement. Assigned rights include applicable copyrights, patent and invention rights, design rights, database rights, trade-secret interests, applications, registrations, renewals, extensions, and the right to bring and retain recoveries from claims for infringement of those assigned rights, to the extent assignable.

The assignment is worldwide and lasts for the full legal term of each assigned right, including lawful renewals and extensions. It covers all legally transferable economic exploitation rights, including reproduction, adaptation, modification, translation, distribution, publication, public performance/display, communication, making available, commercialization, licensing, and creation of derivative works in existing and future media to the extent legally effective. The agreed engagement compensation and any additional consideration above constitute the assignment consideration, subject to mandatory remuneration rights.

Where a future assignment is not effective until creation, Contributor shall hold the relevant rights for Company's benefit to the extent lawful and assign them to Company immediately when they arise. Contributor shall execute the necessary confirmatory assignment without additional discretionary compensation, except mandatory compensation, agreed reimbursement, or legally required consideration. The parties intend ownership to vest in Company at the earliest legally permissible time; this intention does not eliminate mandatory formalities.

To the extent permissible under Indian copyright law, the parties specifically identify the works through Schedule A and the ongoing creation records, state the full-term duration and worldwide territory, and agree that an assigned right shall not lapse solely because Company has not exercised it within one year. That agreement applies only to the extent lawful and does not override non-waivable statutory rights or remedies. Other local assignment formalities and required specificity must be addressed in the applicable schedule.

Contributor retains no ownership interest in Company Work Product except mandatory non-transferable rights. If any legally assignable right cannot be transferred for a reason other than a protected statutory exclusion, Contributor grants Company an exclusive, worldwide, fully paid, transferable and sublicensable license for its full legal term to exercise that right to the extent lawful. No fallback license applies to inventions that mandatory law protects from Company ownership unless Contributor separately and voluntarily agrees to an appropriate license after disclosure.

## 4. Work made for hire and moral rights

Copyright works qualify as work made for hire only where the applicable law and facts support that treatment. To that extent Company is the initial owner. All other assignable Company Work Product is covered by the assignment above. The parties do not rely on the words “work made for hire” to transfer contractor work that does not qualify under the relevant law.

To the maximum extent lawful, Contributor waives waivable moral rights in Company Work Product and consents to reasonable editing, adaptation, combination, publication, and omission of attribution for product operation and commercialization. Where moral rights cannot be waived, Contributor gives the lawful consents needed for those uses and agrees not to assert them inconsistently with those consents, except where the law preserves a right that cannot be contractually restricted. This clause does not authorize false attribution or unlawful derogatory treatment, and does not purport to transfer non-assignable Indian or other statutory moral rights.

## 5. Background Materials and excluded inventions

Contributor shall list relevant Background Materials and excluded inventions in Schedule B, sufficiently identifying ownership, applicable license, and intended use. A blank schedule shall be completed as “None declared” only after a genuine review. Failure to list material does not transfer a third party's ownership or extinguish mandatory employee-invention protections; Contributor remains responsible for accurate disclosure.

Contributor shall not incorporate Background Materials into Company Work Product without Company's written approval. For approved incorporation, Contributor grants Company a perpetual, worldwide, non-exclusive, irrevocable, fully paid license to use, reproduce, modify, distribute, display, perform, make available, and sublicense the incorporated Background Materials as necessary to use and exploit the resulting Company Work Product, to the extent Contributor owns and may license those rights. The schedule may specify a different agreed license where necessary. Contributor shall identify restrictions before approval.

This Agreement excludes inventions protected under applicable employee-invention statutes. In California, the assignment does not apply to an invention developed entirely on Contributor's own time without Company's equipment, supplies, facilities, or trade-secret information, except an invention that relates at conception or reduction to practice to Company's business or actual or demonstrably anticipated research/development, or results from work performed for Company. A provision purporting to assign an invention otherwise protected by California Labor Code section 2870 is not intended to be enforced. Applicable written notices and additional protections in other jurisdictions must be supplied.

Contributor shall disclose potentially relevant inventions through a confidential process sufficient to assess whether they are covered or excluded. Company shall not require unnecessary disclosure of a third party's trade secrets or treat disclosure alone as an assignment. A disputed exclusion shall be resolved under applicable law, not by unilateral deletion of the schedule.

## 6. Third-party materials and open-source compliance

Contributor shall not introduce another employer's or client's proprietary information, unlawfully copied code, unlicensed design assets, or Third-Party Materials inconsistent with the project license and distribution plan. Contributor shall obtain written approval before incorporating material subject to source-disclosure, attribution, patent, copyleft, redistribution, or other obligations that materially affect Company's intended use.

Contributor shall maintain an accurate component and asset provenance record, preserve required notices, disclose license terms, and provide the information necessary for the software bill of materials and source obligations. Company owns only rights validly acquired; this Agreement does not appropriate open-source copyright or eliminate a public license. Joint creators and subcontractors must supply valid assignments for their own contributions before Company claims exclusive ownership.

Contributor shall not submit Company code or customer data to an external generative-AI or cloud tool without approved terms and a permitted data-handling arrangement. Contributor shall record approved AI-assisted contributions, review their provenance and quality, and avoid representations of exclusive copyright where the applicable law does not recognize that right. Company approval of a tool does not waive confidentiality or licensing obligations.

## 7. Confidentiality and permitted use

Contributor shall use Company Confidential Information only to perform authorized duties, protect it with at least reasonable care, and disclose it only to authorized persons with a genuine need and appropriate confidentiality obligations. Contributor shall follow access, device, storage, credential, and incident procedures. Contributor shall not copy repositories or customer data to a personal account, public package, portfolio, or external service without written authorization.

Information is excluded to the extent Contributor can demonstrate it was lawfully known without restriction, becomes public without breach, is independently developed without using protected information, or is lawfully obtained without confidentiality obligations. Company bears the applicable legal burden of establishing protected status; the exclusion does not permit misuse of a secret simply because a related concept is public.

For a legally compelled disclosure, Contributor shall give lawful advance notice where permitted, reasonably cooperate in seeking protection, and disclose only what is required. Company shall reimburse authorized reasonable compliance expenses. Confidentiality continues for five years after engagement ends, except qualifying trade secrets remain protected while they lawfully remain trade secrets and personal/customer information remains protected as applicable while retained. No clause requires unlawful indefinite retention.

## 8. Protected reporting and legal rights

Nothing prohibits reporting suspected legal violations to a competent authority, cooperating with an investigation, discussing wages or working conditions where protected, exercising labor rights, obtaining confidential legal advice, or making another protected disclosure. Prior Company permission is not required for legally protected reporting. Contributor is not required to notify Company where doing so would violate law or defeat a protected right.

Under the U.S. Defend Trade Secrets Act, an individual is not criminally or civilly liable under federal or state trade-secret law for disclosure made in confidence to a federal, state, or local government official, directly or indirectly, or to an attorney, solely to report or investigate a suspected legal violation, or for disclosure in a complaint or other proceeding filed under seal. An individual bringing a retaliation action for reporting a suspected violation may disclose the trade secret to the individual's attorney and use it in court if the material is filed under seal and is not otherwise disclosed except by court order. This notice does not authorize unlawful access or disclosures outside the protected circumstances.

## 9. Records, disclosure, and further assurances

Contributor shall maintain reasonable contemporaneous creation records for Company Work Product, including repository commits, authorship, design history, relevant invention descriptions, dependencies, and assignments. The records must distinguish pre-existing and third-party material. Contributor shall promptly disclose Company Work Product to the designated Company representative and assist in applying for, perfecting, defending, and enforcing valid rights.

Company shall reimburse reasonable documented expenses and pay reasonable agreed compensation for material assistance after the engagement, except routine execution of already owed confirmatory instruments where lawful. Contributor shall not be required to make a false statement or transfer a protected excluded invention. Any power of attorney shall be limited to lawful ministerial perfection of already assigned rights, be separately executed where required, and not authorize Company to waive Contributor's protected rights or create a new substantive assignment without authority.

## 10. Conflicts, representations, and subcontractors

Contributor represents, after reasonable inquiry, that Contributor has authority to make the stated assignment, has disclosed known conflicting obligations, and will not knowingly provide infringing or misappropriated material. Contributor does not warrant ownership of disclosed Third-Party Materials beyond the applicable licenses. Contributor shall not enter a conflicting agreement that prevents performance or transfer of covered Company Work Product.

A contractor shall obtain Company's approval before delegating covered work and shall ensure approved subcontractors sign agreements that validly protect and assign their own contributions to the intended rights holder. Company may request copies or evidence of those assignments with appropriate privacy protection. Applicable employment classification, wage, and invention-compensation rules remain controlling.

## 11. Non-compete: jurisdiction-specific applicability only

No post-engagement non-compete applies by default. Such a restraint becomes part of this Agreement only through a separately signed Schedule C identifying a lawful jurisdiction, protected interest, prohibited activities, duration, territory, consideration, and any required notice. Company shall not ask a California worker to sign a prohibited employment restraint or attempt to enforce a void restraint through a different governing-law choice. Company shall not apply a prohibited post-termination restraint of trade to an Indian employee or consultant under section 27 of the Indian Contract Act.

Where a narrowly limited non-compete is lawful and necessary, its duration shall not exceed [LAWFUL_NONCOMPETE_DURATION], its territory shall be [LAWFUL_TERRITORY], and the restricted activities shall be only [SPECIFIC_COMPETING_ACTIVITIES] directly related to a demonstrable protectable interest. General industry employment, unrelated work, and use of general skill and experience shall not be prohibited. Required garden leave or other consideration is [REQUIRED_CONSIDERATION]. These placeholders must be completed following local legal review; “worldwide, perpetual, any competitor” is not an acceptable default.

The enforceable confidentiality and non-misappropriation duties apply independently. A court's refusal to enforce a non-compete does not expand those duties to prohibit lawful competition.

## 12. Non-solicitation and non-interference

During the engagement, Contributor shall not misuse Company Confidential Information to divert Company business or induce Company personnel to breach valid contractual duties. After the engagement, no employee/customer non-solicitation restraint applies unless Schedule C specifically adopts a lawful, proportionate covenant for the relevant jurisdiction.

Where validly adopted, for twelve months after termination Contributor shall not, through targeted use of Company Confidential Information, solicit an identified Company customer with whom Contributor had material business contact during the preceding twelve months for directly competing services, or deliberately induce a Company employee with whom Contributor worked materially to breach a valid obligation. The covenant does not prohibit general advertising, an unsolicited approach, lawful recruitment, protected labor activity, or business obtained without misuse of protected information. If the applicable law prohibits even this restraint, it does not apply. The separate prohibition on unlawful trade-secret misuse remains subject to applicable law.

## 13. Departure and return of property

At Company's request or on departure, Contributor shall return Company equipment, repositories, documents, credentials, and Company/Customer information, remove unauthorized copies from personal systems, and identify remaining protected data. Company shall arrange proportionate offboarding and shall not require disclosure of unrelated personal accounts or destruction of legally required personal employment/pay records. Approved legal-preservation copies shall be secured and used only for their lawful purpose.

Contributor shall certify completion after reasonable inquiry, identify an unavoidable backup or lawful hold, and cooperate with credential revocation. Company shall not retain access to Contributor's personal systems beyond lawful consent or process. Company shall preserve its creation/assignment records without retaining unnecessary unrelated personal data.

## 14. Remedies and continuing duties

A breach involving actual misuse of protected information or assigned rights may cause harm that damages alone cannot adequately remedy. Company may seek appropriate injunctive relief upon the showing required by applicable law; this clause does not eliminate a bond requirement, evidentiary burden, proportionality, or protected rights. No automatic punitive payment or unenforceable liquidated damages are imposed.

Contributor's indemnity, if any, for intentional misappropriation or knowing third-party-rights infringement is [NEGOTIATED_LAWFUL_CONTRIBUTOR_INDEMNITY_OR_NONE]. Company shall not impose unlimited liability on an employee contrary to employment law. Ordinary mistakes, management-approved component use, and Company-directed changes remain subject to applicable employment law and the engagement agreement.

Assignment of validly covered rights, applicable confidentiality, further assurances, protected-reporting safeguards, and lawful remedies survive termination. A lawful rescission, invalid assignment, statutory compensation, or non-waivable right is not extinguished by the word “irrevocable.”

## 15. Governing law and execution

This Agreement is governed by [GOVERNING_LAW], subject to mandatory employment, invention, copyright, privacy, and restraint-of-trade law applicable to Contributor. The competent forum is [LAWFUL_FORUM], without depriving Contributor of a mandatory local forum or legal protection. The engagement and IP agreements must use consistent lawful dispute terms.

This Agreement and its completed schedules contain the parties' agreement on this subject. Amendments require a signed writing. Severability preserves lawful provisions but does not require an illegal restraint to be rewritten or enforced. Company may assign validly acquired rights to a successor subject to continuing confidentiality and other obligations. Contributor has had a reasonable opportunity to obtain independent advice and does not waive mandatory rights by signing.

## Schedule A. Existing work and retrospective assignment

For each past contribution, identify: [PROJECT_OR_REPOSITORY], [COMMIT_RANGE_OR_ASSET_IDS], [CREATION_DATES], [DESCRIPTION_OF_WORK], [INDIVIDUAL_OR_JOINT_AUTHORS], [CURRENT_RIGHTS_OWNER], [PRIOR_CONTRACTS_OR_ASSIGNMENTS], [THIRD_PARTY_COMPONENTS], and [ASSIGNMENT_CONSIDERATION]. Contributor assigns only the rights Contributor actually owns or is authorized to transfer. Attach additional signed rows for multiple works. Unidentified unrelated past work is excluded.

The parties confirm the listed existing work is [COMPLETE_LIST_ATTACHED_OR_NONE]. Any missing joint-owner consent, prior-employer release, statutory formality, or open-source obligation must be resolved before Company represents exclusive ownership.

## Schedule B. Background Materials and statutory exclusions

For each item, identify: [ITEM_DESCRIPTION], [OWNER], [CREATION_DATE], [LICENSE_TERMS], [PROTECTED_EXCLUSION_IF_ANY], [PERMITTED_INCORPORATION], and [COMPANY_APPROVAL]. The parties confirm this schedule is [COMPLETE_LIST_ATTACHED_OR_NONE_DECLARED_AFTER_REVIEW]. Attach required employee-invention notices for [APPLICABLE_JURISDICTIONS].

## Schedule C. Restrictive covenants election

Election: [NO_POST_ENGAGEMENT_RESTRAINT_OR_SPECIFIC_REVIEWED_COVENANT]. Applicable jurisdiction: [JURISDICTION]. Protected interest and evidence: [PROTECTED_INTEREST]. Restricted activity, territory, and duration: [ACTIVITY_TERRITORY_DURATION]. Required notice and consideration: [NOTICE_AND_CONSIDERATION]. Non-solicitation election and identified scope: [LAWFUL_NON_SOLICITATION_OR_NONE]. Reviewing counsel/date: [COUNSEL_AND_REVIEW_DATE]. This schedule has no effect where the restraint is prohibited by mandatory law.

## Signatures

Company: [AUTHORIZED_SIGNATORY_NAME], [TITLE], signature [SIGNATURE], date [SIGNATURE_DATE].

Contributor: [CONTRIBUTOR_LEGAL_NAME], signature [SIGNATURE], date [SIGNATURE_DATE].

Separate local deed, witness, notarization, or entity execution requirements: [REQUIRED_EXECUTION_FORMALITIES_OR_NONE].


---

# Enterprise Data Processing Addendum

Effective date: [EFFECTIVE_DATE]

This Data Processing Addendum (“DPA”) forms part of the executed agreement for [PRODUCT_NAME] between [CUSTOMER_LEGAL_NAME], of [CUSTOMER_ADDRESS] (“Customer”), and [COMPANY_NAME], of [COMPANY_ADDRESS] (“Provider”). It applies to Personal Data processed by Provider on Customer's behalf. The parties shall complete the schedules and establish the described safeguards before processing in the contracted production service.

## 1. Definitions, roles, and precedence

“Applicable Data Protection Law” means privacy and data-protection law applicable to the relevant processing, including the GDPR and applicable EEA implementing law, UK GDPR and Data Protection Act where relevant, Swiss law where relevant, CCPA as amended by CPRA and implementing regulations where applicable, and India's Digital Personal Data Protection Act, 2023 and operative rules/notifications within their scope. A law is included only to the extent legally applicable; inclusion does not declare all provisions currently commenced.

“Customer Personal Data” means Personal Data in Customer Data processed on Customer's behalf. “Processing,” “Controller,” “Processor,” and “Personal Data Breach” have the meanings under the applicable law. “Subprocessor” means a third party Provider appoints to process Customer Personal Data for the contracted service. “Restricted Transfer” means a transfer requiring a legal safeguard under Applicable Data Protection Law.

Customer is Controller and Provider is Processor unless Customer acts as Processor for another controller, in which case Provider is its authorized Subprocessor. Customer shall obtain the authorizations necessary for that arrangement. Provider acts independently as Controller only for the specific account/billing or other independently determined processing disclosed in the Privacy Policy; it shall not relabel Customer telemetry as independent-controller information to escape this DPA.

Mandatory transfer clauses prevail for their regulated subject matter. This DPA otherwise prevails over inconsistent general terms concerning Customer Personal Data. It does not reduce a person's mandatory rights, a regulator's authority, or the responsibilities the law assigns to each party.

## 2. Subject matter, instructions, and purpose limitation

Provider shall process Customer Personal Data only to supply, secure, support, maintain, and terminate the contracted service on Customer's documented instructions in the agreement, configuration, and lawful written directions. Schedule 1 states the subject matter, duration, nature, purposes, data categories, and data subjects. Customer-directed remote access and integration destinations require explicit authorization and scope.

Provider shall not process for an incompatible purpose, sell or share Customer Personal Data for advertising, combine it for prohibited cross-customer profiling, or train a general-purpose model on it without a separate explicit lawful agreement. Permitted service security and deidentified capacity planning shall remain within applicable processor/service-provider restrictions. Pseudonymization alone does not remove data from this DPA.

If law requires processing outside Customer instructions, Provider shall inform Customer before that processing unless prohibited for legally recognized reasons, limit processing to what the law requires, and maintain an appropriate record. Provider shall promptly inform Customer if it considers an instruction to infringe Applicable Data Protection Law and may suspend that instruction while the parties resolve it; Provider shall not use a general compliance objection to withhold unrelated purchased functionality.

## 3. Customer responsibilities

Customer shall determine lawful purposes and bases, provide required notices, obtain applicable authorizations/consents, define appropriate collection and retention, and avoid unnecessary sensitive information. Customer shall configure least-privilege access and approved destinations and shall inform Provider of processing requiring additional safeguards. Customer shall not direct Provider to conduct unauthorized monitoring or unlawful surveillance.

These duties do not relieve Provider of its independent security, processor, notification, or assistance obligations. If Customer is itself a Processor, it shall transmit the upstream controller's relevant instructions and obligations and shall not authorize a use inconsistent with them.

## 4. Confidentiality and personnel

Provider shall ensure persons authorized to process Customer Personal Data are bound by appropriate confidentiality obligations or a statutory duty and receive relevant security/privacy training. Access shall be limited to a legitimate role, approved purpose, and appropriate period. Provider shall review and revoke access on departure or role change, protect support access, and maintain proportionate records.

Provider shall not permit an individual to access unrelated tenants or use customer logs for personal experimentation. Support evidence shall be minimized and redacted where possible. Confidentiality survives access termination for as long as information lawfully remains held and protected.

## 5. Technical and organizational measures

Provider shall implement and maintain the measures in Schedule 2 appropriate to the risk, categories, volume, purposes, and processing context. The measures shall address confidentiality, integrity, availability, resilience, access control, recovery, and regular assessment. Provider shall not materially diminish the agreed overall security posture during the term without Customer's written agreement or an equivalent improved measure.

A described measure is a binding production obligation only after the parties verify it is deployed in the contracted environment. The current development baseline does not itself establish independent production approval, externally attested audit integrity, regional failover, or complete historical deletion. Material gaps must be disclosed and remediated before accepting production processing that depends on those safeguards.

## 6. Subprocessor appointment

Customer grants general written authorization for the actual Subprocessors listed in Schedule 3. Provider shall give at least thirty days' advance written notice of a proposed addition or material replacement, including legal entity, function, categories, locations, and transfer safeguards. A shorter notice period requires Customer's explicit agreement, not a unilateral emergency label.

Customer may object within that period on reasonable documented data-protection or security grounds. The parties shall attempt a proportionate solution, such as an alternative supplier or affected-feature arrangement. If no reasonable solution is available before the proposed processing, Customer may terminate the affected service without penalty and receive a prorated refund of prepaid unused affected-service fees. Provider shall not begin the disputed new processing merely because an objection is inconvenient.

Provider shall impose written obligations on each Subprocessor substantially equivalent for the relevant processing, including security, confidentiality, instruction limits, assistance, breach reporting, transfer safeguards, and return/deletion. Provider remains responsible for the Subprocessor's performance of those obligations to the extent required by law and the agreement. Customer-selected independent recipients are not automatically Provider Subprocessors, but disclosure still requires a valid instruction and appropriate security.

## 7. Data-subject requests and assistance

Taking account of the nature of processing, Provider shall assist Customer through appropriate technical and organizational means with access, correction, deletion, restriction, portability, objection, consent withdrawal, and other applicable rights. Provider shall promptly forward a request concerning Customer-controlled data and shall not respond substantively without Customer instruction unless law requires it. Provider may acknowledge receipt and identify the responsible controller without disclosing protected information.

Provider shall provide available relevant records and carry out authorized corrections, restrictions, export, and deletion within the timeframe needed for Customer's legal response. Customer and Provider shall agree a practical completion deadline for complex work; it must not exceed the applicable legal deadline. Ordinary assistance inherent in the contracted controls is included. Extraordinary custom work may incur pre-agreed reasonable charges, but Provider shall not condition legally necessary assistance following its own breach on payment of a new fee.

Provider shall assist with impact assessments, regulator consultation, security compliance, breach response, processing records, and audits to the extent the relevant information is available to it. Customer remains responsible for its own regulatory decisions and notices except duties assigned independently to Provider by law.

## 8. Personal Data Breach notification

Provider shall notify Customer without undue delay after becoming aware of a Personal Data Breach affecting Customer Personal Data and, as a proposed contractual target, within twenty-four hours of that awareness. This contractual target is not a statement that all laws impose a twenty-four-hour deadline. An initial notice may be preliminary and shall not be delayed solely because all details are not yet known.

The notice shall provide, as known, the nature of the breach, affected systems/categories, approximate data-subject and record counts, occurrence/discovery times, likely consequences, containment and remediation, recommended Customer actions, and incident contact. Provider shall supplement information promptly, cooperate in reasonable investigation, preserve necessary evidence securely, and keep Customer informed of material developments. Notice does not require Provider to speculate, disclose other customers' data, or waive legitimate legal privilege, but privilege must not be used to withhold facts needed for Customer's legal obligations.

Provider shall not notify affected individuals or identify Customer publicly concerning the breach without Customer coordination unless required by law. It shall advise Customer of such a requirement where permitted. Each party shall meet its own statutory notification duty, including GDPR controller timeframes where applicable and the operative Indian or other local requirements. The parties shall allocate remedial costs under the service agreement and law without contracting away statutory accountability.

## 9. International transfers and government access

Provider shall process in the hosting and access locations identified in Schedules 1 and 3. A change that creates a new Restricted Transfer requires the applicable safeguard and notice before processing. Residency commitments address both storage and authorized access as expressly specified; Provider shall not assume that a storage-region setting eliminates remote-access transfer obligations.

For EEA Restricted Transfers, the parties incorporate the unmodified appropriate clauses of Commission Implementing Decision (EU) 2021/914. Module Two applies where Customer is Controller and Provider is Processor; Module Three applies where Customer is Processor and Provider is Subprocessor. The parties shall select the actual module in Schedule 4, complete the annexes, and obtain a verified copy of the official mandatory text before execution. This DPA does not purport to replace, paraphrase, or amend that mandatory text.

For applicable UK transfers, the parties shall complete the current approved UK Addendum or other valid mechanism identified in Schedule 4. For Swiss transfers, the applicable Swiss-law modifications and competent authority shall be completed. The parties shall conduct and document required transfer assessments and supplementary safeguards. Indian transfers shall comply with operative national restrictions, sectoral requirements, and other applicable law; GDPR clauses alone do not establish Indian compliance.

Provider shall evaluate government demands, verify their authority, disclose only what is legally necessary, notify Customer where legally permitted, and challenge unlawful or disproportionate demands where appropriate. Provider shall not voluntarily grant a general backdoor or unrestricted access to Customer Personal Data. If a transfer safeguard can no longer be honored, the parties shall suspend or lawfully restructure the affected transfer and provide the applicable termination/export remedy.

## 10. Return, deletion, retention, and backups

At Customer's choice, following termination Provider shall return Customer Personal Data through the supported export or agreed assistance within thirty days, or delete it, subject to applicable legal preservation. Provider shall delete residual active copies within thirty days after the authorized return/deletion instruction unless a shorter legal deadline applies. Routine backups shall expire within the agreed thirty-five-day cycle and shall not be accessed for ordinary processing after deletion.

Provider shall retain only the necessary data where law requires preservation, identify the legal basis, categories, access restrictions, and duration, and delete when that basis ends. A security/audit label is not an unlimited retention exception. On restoration, Provider shall reapply erasure and retention instructions before ordinary service processing resumes. At Customer's reasonable request, Provider shall certify the completed deletion and identify any lawful residual backup or hold.

The current implementation does not yet provide finite deletion for every audit, incident, run, and ETL-history category. Provider shall implement and test the required mechanism, including correlated evidence and backups, before undertaking these hosted production commitments. Customer shall not be asked to accept a false deletion certification. Customer-hosted deletion is performed by Customer unless the managed-service scope expressly assigns it to Provider.

## 11. Compliance information and audits

Provider shall make available information reasonably necessary to demonstrate compliance with this DPA and shall allow and contribute to proportionate audits and inspections by Customer or an authorized independent auditor. Where an applicable independent report exists, it may provide initial assurance but does not eliminate audit rights required by law. Provider shall not claim a SOC 2 report or other certification that has not been obtained for the relevant scope.

Routine audits shall be coordinated on reasonable notice, ordinarily no more than once per twelve months unless a breach, credible noncompliance concern, material change, or regulator requirement warrants more. Audits shall protect other customers, security secrets, and system availability. Reasonable confidentiality and non-invasive methods may apply, but must not make the audit right ineffective. Penetration tests require an agreed scope and authorization. Provider shall address substantiated findings with documented priorities and deadlines.

Routine extraordinary audit costs may be reasonably allocated in advance. Provider bears its own remediation costs and reasonable additional audit costs attributable to a substantiated material breach of this DPA. A regulator's lawful inspection is not subject to a contractual annual limit.

## 12. California service-provider and contractor conditions

For information processed as a service provider or contractor under the CCPA/CPRA, Provider shall process only for the specified contracted business purposes and permitted statutory purposes. Provider shall not sell or share the information; retain, use, or disclose it outside the specified business purposes or direct business relationship except as law permits; or combine it with information from other persons or Provider's own consumer interactions except where permitted under the applicable rules.

Provider shall comply with the applicable privacy obligations, provide the required level of protection, and notify Customer if it can no longer meet them. Customer may take reasonable and appropriate steps to ensure compliant use and to stop and remediate unauthorized processing. Provider certifies that it understands these restrictions and will comply. Downstream contracts shall impose the required equivalent restrictions. Customer remains responsible for determining whether its own processing is subject to the CCPA/CPRA and for providing appropriate consumer notices and rights responses.

## 13. India and additional local-law conditions

Where Customer is the Data Fiduciary and Provider its processor under the operative Indian framework, Provider shall process under the valid contract and instructions, maintain appropriate safeguards, cooperate with applicable rights/grievance/breach processes, and facilitate lawful erasure and records. The responsible Data Fiduciary remains accountable for duties assigned to it by law. Provider shall not rely on the DPA to create a consent basis Customer has not obtained.

Before covered processing involving children, a Significant Data Fiduciary designation, sectoral localization, or another enhanced duty, the parties shall approve the specific arrangement and necessary safeguards. Additional appointment, audit, impact-assessment, language, or notification obligations shall be implemented where legally applicable. The actual commencement and implementing-rule status shall be verified at execution and periodically thereafter.

## 14. Duration, liability, and general provisions

This DPA applies while Provider processes Customer Personal Data and survives termination for retained data. Liability is governed by the executed service agreement, except a limitation cannot override mandatory transfer clauses, non-waivable individual rights, or regulator powers. An individual's statutory compensation claim is not reduced merely because the commercial parties agreed a cap between themselves.

The parties shall document material processing changes and agree necessary updates before incompatible new processing begins. No public policy update silently expands this DPA. If an obligation becomes unlawful, the parties shall adopt a lawful equivalent or suspend the affected processing. Remaining valid obligations continue. Disputes follow the agreement subject to mandatory transfer and local-law provisions.

## Schedule 1. Processing description

Customer/data exporter: [CUSTOMER_LEGAL_NAME], [CUSTOMER_ADDRESS], privacy contact [CUSTOMER_PRIVACY_CONTACT].

Provider/data importer: [COMPANY_NAME], [COMPANY_ADDRESS], privacy contact [PRIVACY_CONTACT_EMAIL].

Subject matter: providing the purchased [PRODUCT_NAME] hosted monitoring and operational investigation service described in [ORDER_FORM_ID].

Nature and purposes: authorized collection/receipt, organization-scoped storage, retrieval, rule evaluation, correlation, incident investigation, reporting, permitted support, security administration, and authorized export/return/deletion. No unrelated advertising or general-purpose model training is authorized.

Data subjects: Customer's authorized workforce, business contacts, and individuals whose identifiers occur in lawfully configured technical logs or applications, as specifically identified in [CUSTOMER_DATA_SUBJECT_REGISTER].

Categories: account/role references, resource and network identifiers including IP addresses, observation timestamps, measurements, supported logs/job details, investigation notes, and available correlation identifiers. Exclude raw secrets and unsupported regulated categories. Approved exceptions, if any, are [APPROVED_SPECIAL_CATEGORY_PROCESSING_OR_NONE].

Duration and frequency: recurring configured collection and service processing during the paid term, followed by the return/deletion and lawful residual periods. Purchased collection/capacity profile is [COLLECTION_AND_CAPACITY_PROFILE].

Locations and residency: [HOSTING_REGION], support/access countries [AUTHORIZED_ACCESS_COUNTRIES], and actual Subprocessor locations in Schedule 3.

Retention: raw metric/log periods [PURCHASED_METRIC_RETENTION] and [PURCHASED_LOG_RETENTION]; approved incident/history/audit period [HISTORY_AUDIT_RETENTION]; backup cycle thirty-five days unless lawfully agreed otherwise. Correlated evidence and legal holds are restricted, reviewed, and deleted under the approved schedule rather than retained automatically forever.

## Schedule 2. Security measures and acceptance record

Identity and authorization: individual accounts; separate worker credentials; protected password/token digests; authorized role and organization scopes; session revocation; bounded credential lifetime; privileged access review and secure secret handling. Enterprise identity/MFA requirements are [CONTRACTED_IDENTITY_REQUIREMENTS] and must not be claimed unless deployed.

Transport and deployment: certificate-validated TLS at the contracted boundaries; approved trust configuration; restricted ingress; explicit trusted proxies; verified frontend security headers and CSP; hardened supported runtime; documented vulnerability and dependency handling. Encryption at rest and key management are [DEPLOYED_STORAGE_ENCRYPTION_AND_KEY_CONTROLS], verified against the actual database/storage platform.

Collection and egress: approved target-owner authorization, host/CIDR allowlists, pinned approved HTTPS destinations, network-layer egress enforcement, blocked metadata/unrelated destinations, no arbitrary remote shell, secret references, bounded payloads, leased assignments, timestamp/replay validation, and distinction between worker liveness and target health.

Audit and operations: scoped mutation history, restricted runtime/maintenance/migration roles, append-only protections, independent archival/attestation where contracted, redacted diagnostics, change review, threat assessment, incident response, personnel access review, and adequate investigation records. Required external attestation control is [AUDIT_ARCHIVE_ATTESTATION_CONTROL]; database-owner capability is not equivalent to immutable external assurance.

Continuity and deletion: populated backup/restore tests, verified checksum/integrity, separate restore target, agreed RTO [CONTRACTED_RTO] and RPO [CONTRACTED_RPO], tested restart/reconnect and required failover, scheduled bounded retention, approved historical deletion, lawful holds, backup expiry, and erasure reapplication on restore. Small fixture timings do not establish contracted production objectives.

Production acceptance record: [SECURITY_REVIEW_ID], [RETENTION_DELETION_TEST_ID], [RESTORE_LOAD_FAILOVER_TEST_IDS], [DEPLOYMENT_REGION_KEY_VERIFICATION], [INDEPENDENT_REVIEWER], and [ACCEPTANCE_DATE]. No absent field is deemed completed by signing a development checklist.

## Schedule 3. Actual Subprocessor register

Each entry shall include [LEGAL_ENTITY], [ADDRESS], [FUNCTION], [DATA_CATEGORIES], [STORAGE_AND_ACCESS_COUNTRIES], [TRANSFER_MECHANISM], [SECURITY_ASSURANCE_REFERENCE], and [NOTICE_CONTACT]. Attach the complete actual register or state “No Subprocessors” only after verifying that no appointed hosting, support, backup, or other provider processes Customer Personal Data. A cloud adapter in the code is not evidence of an appointed Subprocessor.

Notice URL: [SUBPROCESSOR_REGISTER_URL]. Notice recipient: [CUSTOMER_SUBPROCESSOR_NOTICE_EMAIL]. Objection and alternative-process contacts: [PARTY_CONTACTS].

## Schedule 4. Transfer mechanism selection

Restricted transfer election: [NO_RESTRICTED_TRANSFER_OR_IDENTIFIED_TRANSFER]. EEA module: [MODULE_TWO_OR_MODULE_THREE_AS_APPLICABLE]. Clause 7 docking election: [DOCKING_ELECTION]. Clause 9 authorization: general authorization with thirty days' notice. Optional Clause 11 election: [OPTIONAL_REDRESS_ELECTION]. Clause 17 law: [QUALIFYING_EU_MEMBER_STATE_LAW]. Clause 18 courts: [CORRESPONDING_EU_MEMBER_STATE_COURTS]. Competent supervisory authority: [ACTUAL_COMPETENT_AUTHORITY].

The parties and signatures are those below; Schedules 1 through 3 supply the actual annex information and shall be adapted to the selected module without changing mandatory clauses. UK mechanism and tables: [COMPLETED_UK_ADDENDUM_OR_OTHER_APPROVED_MECHANISM_OR_NOT_APPLICABLE]. Swiss adaptations: [COMPLETED_SWISS_ADAPTATIONS_OR_NOT_APPLICABLE]. Transfer assessment and supplementary measures: [TRANSFER_ASSESSMENT_ID_AND_CONTROLS]. Mandatory official clause texts shall be obtained and checked before execution; this schedule alone is not a completed international-transfer instrument.

## Signatures

For [COMPANY_NAME]: [AUTHORIZED_SIGNATORY_NAME], [TITLE], signature [SIGNATURE], date [SIGNATURE_DATE].

For [CUSTOMER_LEGAL_NAME]: [AUTHORIZED_SIGNATORY_NAME], [TITLE], signature [SIGNATURE], date [SIGNATURE_DATE].
