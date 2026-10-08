# Pentaho Collector Design

## Purpose
The Pentaho collector converts Pentaho execution evidence into the OpsControl execution contract. It is a monitoring collector, not a job controller.

## Boundary
The collector may discover configured Job Orders, read execution status and timestamps, read step-level data when available, read source errors/log locations, detect new executions and changes, and publish normalized execution events.

The collector must not start, retry, stop, or cancel Pentaho jobs; change transformations or schedules; restart VMs; or store credentials in source code.

## Architecture
Pentaho -> read-only adapter -> Pentaho Collector -> normalize/deduplicate -> FastAPI ETL API -> PostgreSQL.

The collector runs independently from the API process.

## Collection cycle
1. Load active PROD Job Orders.
2. Resolve the Pentaho instance.
3. Query only the execution information needed for the monitoring window.
4. Match source execution to Job Order.
5. Calculate a stable source execution key.
6. Compare with the last observation.
7. Create or update Job Order History.
8. Upsert step execution data where available.
9. Preserve source facts exactly as received.
10. Let OpsControl derive LONG_RUNNING, SLA and NO_RUN.

## Idempotency
Preferred source identity is pentaho instance + repository/job identity + source execution ID. If Pentaho has no stable execution ID, use a deterministic fingerprint from job identity, scheduled start and source run metadata, and mark the identity as derived.

## State mapping
Finished successfully -> SUCCESS
Finished with error -> FAILED
Currently executing -> RUNNING
Missing expected execution -> NO_RUN (derived by monitoring engine)
Source unavailable -> NO_RESPONSE
Running beyond expected runtime -> LONG_RUNNING (derived by monitoring engine)

## Source facts vs analysis
Collector-owned facts: source execution ID, source status/result, timestamps, source error code/message, failed step, exception, log location and step metadata.

OpsControl-owned analysis: failure category, suspected cause, confidence, root cause, SLA status and investigation state.

The collector must never overwrite confirmed root cause data.

## Adapter interface
Start with a provider-neutral interface:
- discover_job_orders()
- list_executions(job_order)
- get_execution(execution_ref)
- get_steps(execution_ref)
- get_source_error(execution_ref)

The first production adapter should be read-only and support one Pentaho environment at a time.

## Reliability and security
Transient source failures use bounded retries with backoff. A collector outage must remain observable through collector health metrics/logs. Do not convert a transport failure into ETL FAILED; use NO_RESPONSE when source state cannot be queried reliably.

Credentials and connection details belong in managed secrets/environment configuration. Use the minimum read-only Pentaho permissions required.

## Future
Webhook/event ingestion, incremental checkpoints, Prometheus collector metrics, dead-letter handling, and per-instance adapter versions can be added without changing the Job Order/History contract.
