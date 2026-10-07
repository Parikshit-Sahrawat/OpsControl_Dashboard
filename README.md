# OpsControl Dashboard

OpsControl Dashboard is an enterprise operations monitoring platform being designed to give NOC, SLM, support, and engineering teams a single operational view of production ETL jobs, VMs, applications, APIs, incidents, alerts, and operational history.

> **Documentation principle:** This README is the living project knowledge base. Important architecture, requirements, operating rules, configuration decisions, implementation steps, and validated design decisions should be documented here as the project evolves.

---

## Current implementation status

**Phase:** UX + operational POC

**Current focus:** Production-quality ETL Jobs frontend contract

**Repository:** `Parikshit-Sahrawat/OpsControl_Dashboard`

**Frontend:** Vite + React under `frontend/`

The frontend remains mock-data driven while the API and PostgreSQL contracts are being finalized. No production Pentaho job control is exposed.

### ETL Jobs page now supports

- Current execution-focused monitoring
- `SUCCESS`, `FAILED`, `RUNNING`, `LONG_RUNNING`, and `NO_RUN` states
- No Run logic based on expected execution window + grace period
- Expected runtime vs SLA visual logic
- Environment filtering with PROD as the default operational scope
- Explicit Scheduled / Manual execution-type filtering
- Search by Job Order, Job Order ID, or server
- Status filter counts
- Loading, error, and empty states
- State-aware Job Details drawer for failed, running, successful, long-running, and no-run executions
- Execution timeline with source attribution
- Step-level execution with optional type/duration
- Related health information where available
- Same Job Order recent history
- Important operational alert/incident history
- Investigation lifecycle transitions
- Chronological Operator Notes
- Operator notes and investigation transitions are currently persisted in frontend state only
- 5-second refresh contract placeholder

### Monitoring rules

```text
Expected execution window + grace period
        |
        +-- execution detected -> normal execution monitoring
        |
        +-- no execution       -> NO_RUN

Execution runtime
        |
        +-- below expected runtime -> ON TRACK
        +-- expected runtime passed -> LONG_RUNNING / AT RISK
        +-- SLA passed             -> SLA BREACH
```

Expected runtime and SLA remain separate thresholds. The UI does not execute, retry, stop, or restart production workloads.

---

# 1. Project Goals

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

# 2. Current Product Scope

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

**VM restart actions are intentionally excluded from OpsControl.**

---

# 4. ETL Monitoring Scope

Regular automated ETL monitoring is currently focused on **PROD only**.

QA/Test/non-production environments are not part of the regular monitoring scope. The current frontend can display other configured environments for validation, but it explicitly identifies them as outside the regular automated scope.

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

## Job Order History

A Job Order History represents:

> **What actually happened during one execution?**

Every execution gets its own history record.

Scheduled and manual Pentaho executions are both captured.

Execution type:

- `SCHEDULED`
- `MANUAL`

---

# 6. ETL Scheduling

Both simple and advanced scheduling are required.

Simple schedules:

- Hourly
- Daily
- Weekly
- Monthly
- Quarterly

Advanced schedules:

- Every N hours
- Monday-Friday
- Specific days of month
- Multiple days/times
- Last working day
- First Monday of month
- Multiple execution windows
- Other future scheduling rules

Do not hard-code the database around only five frequency strings.

### Schedule vs expected execution

**Schedule** answers when the workload should run.

**Expected execution window** answers when OpsControl should expect an execution.

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

The frontend now visualizes this distinction directly in the ETL Jobs table and Job Details drawer.

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

The Job Details drawer is the operational contract for the future backend API and database.

It is now state-aware:

- Successful execution
- Running execution
- Failed execution
- Long-running execution
- No-run condition

### Current drawer sections

1. Execution Summary
2. Failure Diagnosis, where applicable
3. Monitoring Diagnosis for No Run / Long Running
4. Execution Timeline
5. Step-level Execution
6. Related Health
7. Alert & Incident History
8. Recent History — same Job Order only
9. Investigation
10. Operator Notes

