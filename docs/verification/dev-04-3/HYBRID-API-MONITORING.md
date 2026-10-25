# DEV-04.3 — Hybrid API Monitoring

## Baseline
Created from `main` at PR #63 merge commit `6d5fdbf126f9bde296de473a8cdbbaebb0afc7e1`. Kubernetes monitoring retirement remains out of scope.

## Increment 1: safe API configuration contract
- A shared validation module is used at activation planning and worker dispatch.
- Existing remote HTTP probes remain HTTPS GET with bounded expected status and timeout.
- Unsafe or unsupported methods, headers, queries, request bodies, redirects and targets are rejected before any lease is issued.
- Worker network policies, tenant isolation, Basic-auth credential references, DNS pinning and existing evidence remain intact.
- Contract tests cover backward compatibility and rejection cases.

## Increment 2: hybrid API worker execution (in progress)
- Versioned claim payload: v1 workers receive only GET without custom headers; upgraded agents advertise `api_protocol: 2`.
- V2 supports HTTPS GET and HEAD, a single narrowly approved `x-opscontrol-check` header, bounded status/timeouts and pinned TLS with existing DNS/network policies.
- Existing Basic-auth credential references remain worker-policy-gated and resolved only after destination validation. No raw secrets, bodies, URLs or request headers enter evidence.
- POST, arbitrary Authorization headers, request bodies, query strings and redirects remain denied.
- Compatibility and injection tests added; CI and integrated acceptance still need verification.

## Increment 3: operational evidence and response assertions (initial slice)
- Optional `max_response_time_ms` (1..10000) is validated in the control plane and again by the worker.
- Worker evaluates both expected HTTP status and latency threshold, returning `ASSERTION_FAILED` on violations while preserving bounded status, elapsed time and response-size evidence.
- Result ingestion rejects a reported `SUCCESS` when it contradicts the leased status/latency contract; existing availability, response-time metrics, log events and alert evaluation continue to operate.
- No raw response bodies, headers, credentials or target URLs are accepted in result evidence.
- Follow-up: explicit recovery transition acceptance and end-to-end worker/database verification; CI results must pass before marking this slice complete.

## Increment 4: Monitoring Setup UI (initial integration)
- Monitoring Setup now exposes HTTPS endpoint override, GET/HEAD method, expected status, timeout, bounded latency assertion, and approved check header for non-infrastructure sources.
- Preview and activation pass the same `api_config` object. The control plane accepts only explicit non-secret API fields, validates them against worker network policy, and persists approved settings in the activated collector.
- Worker selection, rule-version bindings, activation and live diagnostics use the existing organization-scoped workflow. No health is implied until fresh evidence arrives.
- Source changes clear unsaved request settings. Authenticated UI smoke covers the API editor.
- Follow-up acceptance: verify browser/backend round-trip, reload behavior, worker dispatch and failure/recovery transitions. CI is required before this stage is complete.

## Next increments
1. Design versioned remote-worker capability negotiation before permitting HEAD or additional methods.
2. Implement allowlisted headers and canonical request serialization with no secret-bearing telemetry.
3. Add bounded response assertion operators and sanitized evidence, including response-code and latency checks.
4. Extend Monitoring Setup forms, preview and diagnostics only after the worker can execute matching capabilities.
5. Add disposable PostgreSQL and HTTPS-server acceptance, including lease replay, auth and tenant boundaries.

## Acceptance gate
This increment is not a completed hybrid API monitoring feature. The DEV-04.3 PR is draft until the worker implementation, end-to-end tests, UI and security acceptance pass. Do not merge solely on contract test success.
