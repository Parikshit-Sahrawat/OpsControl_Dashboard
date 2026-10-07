# OpsControl Dashboard

OpsControl Dashboard is an enterprise operations monitoring platform being designed to give NOC, SLM, support, and engineering teams a single operational view of production ETL jobs, VMs, applications, APIs, incidents, alerts, and operational history.

> **Documentation principle:** This README is the living project knowledge base. Important architecture, requirements, operating rules, configuration decisions, implementation steps, and validated design decisions should be documented here as the project evolves.

---

## 1. Project Goals

OpsControl is intended to answer:

> **"What needs my attention right now?"**

The platform should help operators:

- See current production health quickly.
- Detect failed, long-running, and missing ETL executions.
- Investigate Pentaho failures without jumping between multiple tools.
- Correlate ETL failures with VM, application, database, API, and dependency health.
- Track incidents and operator investigation history.
- Monitor VM resources, services, processes, and applications.
- Monitor APIs, response time, availability, authentication, SSL, and certificates.
- Generate operational reports and ETL success/failure reports.
- Integrate with Email, PagerDuty, and ServiceNow.
- Maintain one year of history initially.
- Provide Resource Management and role-based access for multiple departments/teams.

---

## 2. Current Product Scope

### Top navigation

1. Overview
2. ETL Jobs
3. VM Health
4. APIs
5. Incidents
6. Reports
7. Resource Management

### Home / Overview

The Overview page is intentionally action-oriented.

It should show:

- ETL Jobs KPI
- VM Health KPI
- APIs & Services KPI
- Active Incidents KPI
- Recent ETL Jobs
- Recent VM Issues
- Recent API Issues
- Active Incidents

It should **not** become a historical analytics page.

Excluded from Overview:

- Long-term trends
- Historical graphs
- System Health/integration-status panel
- SFTP/S3 section
- Settings/configuration
- Resolved historical ETL noise

Historical analysis belongs in **Reports**.

### Refresh

- Target operational refresh: **5 seconds**
- UI should clearly indicate automatic refresh state.

### Status colors

- Green = Healthy / Success
- Yellow = Warning / Long Running / At Risk
- Red = Critical / Failed
- Blue = Running
- Gray = Unknown / Not Started

---

# 3. Resource Hierarchy

The formal resource hierarchy is:

```
Organization / Customer
        |
        +-- VM / Server
        |     |
        |     +-- Applications
        |     |     +-- Apache
        |     |     +-- Tomcat
        |     |     +-- IEngine
        |     |     +-- Pentaho
        |     |
        |     +-- ETL Job Orders
        |            |
        |            +-- Job Order Name
        |            |      +-- Schedule
        |            |      +-- SLA
        |            |      +-- Monitoring rules
        |            |
        |            +-- Job Order History
        |                   +-- Execution 001
        |                   +-- Execution 002
        |                   +-- Execution 003
        |
        +-- Other VMs...
```

### Organization / Customer

A Customer represents an organization.

### VM / Server

A VM represents an individual machine used to run applications and workloads.

### Application

Applications/services/processes running on a VM can be monitored independently.

Example:

```
HERO-PRDAPP001
├── Windows                 ✓
├── CPU                     42%
├── RAM                     68%
├── C: Drive                71%
├── D: Drive                94%  WARNING
├── Apache                  ✓
├── Tomcat                  ✓
├── IEngine.exe             ✓
└── Pentaho                 ✓
```

**VM restart actions are intentionally excluded from OpsControl.**

---

# 4. ETL Monitoring Scope

Regular automated ETL monitoring is currently focused on **PROD only**.

QA/Test/non-production environments are not part of the regular monitoring scope. If required, those environments may be handled manually or added as a future scope.

Each monitored ETL workload is a **Job Order**.

---

# 5. Job Order vs Job Order History

This distinction is fundamental to the backend design.

## Job Order

A Job Order represents:

> **What should run?**

A Job Order is identified by:

```
Organization + VM + Job Order Name
```

Internally it has a unique `job_order_id`.

Example:

```
job_order_id: JO-000127
Organization: ABC Corporation
VM: HERO-PRDAPP001
Job Order Name: JC_Pricing_Daily
Environment: PROD
```

The same human-readable Job Order Name may exist for another organization/VM without conflict because the resource context identifies the Job Order.

