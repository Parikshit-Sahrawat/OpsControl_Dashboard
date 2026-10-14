# ARCH-001 V1.5 verification

These checks exercise the existing application and owned disposable test stack.
They do not deploy the application or access production databases. Tests using
provider response fixtures establish adapter contracts; they do not establish
successful connections to genuine external providers.

## Install the test tools

From the repository root, use Python 3.12, Node 24, Docker and Make:

```bash
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-providers.txt -r backend/requirements-hosts.txt -r backend/requirements-dev.txt
npm ci --prefix frontend --no-audit --no-fund
npm install --prefix /tmp/opscontrol-v15-tools --no-audit --no-fund prettier@3.5.3 playwright@1.56.1
/tmp/opscontrol-v15-tools/node_modules/.bin/playwright install --with-deps chromium
export PRETTIER_BIN=/tmp/opscontrol-v15-tools/node_modules/.bin/prettier
export PLAYWRIGHT_MODULE=/tmp/opscontrol-v15-tools/node_modules/playwright/index.mjs
```

The development requirements add Black, Ruff, Coverage and pip-audit. They are
not runtime dependencies. Set `OPSCONTROL_TEST_PYTHON` to an alternate Python
executable if required. The default is `backend/.venv/bin/python`.

For actual telemetry acceptance, supply the pinned Contrib 0.123.0 runtime using
`OPSCONTROL_OTEL_BINARY`. The continuous quality workflow extracts it from:

```text
otel/opentelemetry-collector-contrib:0.123.0@sha256:e39311df1f3d941923c00da79ac7ba6269124a870ee87e3c3ad24d60f8aee4d2
```

Use a verified copy of that runtime; do not replace compatibility validation with
an arbitrary newer binary. Native Windows installation requires the separate
Windows packaging workflow and target-host validation.

## Reproducible commands

| Command | Scope |
| --- | --- |
| `make test` / `make test-unit` | Complete backend unittest discovery with coverage, then frontend permission tests |
| `make test-agent` | Agent lifecycle/collection unit contracts and Linux installer shell parsing |
| `make test-integration` | Owned PostgreSQL migration/API/native engine/TLS Agent/OTel acceptance |
| `make test-e2e` | TLS runtime lab followed sequentially by a separate HTTP API/browser lab |
| `make test-security` | Access, release-hardening and remote-authentication regressions; actual Python/npm advisory scans |
| `make test-quality` | Black checks, Ruff correctness checks, focused Prettier checks, ESLint and production frontend build |
| `make test-coverage` | Merge executed coverage, emit JSON/XML and enforce the configured critical-module target |
| `make test-performance` | Actual bounded local API and authenticated OTLP load, requiring private input configuration |
| `make test-compatibility` | Independent Access schema/API/security regression and controlled legacy monitoring UAT |
| `make test-docker` | Owned Docker image builds, populated bootstrap, startup/restart and authentication smoke |
| `make test-all` | Quality, unit, Agent, sequential runtime/browser labs, Access/legacy workflow regressions, Docker smoke, security and coverage gate |

Failures return a nonzero exit status. The quality workflow runs on every push to
`main`, pull requests and manual dispatch. Dependency downloads use pip/npm
caches; Docker image layers use scoped GitHub Actions caches and inline-cache
images consumed by the owned smoke build. The Docker smoke gate is mandatory.
It retains reports and actual browser
screenshots even when a gate fails. No failure is converted into a passing check.

`make test-quality` checks all Python files in the registry, unified monitoring,
telemetry, pipeline-adapter and Agent modules. Ruff currently checks syntax and
undefined-name/control-flow correctness (`E9,F63,F7,F82`); it does not claim to be
a complete static security analysis. Prettier checks the changed access UI and its
browser test. Other existing frontend formatting conventions remain unchanged.

## Owned integration environment

`scripts/arch001-acceptance.py` creates and cleans up its own disposable PostgreSQL
container, private randomized credentials, temporary test files and local servers.
It verifies populated migration preservation and downgrade safeguards before
running the enabled acceptance checks. It never migrates a user's configured
Docker development database. Its fixture data is explicitly controlled test
input. Genuine provider, Windows-service and production failover acceptance must
be recorded separately.

The shared test runner enables the API, engine and real runtime flags. The E2E
runner first completes a TLS runtime lab, then starts a separate HTTP browser
lab with `ARCH001_BROWSER_ACCEPTANCE=1` and runtime disabled. This keeps trusted
TLS Agent verification separate from Chromium API trust requirements. Both runs
retain their own evidence under `owned-lab-runtime` and `owned-lab-browser`. Docker must be usable
by the current user. The harness requires working pinned runtime and browser
tools; missing tools are errors, not skipped success.

