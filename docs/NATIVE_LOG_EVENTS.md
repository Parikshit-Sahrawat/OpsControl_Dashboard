# Native Log Events

OpsControl now has a native structured log-event layer.

## Model

A Log Source describes where logs come from. A Log Event is one observed log record.

Each event stores:

- organization
- log source
- observed timestamp
- severity
- event type
- message
- parser type
- source offset
- optional fingerprint
- structured attributes

Raw message content is preserved as evidence. Structured fields are available for filtering and future correlation.

## API

Create an event:

POST /api/v1/monitoring/logs/{log_source_id}/events

Query events:

GET /api/v1/monitoring/logs/{log_source_id}/events

Query supports:

- start
- end
- severity
- search
- limit

## Operational boundary

The current API stores normalized log evidence but does not execute arbitrary commands or directly read production log files.

Future collectors will populate this table through the Log Source / Collector architecture.

## Retention

LogSource.retention_days is the intended retention policy. The worker will enforce log retention when native log collection is implemented.

## Correlation direction

The first correlation implementation connects log events to ETL executions through:

Log Event
  -> resource
  -> bounded time window
  -> ETL execution
  -> Correlation Record / Evidence

Metric samples and alert states are also correlated through the same resource and time-window model.

Correlation must preserve the distinction between source evidence and OpsControl inference. See `docs/CORRELATION_ENGINE.md`.
