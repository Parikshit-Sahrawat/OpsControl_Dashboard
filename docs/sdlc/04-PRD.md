# DOC-04 — Product Requirements and User Journeys
**Status:** Draft | **Version:** 0.1

## Product principles
Operator-first, organization-aware, evidence-based, configuration-driven, least-privilege and auditable. The UI should never imply that a template is collecting data until an enabled collector actually runs and reports health.

## Journey A — Onboard an organization and source
1. Authorized administrator selects or creates an organization.
2. Creates a data source with type, environment, endpoint and authentication reference.
3. Tests connectivity without exposing secrets.
4. Attaches a compatible monitoring template.
5. Reviews the **effective configuration**: collector, schedule, metric definitions, log sources and alert rules.
6. Enables monitoring and sees collector status, first successful collection and latest evidence.

**Acceptance:** source is visible only to authorized organization users; activation produces persisted collector runs and observable samples/events; invalid configuration surfaces actionable errors.

## Journey B — Monitor Pentaho batch execution
1. Operator selects organization/environment and views scheduled/running jobs.
2. Opens a job to see schedule, status, last run, duration and source execution ID.
3. Reviews available step-level progress, source errors and historical executions.
4. Distinguishes job FAILED, expected execution NO_RUN, collector NO_RESPONSE and LONG_RUNNING.
5. Escalates with evidence and timestamps.

**Acceptance:** no source job mutation; historical runs retained; missing step data clearly labeled unavailable rather than fabricated.

## Journey C — Investigate and notify
1. An alert rule evaluates persisted evidence.
2. Alert opens only after configured criteria and stores evidence.
3. Notification delivery records retries and external reference.
4. Operator drills into related logs, metrics and ETL executions.
5. Correlation offers evidence-based hypotheses, not confirmed RCA.
6. Recovery resolves alert and emits configured transition notification.

**Acceptance:** no duplicate notifications for ongoing breach; transport failure does not discard alert state; tenant boundaries hold.

## Journey D — Navigate KPI summaries
1. Operator clicks a count card.
2. UI opens the matching filtered list.
3. List total matches the card's scope, organization, environment and status.
4. Filters remain visible and can be cleared.

**Acceptance:** navigation is keyboard accessible and count/list scope is consistent.

## UX requirements
No trend or system-health sections on the home page unless explicitly reapproved; maintain dedicated resource views where relevant. Five-second polling is a target subject to load validation. Empty, loading, stale, disconnected and error states must be distinct.

## Decisions pending
First production adapter; preferred source environments; RBAC roles; severity mapping; retention; permitted notifications; accessibility target.