Do not run networking integration harnesses concurrently with the browser run.
Docker networking changes can invalidate Chromium's current network context.

## Coverage evidence and target

Coverage includes branch and statement execution for these critical areas:

- Attribute registry.
- Unified resources, reconstruction, schedules, correlation and reports.
- Managed telemetry, enrollment, ingestion and configuration.
- Pipeline adapters.
- Agent supervisor and service health.
- Native incident lifecycle, APIs and persistence.

Unit tests produce parallel coverage files. The owned integration runner enables
Coverage startup in child FastAPI, worker and Agent Python processes. Only
processes which actually execute and flush their coverage contribute evidence.
SIGTERM coverage saving is enabled so gracefully terminated local server/Agent
processes retain executed coverage. Forced SIGKILL cannot flush evidence and must
not be described as verified coverage. Unexecuted modules remain in the denominator. Fixture and browser test code is
not included in the critical application coverage denominator.

The target is **80%**; `make test-coverage` fails below it. The threshold can be
changed explicitly with `OPSCONTROL_COVERAGE_MIN`, but a lower local threshold is
not evidence that the standard target passed. The main workflow fixes the target
at 80%.

The current clean verification results are recorded in `ARCH-001_IMPLEMENTATION_STATUS.md`. Always use a fresh evidence directory for a source revision; historical coverage and screenshots do not certify subsequently changed code.

By default, reports are written to `/tmp/opscontrol-v15-quality`. Set
`OPSCONTROL_TEST_EVIDENCE_DIR` to an isolated directory for each independent run.
For a clean baseline use a new directory rather than mixing evidence from different
commits. JSON/XML reports contain source paths and coverage results, not credentials.

## Dependency security checks

Python advisories are checked against the installed requirement definitions using
`pip-audit --strict`. The npm scan checks the locked frontend including development
dependencies, with failure severity `high` or above. Both scanners save their JSON
reports, and either failing scanner fails the security target. Network/scanner
errors are recorded as failed execution, not interpreted as an advisory-free scan.

Fix vulnerable dependencies and rerun relevant functional checks. Do not suppress
an advisory merely to make CI green. Any accepted exception needs a separately
reviewed documented assessment.

## Measured local performance

The performance runner accepts **only localhost or literal loopback origins** and
requires `ENV=test`/`development` plus `OPSCONTROL_PERFORMANCE_ACCEPTANCE=1`. It
refuses redirects and validates TLS with the configured trust store. It does not
load production origins, accept public test targets or disable certificate checks.

Create a private owner-only input JSON file outside the checkout. Supply the
actual user session and enrolled Agent credentials from the owned test harness;
never copy token values into documentation, command arguments or commits:

```json
{
  "base_url": "https://127.0.0.1:YOUR_OWNED_API_PORT",
  "api_token": "REPLACE_PRIVATELY_WITH_OWNED_TEST_USER_TOKEN",
  "agent_token": "REPLACE_PRIVATELY_WITH_OWNED_ENROLLED_AGENT_TOKEN",
  "ca_file": "/private/test-ca.pem",
  "requests": 200,
  "concurrency": 8,
  "timeout_seconds": 10,
  "max_p95_ms": 2000,
  "max_error_rate": 0,
  "min_requests_per_second": 1
}
```

```bash
chmod 600 /private/performance-inputs.json
export OPSCONTROL_PERFORMANCE_INPUTS=/private/performance-inputs.json
make test-performance
```

A harness can invoke the same interface directly:

```bash
ENV=test OPSCONTROL_PERFORMANCE_ACCEPTANCE=1 backend/.venv/bin/python scripts/test-performance.py --inputs /private/performance-inputs.json --output /tmp/performance.json
```

The runner sends inventory GET requests to `/api/v1/unified/resources` and unique
OTLP metric POST batches to `/api/v1/agent/otlp/v1/metrics`. Unique batch timestamps
prevent repeated transport-idempotency hits from masquerading as ingestion
throughput. The metric is named `opscontrol.lab.performance` and tagged
`CONTROLLED_LOAD_TEST`. Use a disposable Agent/customer and database; test samples
are genuine HTTP-ingested controlled input, not production health evidence.

Bounds are 1–10,000 requests per mode, 1–32 concurrent workers, and a timeout of
at most 60 seconds. The result includes measured request rate, mean/p50/p95/p99
latency, error fraction and status counts. Each mode must satisfy the explicitly
configured thresholds. The default thresholds are a local regression baseline,
not a promised product capacity or SLA.

HTTP acceptance measurements must be paired with the owned integration harness's
actual persistence/reception checks. Performance results alone do not prove
collector recovery, database durability, production scale, regional failover or
successful external provider acceptance.
