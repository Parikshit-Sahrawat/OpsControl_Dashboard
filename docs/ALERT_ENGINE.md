# Alert Rule Evaluation and Notifications

OpsControl now evaluates native metric samples against first-class Alert Rules.

## Evaluation

Supported operators: GT, GTE, LT, LTE, EQ, NE.

Each evaluation uses the current sample plus prior samples for the same Metric Definition inside the rule evaluation window.

consecutive_breaches counts consecutive newest samples that breach the condition.

Example: API response time > 1000 ms, window 60 seconds, consecutive breaches 3. The alert opens only after three consecutive samples inside the 60-second window breach the threshold.

A non-breaching sample resolves an existing OPEN alert.

## Alert state

Alert state is separate from Metric Sample evidence.

States: OPEN, RESOLVED.

Only a transition into OPEN or RESOLVED creates a notification delivery. Continued breach samples update the existing OPEN state without duplicate notifications.

An OPEN alert has one active state per Alert Rule. Historical RESOLVED states are preserved.

## Notification channels

Alert Rules can select EMAIL, PAGERDUTY, SERVICENOW.

Existing rules default to no channels, so adding this feature does not unexpectedly send notifications.

### PagerDuty

OpsControl uses PagerDuty Events API v2. OPENED sends a trigger event and RESOLVED sends a resolve event using the same deduplication key.

Required setting: OPSCONTROL_PAGERDUTY_ROUTING_KEY

### Email

OpsControl uses SMTP with STARTTLS.

Settings: OPSCONTROL_SMTP_HOST, OPSCONTROL_SMTP_PORT, OPSCONTROL_SMTP_USERNAME, OPSCONTROL_SMTP_PASSWORD, OPSCONTROL_ALERT_EMAIL_FROM, OPSCONTROL_ALERT_EMAIL_TO.

### ServiceNow

OpsControl creates an Incident through the ServiceNow Table API when an alert opens and updates that incident to the configured resolved state when the alert resolves.

Settings: OPSCONTROL_SERVICENOW_URL, OPSCONTROL_SERVICENOW_USERNAME, OPSCONTROL_SERVICENOW_PASSWORD, OPSCONTROL_SERVICENOW_TABLE, OPSCONTROL_SERVICENOW_ASSIGNMENT_GROUP, OPSCONTROL_SERVICENOW_RESOLVED_STATE.

Credentials are not stored in Alert Rules or notification records.

## Delivery reliability

Every notification transition is persisted in alert_notification_deliveries.

Delivery states: PENDING, SENT, FAILED.

Failed deliveries can be retried by the worker up to five attempts. Notification failure does not roll back the alert state or metric sample.

## APIs

Alert states:
- GET /api/v1/monitoring/alerts
- GET /api/v1/monitoring/alerts/{id}

Notification history:
- GET /api/v1/monitoring/alerts/{id}/notifications

Alert Rule channel configuration is available through the existing Alert Rule create/update APIs.

## Operational boundary

Alert evaluation never modifies the source resource. It does not restart VMs, retry Pentaho jobs, modify ETL definitions, or execute arbitrary production commands.

It only evaluates collected evidence and creates operational alert and notification records.