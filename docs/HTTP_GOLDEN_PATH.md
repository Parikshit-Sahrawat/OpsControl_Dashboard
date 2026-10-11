# HTTP monitoring golden path

This disposable lab onboards **Fictional HTTPS Portal** in **Golden HTTP Lab**. It uses an actual HTTPS server on an isolated Docker network, authenticated FastAPI calls, PostgreSQL, the real outbound agent, and the React UI in Playwright. It connects to no customer application.

## Run the lifecycle

Requirements: Docker Engine/Compose, Python 3, OpenSSL, Node 24 (or another Vite-compatible runtime), installed frontend dependencies, and Playwright 1.56.1 with Chromium. Ports 18000 and 15173 and Docker subnets 172.28.77.0/24 and 172.28.78.0/24 must be available. Run one copy at a time because the ports/subnets are fixed.

From the repository root:

```bash
(cd frontend && npm ci --cache /tmp/opscontrol-npm-cache --no-audit --no-fund)
npm install --prefix /tmp/opscontrol-browser-tools --cache /tmp/opscontrol-npm-cache --no-audit --no-fund playwright@1.56.1
/tmp/opscontrol-browser-tools/node_modules/.bin/playwright install --with-deps chromium
PLAYWRIGHT_MODULE=/tmp/opscontrol-browser-tools/node_modules/playwright/index.mjs \
  scripts/http-golden-path.sh
```

An installed system Chromium can be selected with `PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium` instead of downloading a browser. The cloud validation used this supported override. `GOLDEN_BUILD_CA_BUNDLE` selects a trusted package-download CA bundle; the default is `/etc/ssl/certs/ca-certificates.crt`. Installation keeps TLS verification enabled. The agent separately trusts only the generated fixture certificate and verifies its hostname.

`GOLDEN_EVIDENCE_DIR=/tmp/my-http-evidence` changes the artifact directory. The default is `docs/screenshots/http-golden-path/`. The runner creates a new Compose project, database volume, random account/worker credentials, and TLS key for each invocation. Its exit trap removes only that run's containers, networks, volume, and private files; existing development databases are untouched. Built Docker images are retained as ordinary local build outputs.

## What the assertions prove

1. A platform administrator authenticates and creates two fictional organizations, scoped users and memberships. The first organization's administrator creates the HTTPS Data Source through the API.
2. Metric, Log and Alert catalogs are published as immutable v1 rules. A new Metric v2 is published while activation remains pinned to v1. Preview validates the plan, activation provisions the collector and bindings, and repeat activation reuses the collector. Playwright signs in through the login form and exercises preview and idempotent activation in the UI.
3. The scheduler creates a leased job. An agent on internal target/control networks claims it, performs certificate-verified HTTPS against `portal.example.test`, and submits sanitized evidence. Target state is changed in the fixture, never by inventing evidence payloads.
4. Healthy HTTP 200 creates `probe_up=1`; failed HTTP 503 creates `probe_up=0` and opens one native alert; recovered HTTP 200 creates `probe_up=1` and resolves the same alert. Each phase checks completed jobs, evidence status/timing, tenant IDs, native samples, log events, pinned bindings, and the authenticated diagnostics API.
5. Playwright checks each phase's visible diagnostics, captures the actual rendered UI, and rejects browser JavaScript errors. Recovery shows zero open alerts, one resolved alert, and no stale collector error. Another tenant signs in and sees no first-tenant source or rules.
6. Anonymous diagnostics access is denied; cross-tenant reads, activation and source creation return 404; audit access is forbidden; scoped source/rule/alert lists reveal no first-tenant resources. Audit events are verified through the admin API and database, contain no credentials, and reject SQL UPDATE and DELETE. An agent socket check verifies public network egress is blocked.

The redacted JSON report contains phase counts, HTTP status, observed timestamps, source/organization IDs, selected rule version IDs, and audit metadata. Credentials remain in a temporary protected file and are deleted during cleanup. Screenshot capture does not expose worker enrollment tokens.

This validates a synthetic local/private HTTPS lifecycle. It does not validate production deployment, real private CA rotation, external notifications, customer networks, or a browser driving every resource-creation form. The test dispatches one job per phase instead of waiting for a long-running scheduler loop. CI execution is tracked independently from the local run.

## Verified local result

On 2026-10-11, `scripts/http-golden-path.sh` passed in the cloud workspace with Playwright 1.56.1 and system Chromium. All four browser phases and the second-tenant view passed without browser JavaScript errors. Three completed jobs produced HTTP 200/503/200 evidence, three native samples and three log events. The failure alert's ID matches the recovered alert's ID; one alert opened and then resolved. Anonymous/cross-tenant denials, redacted audit review, append-only SQL guards and public network egress denial passed. Frontend production build, backend mapper import, remote-egress negative tests and diff checks also passed.

The new CI workflow has **not run remotely** for these changes. The checked-in screenshots and report are from the successful local run. Disposable services, credentials and the lab database were cleaned up afterward.

## Actual browser evidence

- [Configured, no evidence yet](screenshots/http-golden-path/configured.png)
- [Healthy HTTP 200](screenshots/http-golden-path/healthy.png)
- [Failed HTTP 503 and open alert](screenshots/http-golden-path/failed.png)
- [Recovered HTTP 200 and resolved alert](screenshots/http-golden-path/recovered.png)
- [Other tenant sees no source or rules](screenshots/http-golden-path/other-tenant.png)
- [Redacted database and audit report](screenshots/http-golden-path/report.json)

The [golden path CI workflow](../.github/workflows/http-golden-path.yml) runs the same harness and uploads screenshots and evidence; it does not overwrite checked-in screenshots.