## Job Order History

A Job Order History represents:

> **What actually happened during one execution?**

Every execution gets its own history record.

Example:

```
JC_Pricing_Daily
├── 08-Oct 08:00 -> FAILED
├── 08-Oct 09:30 -> SUCCESS (MANUAL)
└── 09-Oct 08:00 -> SUCCESS
```

Scheduled and manual Pentaho executions are both captured.

Execution type:

- `SCHEDULED`
- `MANUAL`

A manual execution is not automatically considered a recovery. If required, a future explicit relationship can associate it with an earlier failed execution.

---

# 6. ETL Scheduling

Both simple and advanced scheduling are required.

## Simple schedules

- Hourly
- Daily
- Weekly
- Monthly
- Quarterly

Examples:

```
Hourly   -> every 1 hour
Daily    -> every day at 08:00
Weekly   -> Monday at 08:00
Monthly  -> 1st day at 08:00
Quarterly -> first day of quarter at 08:00
```

## Advanced schedules

The backend must be extensible for:

- Every N hours
- Monday-Friday
- Specific days of month
- Multiple days/times
- Last working day
- First Monday of month
- Multiple execution windows
- Other future scheduling rules

Do not hard-code the database around only five frequency strings.

## Schedule vs expected execution

These are different concepts.

**Schedule** answers:

> When should the workload run?

**Expected execution window** answers:

> When should OpsControl expect to see an execution?

Example:

```
Schedule:
Daily at 08:00

Expected window:
08:00-08:15

No-run grace:
15 minutes
```

Only after the configured grace period should the monitor classify the execution as `NO_RUN`.

---

# 7. Runtime and SLA

Expected runtime and SLA are separate.

Example:

```
Expected runtime: 20 minutes
SLA:              30 minutes
```

Operational states:

```
08:00  Job starts
08:20  Expected runtime exceeded
       -> LONG_RUNNING / At Risk

08:30  SLA exceeded
       -> SLA BREACH
```

This allows early warning before an actual SLA breach.

---

# 8. ETL Job States

Initial normalized states:

- `SUCCESS`
- `FAILED`
- `RUNNING`
- `LONG_RUNNING`
- `NO_RUN`
- `NO_RESPONSE`

Additional UI-level step states:

- `SUCCESS`
- `FAILED`
- `RUNNING`
- `NOT_STARTED`
- `SKIPPED`
- `UNKNOWN`

---

# 9. Job Details Drawer

The Job Details drawer is being designed as the operational contract for the future backend API and database.

A failed execution should provide enough information for an operator to understand:

1. What failed?
2. Where did it fail?
3. What exactly did Pentaho report?
4. What does OpsControl know about the surrounding infrastructure/dependencies?
5. Has the same problem happened before?
6. What incidents/alerts were generated?
7. What is the current investigation state?
8. What has the operator documented?

## Drawer sections

### 9.1 Execution Summary

Expected information:

- Job Order Name
- Job Order History / Execution ID
- Organization
- VM/server
- Environment
- Pentaho instance
- Execution type
- Status
- Start time
- End time / failure time
- Detected time
- Duration
- Expected runtime
- SLA
- SLA status
- Current incident reference
- Last update time

### 9.2 Failure Diagnosis

Failure diagnosis deliberately separates **source facts** from **OpsControl analysis**.

#### Pentaho/source facts

These should represent what the source actually reported:

- Failed step
- Step type
- Error code
- Error message
- Exception
- Pentaho status/result
- Source timestamps
- Log location
- Other available raw execution metadata

#### OpsControl diagnosis

These are calculated, correlated, or manually confirmed by OpsControl:

- Failure category
- Suspected cause
- Confidence
- Related resource
- Related event
- Correlated incident
- Root cause
- Root cause status
- Analysis timestamp

**Important:** Suspected Cause and Confirmed Root Cause are different fields.

Example:

```
Pentaho:
Connection timeout

OpsControl:
Category: Database
Suspected cause: ORACLE-PROD-01 unavailable
Confidence: High

Root cause:
Pending investigation
```

Later:

```
Root cause:
Database listener failure

Confirmed by:
DB Team

Confirmed at:
08:32 IST
```

Do not overwrite historical diagnostic evidence.

