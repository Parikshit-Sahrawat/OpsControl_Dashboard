# Correlation Engine

OpsControl now has a persisted correlation layer for ETL execution investigations.

## Purpose

The first correlation scope is intentionally narrow:

- same organization
- same execution VM
- applications on that VM
- bounded time window around the execution
- native metric samples
- native log events
- alert states

It does **not** infer a confirmed root cause.

## Data model

CorrelationRecord is one analysis result for one ETL execution.

CorrelationEvidence stores the source evidence that contributed to that analysis.

```
ETL Execution
     |
     v
Correlation Record
     |
     +-- Metric Sample
     +-- Log Event
     +-- Alert State
```

Source evidence remains source-derived. Correlation category, confidence, and summary are OpsControl inference.

## Correlation window

Default:

- 15 minutes before the execution anchor
- 15 minutes after the execution anchor

Anchor priority:

1. detected_at
2. ended_at
3. started_at

The API allows a caller to override the before/after window up to 24 hours.

## Resource matching

The first implementation matches:

- the execution Job Order VM
- applications directly attached to that VM

Metric Definitions and Log Sources must have a matching resource_id.

This avoids broad same-organization correlation noise.

## Evidence types

### METRIC_SAMPLE

A metric sample observed on a related VM/application in the time window.

This is supporting evidence only. A metric sample is not automatically classified as abnormal unless a separate alert or future rule evaluation establishes that.

### LOG_EVENT

ERROR, CRITICAL, and WARNING log events observed on a related resource.

### ALERT_STATE

An alert state whose related Metric Definition points to a VM/application involved in the execution and whose last evaluation falls inside the correlation window.

## Confidence

Current confidence is deliberately conservative:

- HIGH: critical alert or error/critical log evidence
- MEDIUM: alert or warning log evidence
- NONE: no alert/log evidence

Metric samples alone do not establish a probable cause.

## Categories

- LOG_ERROR
- RESOURCE_ALERT
- LOG_WARNING
- NO_RELATED_EVIDENCE

These categories describe correlated evidence, not confirmed root cause.

## API

Get the stored result:

GET /api/v1/etl/executions/{history_id}/correlation

Run/re-run correlation:

POST /api/v1/etl/executions/{history_id}/correlation

Optional query parameters:

- window_before_seconds
- window_after_seconds

Re-running correlation replaces the previous evidence set and increments analysis_version. Source evidence itself is not modified.

## Operational boundary

The correlation engine:

- does not restart VMs
- does not retry Pentaho jobs
- does not modify ETL definitions
- does not resolve investigations automatically
- does not overwrite source error evidence
- does not claim root cause without operator confirmation

## Future extensions

Planned later:

- API health evidence
- SFTP/S3 evidence
- dependency-aware correlation
- cross-resource topology
- incident correlation
- configurable correlation policies
- scoring/ranking of competing evidence
- automatic invocation after collector ingestion
