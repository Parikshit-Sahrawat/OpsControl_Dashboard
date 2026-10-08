# Demo Correlation Scenario Generator

OpsControl includes a synthetic scenario generator for validating the Correlation Engine without access to company infrastructure.

## What it creates

Each run creates an isolated synthetic organization containing:

- Windows VM
- Tomcat application
- Pentaho instance
- ETL Job Order
- failed ETL execution
- successful and failed ETL steps
- CPU and memory metric definitions
- three consecutive high-CPU metric samples
- CRITICAL high-CPU alert
- application log source
- ERROR and CRITICAL application log events
- persisted Correlation Record and Correlation Evidence

Scenario flow:

```
High CPU
   |
   +--> CRITICAL Alert
   |
Tomcat ERROR
   |
Tomcat CRITICAL
   |
   v
ETL database step fails
   |
   v
OpsControl Correlation
```

## Run

From the repository root, after PostgreSQL is running and migrations are current:

```bash
cd backend
python scripts/generate_correlation_scenario.py
```

Optional scenario name:

```bash
python scripts/generate_correlation_scenario.py --scenario vm-cpu-tomcat
```

Every invocation creates a new isolated synthetic dataset. It does not connect to company resources and does not modify existing demo records.

## Expected result

The generator should produce a correlation result similar to:

```
primary_category: RESOURCE_ALERT
confidence: HIGH
evidence_count: ...
```

The exact evidence count can change if the scenario is extended.

The result should include:

- CPU metric evidence
- memory metric evidence
- CRITICAL alert evidence
- Tomcat ERROR evidence
- Tomcat CRITICAL log evidence

The engine should **not** declare a confirmed root cause.

## Inspect the scenario

The script prints the generated:

- organization ID
- VM ID
- application ID
- job order ID
- execution/history ID
- metric ID
- log source ID
- alert rule ID
- correlation ID

Use the history ID with:

```
GET /api/v1/etl/executions/{history_id}/correlation
```

or re-run analysis:

```
POST /api/v1/etl/executions/{history_id}/correlation
```

## Safety

This is a synthetic-only validation tool.

It:

- does not connect to Windows
- does not connect to Pentaho
- does not connect to Tomcat
- does not send production alerts
- does not call PagerDuty
- does not call ServiceNow
- does not restart or modify any resource
- uses no company credentials

Alert notifications are intentionally configured with an empty channel list.

## Why this exists

The Correlation Engine needs repeatable failure scenarios before real collectors are connected.

This gives us a controlled test bed for validating:

1. evidence collection
2. temporal correlation
3. resource matching
4. alert correlation
5. log correlation
6. confidence calculation
7. investigation UI behavior

Later, additional scenarios can be added for:

- disk exhaustion
- RAM pressure
- Tomcat unavailable
- API latency
- API outage
- SFTP file missing
- S3 file late
- multiple simultaneous failures
- unrelated failures that should **not** correlate