### 9.3 Execution Timeline

The drawer should show an event timeline such as:

```
08:00:01  Job started
08:01:12  Extract started
08:04:21  Transformation started
08:05:48  Database connection error
08:05:49  Job failed
08:05:55  OpsControl detected failure
08:06:01  PagerDuty notification
08:06:05  ServiceNow incident created
```

### 9.4 Step-level execution

The initial implementation should capture **full step-level execution information when Pentaho provides it**.

Example:

```
Extract Customer Data       SUCCESS
Transform Pricing           SUCCESS
Update Customer Database    FAILED
Generate Output             NOT_STARTED
```

Available fields may include:

- Step name
- Step type
- Step status
- Start time
- End time
- Duration
- Records read
- Records written
- Records rejected
- Error code
- Error message
- Step-specific log information

All fields must be optional when the selected Pentaho integration/source cannot provide them.

### 9.5 Logs

Potential capabilities:

- Execution log
- Error log
- Log location
- Relevant error excerpt
- Search/filter
- Open log location
- Future full-log access/download

Raw logs remain troubleshooting evidence. Structured events should be used for operational state.

### 9.6 Related Health / Correlation

The drawer should eventually correlate ETL execution with:

- VM health
- CPU
- RAM
- Disk
- Services
- Processes/applications
- Database health
- APIs
- SFTP/S3 availability where relevant
- Related ETL jobs
- Active incidents

Example:

```
Job failed
    |
    +-- Database connection timeout
    |
    +-- ORACLE-PROD-01 unavailable
    |
    +-- VM CPU 91%
    +-- Disk 72%
    +-- Network healthy
```

Correlation must distinguish observed facts from inferred causes.

### 9.7 Alert & Incident History — Confirmed Scope

The Job Details drawer will show **important operational events only**.

The drawer is intentionally not a complete integration audit log. Its purpose is to answer quickly:

- Was an alert triggered?
- Was it delivered successfully?
- Was an incident created?
- Was it acknowledged?
- Who is handling it?
- What is the current incident state?

Example:

```
ALERT & INCIDENT HISTORY

08:05:55  Failure detected
          Severity: CRITICAL

08:06:01  PagerDuty
          TRIGGERED
          Incident: PD-12345

08:06:05  ServiceNow
          INCIDENT CREATED
          INC0012345

08:06:07  Email
          SENT
          Recipients: SLM Operations

08:08:14  PagerDuty
          ACKNOWLEDGED
          By: Operator A
```

The drawer should prioritize operational milestones such as:

- Failure/alert detected
- PagerDuty triggered
- ServiceNow incident created
- Email notification sent
- PagerDuty acknowledgement
- ServiceNow assignment/update
- Incident resolved/closed

Repeated delivery attempts, retries, webhook details, payloads, API responses, and other low-level integration events should **not** clutter the Job Details drawer.

A separate future integration/audit view may expose the complete technical event history when troubleshooting the integration itself.

The drawer should retain a link/reference to the related PagerDuty and ServiceNow records where available.

### 9.8 Investigation

Operators need a persistent investigation record.

Minimum concepts:

- Investigation status
- Operator
- Timestamp
- Notes
- State transitions
- Optional evidence/reference

### 9.9 Recent History — Confirmed Scope

The Recent History section will initially show **previous executions of the same Job Order only**.

Scope:

```
Current execution
      |
      +-- Same Job Order
      |     +-- Previous execution
      |     +-- Previous execution
      |     +-- Previous execution
      |
      +-- Other Job Orders -> excluded from this initial view
```

For example, if the current execution is:

```
Organization: ABC Corporation
VM: HERO-PRDAPP001
Job Order: JC_Pricing_Daily
```

Recent History will show only earlier executions belonging to that same `job_order_id`.

It should include enough information to compare executions, such as:

- Execution date/time
- Execution type
- Status
- Duration
- Failed step, when applicable
- Failure category, when available
- SLA status
- Incident reference, when applicable

Example:

```
RECENT HISTORY

08-Oct 08:05  FAILED   Database timeout       INC0012345
07-Oct 08:04  FAILED   Database timeout       INC0012291
06-Oct 08:00  SUCCESS  18m                    -
05-Oct 08:00  SUCCESS  19m                    -
04-Oct 08:00  SUCCESS  21m                    -
```

