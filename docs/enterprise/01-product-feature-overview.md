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
