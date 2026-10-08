# API Basic Authentication Collector

The API collector is the first real OpsControl transport implementation.

## Supported configuration

A collector of type `API` uses:

```json
{
  "url": "https://example.internal/api/health",
  "method": "GET",
  "auth_type": "BASIC",
  "credential_ref": "prod_api",
  "timeout_seconds": 15,
  "expected_status": 200,
  "verify_ssl": true,
  "capture_response_body": false
}
```

Optional configuration:

- `headers`: static non-authorization headers
- `request_body`: JSON object/array or string for POST/PUT/PATCH
- `max_response_body_bytes`: bounded response capture, maximum 64 KiB

OpsControl rejects configured `Authorization` and `Proxy-Authorization` headers. Basic credentials are resolved from the credential reference instead.

## Local credential provider

For the current development/runtime implementation, the worker resolves a credential reference from environment variables.

For:

```
credential_ref = "prod_api"
```

the worker expects:

```
OPSCONTROL_CREDENTIAL_PROD_API_USERNAME=api-user
OPSCONTROL_CREDENTIAL_PROD_API_PASSWORD=<secret>
```

The password is never stored in collector JSON, logged, or returned by the API.

This environment-backed resolver is a local/development secret-provider boundary. A production deployment should replace `app/worker/credentials.py` with a managed secret provider without changing collector configuration.

## Runtime behavior

Each scheduled execution:

1. Loads the enabled collector and its Data Source.
2. Resolves the Basic Authentication credential.
3. Performs the configured HTTP request.
4. Measures response time.
5. Validates the HTTP status against `expected_status`.
6. Optionally captures a bounded response body.
7. Persists a `collector_runs` record.
8. Updates Collector and Data Source runtime status.
9. Schedules the next execution.

Important outcomes include:

- `SUCCESS`
- `UNEXPECTED_STATUS`
- `AUTHENTICATION_ERROR`
- `HTTP_ERROR`
- `TIMEOUT`
- `CONNECTION_ERROR`
- `TLS_ERROR`
- `CREDENTIAL_ERROR`
- `CONFIGURATION_ERROR`

An HTTP 401/403 is treated as an authentication failure. A transport failure is not treated as an application-level API failure.

## Collection result API

Recent executions are available from:

```
GET /api/v1/monitoring/collectors/{collector_id}/runs
```

The response includes status, outcome, HTTP status, response time, response size, bounded response body when enabled, and the error message when the run failed.

## Security boundaries

The API collector:

- is read-only from the monitored system
- never stores Basic Authentication passwords in PostgreSQL collector configuration
- never accepts an authorization header through collector configuration
- bounds captured response bodies
- does not log credentials
- supports TLS verification by default
- allows TLS verification to be disabled only when explicitly configured

Response-body capture should remain disabled unless the API response is known to be safe to retain.

## Worker

Start the collector worker separately from FastAPI:

```bash
python backend/scripts/run_collector_worker.py
```

The scheduler uses each collector's configured interval and polls for due work every five seconds.

## Next step

The next layer is native metric sample persistence and metric extraction from successful API collection results. That will let Metric Definitions and Alert Rules consume real API measurements rather than only collector health.