This is intentionally **not** a cross-Job-Order diagnostic view.

Future correlation can add a separate capability for:

- Same failure category across the same Job Order
- Related failures across the same VM
- Related failures across the same organization/customer
- Cross-resource dependency correlation

That future capability should not be mixed into the initial Recent History contract.

---

# 10. Investigation Lifecycle

Confirmed lifecycle:

```
NEW
  |
  v
ACKNOWLEDGED
  |
  v
INVESTIGATING
  |
  v
ROOT_CAUSE_IDENTIFIED
  |
  v
RECOVERY_IN_PROGRESS
  |
  v
MONITORING
  |
  v
RESOLVED
```

Every transition should record:

- Operator
- Timestamp
- Previous state
- New state
- Optional comment/reason

### Execution status and investigation status are separate

Example:

```
Job Order History:
FAILED

Investigation:
MONITORING
```

A later successful execution does not automatically mean the investigation is resolved.

---

# 11. Operator Action Boundary

OpsControl is initially a **monitoring, investigation, and incident-management platform**, not a Pentaho execution controller.

## Supported / planned operator actions

- Acknowledge alert
- Change investigation state
- Add investigation note
- View/copy error
- View logs
- Open related incident
- Create ServiceNow incident
- Open PagerDuty incident
- View correlated health information

## Explicitly excluded

- Retry Job
- Start Job
- Stop/Cancel Job
- Restart VM
- Modify Pentaho production configuration
- Modify production job definitions

Recovery is performed manually by the appropriate operator/team using the existing approved Pentaho operational procedure.

---

# 12. SFTP / S3 Monitoring

SFTP/S3 monitoring is not displayed on the Overview page.

Where implemented, checks should focus on:

- Expected file
- Expected arrival time
- Actual arrival time
- File size
- File age

**Content validation is currently excluded.**

---

# 13. API Monitoring

API monitoring requirements include:

- HTTP status
- Response time
- Availability
- Response body
- Authentication
- SSL
- Certificate expiry
- Request/response logging

The Overview page should surface only current/recent API issues; detailed historical analysis belongs in Reports.

---

# 14. VM Monitoring

VM monitoring should include:

- Availability
- CPU
- RAM
- Disk by drive
- Services
- Processes
- Applications
- Event/log information where useful

Example:

```
HERO-PRDAPP001
├── Windows           HEALTHY
├── CPU               42%
├── RAM               68%
├── C:                71%
├── D:                94% WARNING
├── Apache             HEALTHY
├── Tomcat             HEALTHY
├── IEngine.exe        HEALTHY
└── Pentaho            HEALTHY
```

---

# 15. Alerts and Integrations

Initial alerting channels:

- Email
- PagerDuty

Incident integration:

- ServiceNow

The platform should automatically create an incident according to the configured alert policy.

The system must retain integration event/status history so an operator can see whether an alert was successfully delivered.

---

# 16. Reports

Reports are separate from the action-first Overview page.

Initial retention target: **1 year**.

### ETL reports

- Job success/failure trends
- SLA compliance
- Runtime trends
- Failure analysis
- Execution history
- Recurring failures
- Long-running jobs
- No-run events

### VM reports

- CPU trends
- RAM trends
- Disk trends
- Service/application health

### API reports

- Availability
- Response time
- High latency
- SSL/certificate status

### Incident reports

- Incident trends
- MTTA
- MTTR
- Recurring issues
- Root-cause analysis

Reports should support email delivery.

---

# 17. Daily ETL Report

The platform should eventually generate a standardized report containing:

- Total jobs
- Successful jobs
- Failed jobs
- Long-running jobs
- No-run jobs
- Success rate
- SLA compliance
- Failed job details
- Incident references

The source should be structured Job Order History data rather than manually compiled status.

---

# 18. Resource Management

Resource Management will eventually provide controlled configuration for:

- Organizations/customers
- VMs
- Applications
- Pentaho instances
- Job Orders
- Schedules
- Monitoring rules
- Alert policies
- API resources
- Dependencies
- Access permissions
- Roles
- Integration configuration

Every resource should have documented onboarding/configuration steps.

The goal is that a future developer or support engineer can configure a new monitored resource without relying on undocumented tribal knowledge.

