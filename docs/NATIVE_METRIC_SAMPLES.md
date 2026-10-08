# Native Metric Samples

OpsControl now persists native metric samples produced by collector executions.

## Extraction contract

Metric definitions linked to a collector can set query_config.extract to one of:

- AVAILABILITY — 1 for a successful collection, 0 for a failed collection.
- HTTP_STATUS — HTTP response status when available.
- RESPONSE_TIME_MS — measured request duration.
- RESPONSE_SIZE_BYTES — captured response size.

Example:

```json
{
  "extract": "RESPONSE_TIME_MS"
}
```

A missing source value does not create a sample. This preserves the distinction between zero and not observed.

## Sample record

Each sample stores:

- organization
- metric definition
- collector
- collector run
- observation timestamp
- numeric value
- unit
- dimensions

Collector-run evidence remains the source record; metric samples are the normalized query layer.

## Query API

GET /api/v1/monitoring/metrics/{metric_definition_id}/samples

Optional query parameters:

- start
- end
- limit

Results are returned newest first.

## Retention

Metric definitions already contain retention_days. The collector worker performs retention cleanup once per hour and removes samples older than each metric definition's retention period.

## Current boundary

This stage does not yet evaluate Alert Rules or send notifications. The next layer will evaluate real samples against Alert Rules and maintain alert state without changing the collector evidence model.
