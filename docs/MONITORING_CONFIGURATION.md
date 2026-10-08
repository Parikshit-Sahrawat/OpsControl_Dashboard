# OpsControl Dynamic Monitoring Configuration

This document defines the first control-plane model for building OpsControl's native monitoring platform without Prometheus or Grafana.

## Design principle

Monitoring behavior is configuration-driven:

```
Data Source
   |
   +-- Collector
   +-- Metric Definitions
   +-- Log Sources
```

The UI will eventually create and modify these objects. Collectors consume the configuration; operators do not edit collector code for each monitored resource.

## 1. Data Source

A Data Source represents a connection or source system.

Examples:

- WINDOWS
- LINUX
- API
- PENTAHO
- SFTP
- S3
- DATABASE
- FILE

Core fields:

- organization_id
- name
- source_type
- endpoint
- auth_type
- connection_config
- enabled
- status
- last_test_at
- last_error

`connection_config` is intentionally structured JSON so connector-specific settings can evolve without schema changes. Production credentials must not remain in plaintext configuration; managed secret storage will be added before production connectors are enabled.

## 2. Collector

A Collector defines how a Data Source is collected.

Core fields:

- data_source_id
- name
- collector_type
- enabled
- interval_seconds
- configuration
- status
- last_run_at
- last_success_at
- last_error_at
- last_error
- next_run_at

The Collector Manager will eventually schedule collectors independently of FastAPI request handling.

Initial collector lifecycle:

```
STOPPED
   |
   v
STARTING
   |
   v
RUNNING
   |
   +----> ERROR
   |
   v
STOPPED
```

The current database model stores runtime status fields. Scheduler/runtime behavior is intentionally a later implementation step.

## 3. Metric Definition

A Metric Definition describes what should be collected.

Example:

```json
{
  "name": "vm.cpu.usage",
  "resource_type": "VM",
  "resource_id": "<vm-id>",
  "metric_type": "GAUGE",
  "unit": "percent",
  "collection_interval_seconds": 30,
  "retention_days": 365,
  "aggregation": "avg"
}
```

The definition is configuration. Metric samples are separate runtime data and will be implemented by the native metrics subsystem.

Avoid putting high-cardinality operational values such as execution IDs, incident IDs, raw error messages, or timestamps into metric definition identity.

## 4. Log Source

A Log Source describes where logs should be collected.

Example:

```json
{
  "name": "IEngine Error Logs",
  "source_type": "FILE",
  "resource_type": "VM",
  "resource_id": "<vm-id>",
  "location": "D:\\Intellicus\\logs\\IEngine\\*.log",
  "parser_type": "PATTERN",
  "start_position": "NEW",
  "collection_interval_seconds": 30,
  "retention_days": 30
}
```

Parser configuration is structured JSON so different log formats can be supported without changing the database schema.

Initial parser concepts:

- RAW
- PATTERN
- JSON
- CSV
- REGEX

Actual parsing/runtime is a later phase.

## 5. API boundary

The current API is:

```
/api/v1/monitoring
```

The API provides CRUD/configuration operations only.

It does not yet:

- execute collectors
- collect metrics
- collect logs
- store metric samples
- store log events
- evaluate alerts
- test external connections

Those capabilities belong to subsequent implementation stages.

## 6. UI direction

The Resource Management UI should eventually expose:

```
Monitoring
|
+-- Data Sources
|    +-- Add
|    +-- Edit
|    +-- Enable / Disable
|    +-- Connection Test
|
+-- Collectors
|    +-- Configure
|    +-- Enable / Disable
|    +-- Runtime Status
|
+-- Metrics
|    +-- Define
|    +-- Enable / Disable
|
+-- Logs
     +-- Define
     +-- Parser
     +-- Retention
     +-- Enable / Disable
```

The UI should display the relationship between the four objects rather than treating them as unrelated settings.

## 7. Safety boundary

OpsControl is initially a monitoring and investigation platform.

The configuration model must not introduce:

- Pentaho start/retry/stop controls
- VM restart controls
- arbitrary production command execution
- unprotected credential storage

Any future action capability requires explicit RBAC and audit design.