---

# 19. Roles and Permissions

Multiple departments/teams will use the platform.

Potential roles:

- Admin
- Operator
- Viewer
- Support
- Manager

RBAC is planned.

Actions that can change investigation state, configuration, alerting, or access must eventually be permission-controlled and audited.

---

# 20. Proposed Architecture

Initial logical architecture:

```
React UI
   |
   +-- Overview
   +-- ETL Jobs
   +-- VM Health
   +-- APIs
   +-- Incidents
   +-- Reports
   +-- Resource Management
          |
          v
      FastAPI API
          |
     +----+----+
     |         |
     v         v
 PostgreSQL  Prometheus
```

Longer-term:

```
Users
  |
React Dashboard
  |
FastAPI
  |
+-------------------------------+
| PostgreSQL                    |
| Prometheus                    |
| Redis                         |
| Monitoring / Alert Engines    |
+-------------------------------+
  |
+-------------------------------+
| Pentaho                       |
| SFTP / S3                     |
| VM / OS / Application Agents  |
| APIs                          |
+-------------------------------+
  |
+-------------------------------+
| Email | PagerDuty | ServiceNow|
+-------------------------------+
```

The exact storage/observability stack remains an implementation decision and should be validated during the POC.

---

# 21. Backend/Data-Model Principles

The UI requirements are intentionally being finalized before the production backend schema.

Important principles already confirmed:

1. Organization is a first-class resource.
2. VM is a first-class resource.
3. Job Order is a first-class resource.
4. Job Order History is an execution/event record.
5. Organization + VM + Job Order Name identifies a Job Order configuration.
6. A Job Order has many Job Order History records.
7. Scheduled and manual executions are both captured.
8. Step-level execution data is supported where available.
9. Raw Pentaho facts are separated from OpsControl analysis.
10. Suspected cause is separate from confirmed root cause.
11. Execution status is separate from investigation status.
12. Investigation state transitions are auditable.
13. Schedule configuration is structured and extensible.
14. Expected runtime is separate from SLA.
15. Expected execution window/grace period is separate from schedule.
16. PROD is the regular automated ETL monitoring scope.
17. Recovery actions are performed outside OpsControl.
18. Historical evidence should not be overwritten.
19. Initial Recent History is scoped to the same Job Order.

---

# 22. Development Workflow

The project is being built incrementally.

Current approach:

1. Validate the operational requirement with human/operator feedback.
2. Freeze the UX/data requirements for that capability.
3. Update this README.
4. Update the React prototype.
5. Define API contracts.
6. Define PostgreSQL schema.
7. Implement backend.
8. Connect real monitoring sources.
9. Test failure scenarios.
10. Document the final operational procedure.

**Do not design production database tables solely from assumptions.** The UI and operator workflow should be validated first.

---

# 23. Planned ETL Monitoring Lifecycle

```
Pentaho execution
      |
      v
Execution detected
      |
      v
Normalize event
      |
      v
Create/update Job Order History
      |
      +--> RUNNING
      |
      +--> SUCCESS
      |
      +--> FAILED
      |
      +--> LONG_RUNNING
      |
      +--> NO_RUN
      |
      v
Evaluate monitoring rules
      |
      v
Alert
      |
      +--> Email
      +--> PagerDuty
      +--> ServiceNow
      |
      v
Operator investigation
      |
      v
Manual recovery outside OpsControl
      |
      v
Monitor subsequent execution
      |
      v
Document / resolve investigation
```

---

# 24. Failure Investigation Example

Example scenario:

```
Organization:
ABC Corporation

VM:
HERO-PRDAPP001

Job Order:
JC_Pricing_Daily

Scheduled:
08:00

Actual:
08:00:01 start

Failed:
08:05:49

Failed Step:
Update Customer Database

Pentaho Error:
Connection timeout
```

OpsControl may correlate:

```
Database:
UNAVAILABLE

VM:
CPU 87%
RAM 61%
Disk 72%

Network:
HEALTHY

Tomcat:
HEALTHY
```

Operator workflow:

```
NEW
  |
ACKNOWLEDGED
  |
INVESTIGATING
  |
Database team contacted
  |
ROOT_CAUSE_IDENTIFIED
  |
Database listener restored
  |
RECOVERY_IN_PROGRESS
  |
Manual Pentaho recovery
  |
Next execution SUCCESS
  |
MONITORING
  |
RESOLVED
```