The drawer does not expose:

- Retry Job
- Start Job
- Stop/Cancel Job
- Restart VM
- Production Pentaho configuration changes

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

The React drawer now allows the operator to advance an investigable execution through this lifecycle.

Each transition records:

- Previous state
- New state
- Operator
- Timestamp
- Optional comment/reason in the future API contract

Execution status and investigation status remain separate.

A successful subsequent execution does not automatically resolve an investigation.

---

# 11. Operator Notes

The initial design uses simple chronological notes.

Each note contains:

- Note ID in the future backend
- Investigation ID in the future backend
- Operator
- Timestamp
- Note text
- Optional evidence/reference

The React prototype now provides a working **Add Note** interaction.

Current limitation:

> Notes are stored only in frontend state. Backend persistence will be implemented after the API contract is frozen.

Adding a note does not automatically change investigation status.

---

# 12. Execution Timeline

The Job Details drawer now supports structured timeline events.

Example:

```
08:00:01  Job started             Pentaho
08:01:12  Extract started         Pentaho
08:04:21  Transformation started  Pentaho
08:05:48  Database error          Pentaho
08:05:49  Job failed              Pentaho
08:05:55  Failure detected        OpsControl
08:06:01  PagerDuty triggered     PagerDuty
08:06:05  ServiceNow created      ServiceNow
```

The future backend should normalize source events while preserving their source attribution.

---

# 13. Step-level Execution

The drawer supports step-level states and optional metadata.

Potential fields:

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

Fields remain optional when the Pentaho source cannot provide them.

---

# 14. Loading, Error, and Empty States

The ETL Jobs page now explicitly handles:

### Loading

Shows an operational loading state while execution data is being refreshed.

### Error

Shows an actionable error state with a Retry action.

### Empty

Shows a clear no-results state when filters/search return no executions, with a Clear Filters action.

These states are part of the frontend/API contract and should remain present when mock data is replaced by FastAPI.

---

# 15. Environment Handling

The ETL Jobs page now has a dynamic environment selector.

Current behavior:

- Defaults to `PROD`
- Detects configured environments from execution data
- Supports `All`
- Supports explicit environment filtering
- Shows a scope warning for non-PROD environments

Regular automated monitoring remains PROD-only.

This allows the UI to be ready for future multi-environment configuration without silently implying that QA/Test monitoring is already production scope.

---

# 16. Execution Type Filtering

The ETL Jobs page now supports:

- All
- Scheduled
- Manual

Execution type is displayed for every execution.

This is important because a manual execution is not automatically considered a recovery.

---

# 17. Alerts and Integrations

Initial alerting channels:

- Email
- PagerDuty

Incident integration:

- ServiceNow

The Job Details drawer shows important operational milestones rather than complete integration audit logs.

---

# 18. SFTP / S3 Monitoring

SFTP/S3 monitoring is not displayed on the Overview page.

Where implemented, checks should focus on:

- Expected file
- Expected arrival time
- Actual arrival time
- File size
- File age

Content validation is currently excluded.

---

# 19. API Monitoring

API monitoring requirements include:

- HTTP status
- Response time
- Availability
- Response body
- Authentication
- SSL
- Certificate expiry
- Request/response logging

---

# 20. VM Monitoring

VM monitoring should include:

- Availability
- CPU
- RAM
- Disk by drive
- Services
- Processes
- Applications
- Event/log information where useful

---

# 21. Reports

Reports are separate from the action-first Overview page.

Initial retention target: **1 year**.

ETL reports:

- Job success/failure trends
- SLA compliance
- Runtime trends
- Failure analysis
- Execution history
- Recurring failures
- Long-running jobs
- No-run events

---

# 22. Resource Management

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

---

# 23. Roles and Permissions

Potential roles:

- Admin
- Operator
- Viewer
- Support
- Manager

RBAC is planned.

---

# 24. Proposed Architecture

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

---

# 25. Security and Operational Safety

Initial safety principles:

- No production job execution control from OpsControl.
- No VM restart action.
- No direct production configuration changes from the monitoring drawer.
- Managed secrets rather than hard-coded credentials.
- RBAC before sensitive configuration/actions.
- Operator actions and investigation transitions must be auditable.
- Monitoring platform health must itself be monitored.

---

# 26. React Frontend Structure

```
frontend/
├── index.html
├── package.json
├── vite.config.js
└── src/
    ├── main.jsx
    ├── App.jsx
    ├── styles.css
    ├── data/
    │   └── mockData.js
    ├── components/
    │   ├── KpiCard.jsx
    │   ├── JobDetailsDrawer.jsx
    │   ├── StatusBadge.jsx
    │   └── TopNav.jsx
    └── pages/
        ├── Overview.jsx
        └── ETLJobs.jsx
```

The frontend currently uses mock operational data to validate the UI contract before backend implementation.

---

# 27. Development Workflow

1. Validate operational requirement with human/operator feedback.
2. Freeze UX/data requirements for that capability.
3. Update README.
4. Update React frontend.
5. Define API contracts.
6. Define PostgreSQL schema.
7. Implement backend.
8. Connect real monitoring sources.
9. Test failure scenarios.
10. Document operational procedure.

**Do not design production database tables solely from assumptions.**

---

# 28. Current Decision Log

| Decision | Status |
|---|---|
| Top navigation | Confirmed |
| Action-first Overview | Confirmed |
| Overview refresh | 5 seconds |
| Historical trends on Overview | Excluded |
| SFTP/S3 on Overview | Excluded |
| PROD-only regular ETL monitoring | Confirmed |
| Organization → VM → Application/ETL hierarchy | Confirmed |
| Job Order vs Job Order History | Confirmed |
| Scheduled + manual executions | Confirmed |
| Simple + advanced schedules | Confirmed |
| Expected execution window/grace | Confirmed |
| Expected runtime separate from SLA | Confirmed |
| No Run detection | Confirmed in frontend contract |
| Environment filtering | Confirmed |
| Execution-type filtering | Confirmed |
| Full step-level Pentaho data where available | Confirmed |
| Execution timeline | Confirmed |
| Loading/error/empty states | Confirmed |
| Investigation lifecycle | Confirmed |
| Operator Notes | Simple chronological notes — Confirmed |
| Recent History | Same Job Order only — Confirmed |
| Alert & Incident History | Important operational events only — Confirmed |
| Retry/Start/Stop Pentaho job | Excluded |
| VM restart | Excluded |
| Recovery outside OpsControl | Confirmed |
| Email | Confirmed |
| PagerDuty | Confirmed |
| ServiceNow | Confirmed |
| 1-year initial history | Confirmed |
| Reports emailed | Confirmed |
| Resource Management | Confirmed |
| RBAC | Planned |
| Production backend schema | Not yet frozen |

---

# 29. Next Implementation Stage

The ETL Jobs frontend contract is now sufficiently mature to move toward:

1. FastAPI REST contract
2. PostgreSQL Job Order / Job Order History schema
3. Investigation and Operator Note API
4. ETL execution collector contract
5. Pentaho integration strategy
6. Real 5-second polling/refresh behavior
7. Alert and incident integration adapters
8. Authentication/RBAC

The next backend design should preserve the frontend distinctions already established:

- Job Order vs Job Order History
- Scheduled vs Manual
- Expected runtime vs SLA
- Schedule vs expected execution window
- Execution status vs investigation status
- Pentaho source facts vs OpsControl analysis
- Suspected cause vs confirmed root cause
- Same Job Order history vs broader correlation
- Operational incident milestones vs technical integration audit logs

---

## Project status

**Phase:** UX + operational requirements / POC

**Current focus:** React frontend + ETL Jobs operational page

**Source of truth:** GitHub repository + this README

**Frontend:** Vite + React application under `frontend/`

**Current frontend stage:** Production-quality ETL Jobs UX contract using mock data

**Repository:** `Parikshit-Sahrawat/OpsControl_Dashboard`
