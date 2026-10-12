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
