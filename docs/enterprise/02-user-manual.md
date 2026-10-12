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
