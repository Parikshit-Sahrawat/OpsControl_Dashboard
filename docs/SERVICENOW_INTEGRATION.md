# ServiceNow incident delivery and controlled acceptance

ServiceNow is an outbound alert integration, not an ETL control interface. Existing native metric rules queue OPENED/RESOLVED events. Duplicate channel names are normalized. The destination/credentials are privileged deployment configuration; ordinary source configuration cannot select a ServiceNow host or table.

## Configuration

| Variable | Meaning |
|---|---|
| `OPSCONTROL_SERVICENOW_URL` | Exact HTTPS origin, without userinfo/path/query/fragment |
| `OPSCONTROL_SERVICENOW_CREDENTIAL_REF` | Approved external username/password reference; production requires the existing AWS Secrets Manager resolver and scoped workload IAM |
| `OPSCONTROL_SERVICENOW_USERNAME`, `OPSCONTROL_SERVICENOW_PASSWORD` | Development-only environment credentials, configured securely, never committed |
| `OPSCONTROL_SERVICENOW_TABLE` | Validated table identifier; defaults to `incident` |
| `OPSCONTROL_SERVICENOW_CORRELATION_FIELD` | Validated field identifier; defaults to `correlation_id` |
| `OPSCONTROL_SERVICENOW_ASSIGNMENT_GROUP` | Optional instance-approved assignment group |
| `OPSCONTROL_SERVICENOW_RESOLVED_STATE` | Instance-approved resolved choice; defaults to `6` |
| `OPSCONTROL_SERVICENOW_CLOSE_CODE` | Optional instance-required closure choice; validate its actual allowed value |

Provider TLS/hostname verification is mandatory; redirects are never followed. Responses are bounded to 8 KiB and validated for JSON envelope, duplicate keys and 32-character hexadecimal sys_id. A number, missing identity or path-like identity cannot mark a delivery SENT. Provider errors persist a generic status/classification, not raw response/credential/URL text.

OPENED uses `opscontrol:<alert_state_id>:OPENED` correlation. Retry looks up that correlation before creation; an ambiguous response after creation can recover the same sys_id. RESOLVED requires a successful OPENED delivery and PATCHes that same incident. Event message comes from the queued event snapshot, preserving an opening message even if recovery occurred before transport.

## Durable delivery claims

Migration `0024_notification_leases` adds nullable lease_token and lease_expires_at to the existing outbox table. Dispatch claims a bounded batch through short SKIP LOCKED transactions, releases all DB connections/row locks before network IO, and fences completion by token and unexpired lease. An alert-state lock serializes competing claims and legacy duplicate event rows; completed duplicate events reuse prior delivery references. Failed delivery retries after 30 seconds, up to five attempts. Processing leases expire after 120 seconds and can be reclaimed; exhausted processing is recorded FAILED.

RESOLVED waits for the successful opening reference. Permanent OPENED failure leaves resolution blocked until an operator repairs/retries the opening delivery through an approved administrative procedure. Do not invent a provider reference or bypass the source condition. Local operational incidents remain governed by their authenticated operator lifecycle even when their external ServiceNow counterpart is resolved.

The existing collector worker's independent notification loop invokes delivery; more worker replicas may process different alerts. Application rollback should retain compatible additive schema, stop in-flight dispatch safely, and avoid dropping live leases. Real SMTP/provider total-operation deadlines and sustained destination load still need deployment validation.

## Reproduce the controlled gate

From repository root with existing venv, Docker, OpenSSL and browser tools:

```bash
RELEASE_BROWSER_ACCEPTANCE=1 \
PLAYWRIGHT_MODULE=/absolute/path/playwright/index.mjs \
RELEASE_EVIDENCE_DIR=/tmp/servicenow-review \
backend/.venv/bin/python scripts/release-acceptance.py
```

`scripts.servicenow_acceptance_probe` uses an authenticated certificate-verified fictional Table API on an ephemeral loopback port. Real PostgreSQL rules/samples produce consecutive breach → one alert → recovery → correlated incident evidence. Assertions cover three creates/three resolves, duplicate channel normalization, competing dispatchers, no DB ownership during IO, retry after lost/failed creation response, expired lease fencing, malformed identities and redirects, and absence of fixture credentials from errors. [Redacted report](acceptance/operational-sequence/sprint4-servicenow.json).

This is genuine HTTP/TLS/database execution against a controlled API, **not** acceptance against an actual ServiceNow instance. Before real delivery approve tenant-to-destination routing, incident payload privacy, create/update ACLs, correlation uniqueness and choice/mandatory closure fields. Configure external credential/workload identity and test rotation; approve actual outbound messaging explicitly. The current destination is deployment-global, not separate per-tenant ServiceNow routing. Live AWS setup remains paused.
