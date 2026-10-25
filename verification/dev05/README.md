# DEV-05.0 disposable full-product verification

This harness builds **application source from the exact baseline**
`f617cc653a965c2ad1bb7edf9e20237e40044b97` using `git archive`, then adds only
`verification/dev05`. Working tree application changes and later application
commits cannot silently change the tested product. No production deployment,
customer endpoint, provider identity or host Docker socket is exposed to tests.

Requirements: Linux Docker Engine + Compose v2 + BuildKit, Python 3.12+, OpenSSL,
Git with the baseline object available, sufficient disk for Playwright/Chromium,
and permitted build-time access to Docker Hub, Debian package mirrors,
PyPI and npm. Builds retain TLS verification and use a BuildKit CA secret.

Run from the repository checkout:

```sh
python verification/dev05/run.py --output /tmp/dev05-evidence-unique
```

The output directory must not already exist. Expect an exit code of 1 on any
failed required check or incomplete cleanup. `acceptance.json` distinguishes
PASS, FAIL, BLOCKED and NOT TESTED; `regressions.json` records actual unit-test
counts and skips. Screenshots contain synthetic data only. `commands.log` and
`service.log` are redacted before export. No credential/session/CA private key
files are exported. Do not publish the temporary runtime directory.

Services: PostgreSQL, API (migration + demo bootstrap), Vite frontend, controlled
HTTPS fixture, remote worker container and pinned Playwright 1.56.1 with system Chromium (version captured in logs).
Worker cycles use the real baseline runner and lease/result protocol. Workers receive only their worker token and fixture CA; browsers receive only synthetic UI account credentials. PostgreSQL is reachable only from the API on its separate internal network. The database, control
and target networks are internal; no host ports are published. PostgreSQL trust
authentication is confined to the disposable internal network. Runtime proxy
variables are cleared so inherited build proxies cannot provide outbound egress.
The target subnet is selected after checking existing Docker subnets.

The API probes reuse baseline authenticated fixture seeding and assert immutable
rule versions, idempotent activation, real TLS results, PostgreSQL evidence,
metric/log counts, OPEN → RESOLVED alert identity, diagnostics, tenant boundaries
and append-only redacted audit history. Playwright uses real login and navigation,
activation and reload. No routes are mocked. Extra checks cover HEAD, latency,
forbidden methods/headers, worker revocation and read-only synthetic Carte.
Only related existing backend contract modules and frontend checks are run.
Existing unit fixtures do not constitute genuine provider certification.

The `finally` cleanup runs on success, failure, SIGINT and SIGTERM. It exports
artifacts first, then invokes Compose down with the unique project name and
volumes, inventories resources by that exact Compose project label and removes
the synthetic secret directory. It never runs prune or broad container removal.
Cached images/build layers may remain for reuse; live processes, networks,
volumes and secrets must not remain. SIGKILL or host loss cannot execute a finally
block; recover using the project identifier recorded in `acceptance.json` and
remove only resources with that exact label.

To test the failure cleanup path, use a separate output directory:

```sh
python verification/dev05/run.py --inject-failure --output /tmp/dev05-failure-unique
```

This intentionally returns 1 after stack startup; inspect `cleanup.json` for
zero remaining project containers, networks and volumes and removed secrets.

The acceptance report documents unexecuted scopes and repository defects.
Synthetic infrastructure projection and Pentaho contract tests are not live
EC2/Kubernetes/Windows/Pentaho runtime acceptance. No production operation is
part of this harness.

Reviewed run results and release blockers: [DEV-05.0 acceptance report](../../docs/verification/dev05/ACCEPTANCE.md).