All important state transitions and notes should remain auditable.

---

# 25. Security and Operational Safety

Initial safety principles:

- No production job execution control from OpsControl.
- No VM restart action.
- No direct production configuration changes from the monitoring drawer.
- Integrations should use managed secrets/configuration rather than hard-coded credentials.
- Role-based access will be required before sensitive configuration/actions are exposed.
- Operator actions and investigation transitions should be auditable.
- Monitoring platform health must itself be monitored.

---

# 26. Documentation Standard

Every major feature should document:

### What it does
Purpose and operator value.

### Why it exists
Operational problem being solved.

### Architecture
Data flow and dependencies.

### Configuration
Step-by-step setup.

### Monitoring
What is collected, frequency, thresholds, and expected behavior.

### Alerts
Trigger condition, severity, notification path.

### Troubleshooting
Common failures and diagnostic steps.

### Recovery
Approved recovery procedure and ownership.

### Security
Credentials, permissions, secrets, network requirements.

### Database/API
Relevant entities, fields, event contracts, and relationships.

### Change history
What changed, why, and when.

This documentation is intended to support developers, NOC/operators, support teams, and future maintainers.

---

# 27. Current Decision Log

| Decision | Status |
|---|---|
| Top navigation | Confirmed |
| Action-first Overview | Confirmed |
| Overview refresh | 5 seconds |
| Historical trends on Overview | Excluded |
| System Health panel on Overview | Excluded |
| SFTP/S3 on Overview | Excluded |
| PROD-only regular ETL monitoring | Confirmed |
| Organization → VM → Application/ETL hierarchy | Confirmed |
| Job Order vs Job Order History separation | Confirmed |
| Organization + VM + Job Order Name = Job Order identity | Confirmed |
| Scheduled + manual executions captured | Confirmed |
| Simple + advanced schedules | Confirmed |
| Expected execution window/grace | Confirmed |
| Expected runtime separate from SLA | Confirmed |
| Full step-level Pentaho data | Confirmed |
| Failure diagnosis | Confirmed |
| Pentaho facts vs OpsControl diagnosis | Confirmed |
| Suspected cause vs confirmed root cause | Confirmed |
| Investigation lifecycle | Confirmed |
| Recent History scope | **Same Job Order only — Confirmed** |
| Cross-Job-Order failure correlation in Recent History | Excluded from initial view / Future capability |
| Alert & Incident History in Job Details drawer | **Important operational events only — Confirmed** |
| Complete integration audit log in Job Details drawer | Excluded from drawer / Future dedicated audit view |
| Retry Job from OpsControl | Excluded |
| Start/stop Pentaho job | Excluded |
| VM restart | Excluded |
| Manual recovery outside OpsControl | Confirmed |
| Email alerts | Confirmed |
| PagerDuty | Confirmed |
| ServiceNow | Confirmed |
| 1-year initial history | Confirmed |
| Reports emailed | Confirmed |
| Resource Management | Confirmed |
| RBAC | Planned |
| Production backend schema | Not yet frozen |

---

# 28. Next Design Stage

The next design stage remains:

## **Failed Job Details Drawer — operator workflow and data contract**

Already validated:

1. Execution Summary
2. Failure Diagnosis
3. Step-level execution
4. Timeline/events
5. Logs
6. Dependency correlation
7. **Recent History: same Job Order only**
8. **Alert & Incident History: important operational events only**
9. **PagerDuty/ServiceNow state: operational status, not full integration logs**
10. Investigation state
11. Operator notes
12. Audit history

The Alert History + PagerDuty/ServiceNow scope is now validated as **important operational events only**.

The next focused design step is to validate the **Investigation section and operator notes** portion of the drawer.

Only after the drawer is validated should we finalize:

- REST API contracts
- PostgreSQL tables
- indexes
- relationships
- event schema
- monitoring collector contract
- Pentaho integration strategy

---

## Project status

**Phase:** UX + operational requirements / POC

**Current focus:** Pentaho Job Details and failure investigation workflow

**Source of truth:** GitHub repository + this README

**Repository:** `Parikshit-Sahrawat/OpsControl_Dashboard`
