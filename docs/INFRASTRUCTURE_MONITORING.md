# Sprint 2 infrastructure monitoring

Branch: `feature/sprint2-infrastructure-monitoring`, based on the verified Sprint 1 HTTP reference. This development slice reuses organization-scoped sources, immutable rule versions, preview/apply activation, native metric samples and stable alert recovery. Production acceptance remains separate.

## Evidence origins and acceptance

| Provider | Environment used by this gate | Genuine field acceptance |
|---|---|---|
| AWS EC2 / CloudWatch | Actual boto3/botocore models and Stubber responses; discovery, status checks and CPU request contract | Pending approved sandbox identity |
| Kubernetes Pod / Deployment / Node | Actual Kubernetes SDK over certificate-verified HTTPS, bearer authentication and a fixed read-only controlled API | Pending suitable cluster; local kind could not start because this cloud kernel lacks `/dev/kmsg` and default IPv6 iptables support |
| Linux CPU / memory / disk / process | Live local `/proc/stat`, `/proc/meminfo`, filesystem and an actual disposable process | Local Linux worker exercised |
| Windows CPU / memory / disk / process | Controlled Windows API inputs through the native adapter | Pending native Windows worker; adapter rejects execution on Linux |

Controlled acceptance does not establish an AWS IAM policy, Kubernetes authorization policy or native Windows installation. The fixtures exercise SDK transport/contracts and the real persistence, activation, alert and UI paths. Genuine provider gates remain explicitly pending.

## Reproduce the controlled gate

Requires Docker, Python 3.12, Node 24, OpenSSL and Chromium/Playwright. Ports 15432, 18000, 18443 and 15173 must be free. From the repository root:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements-providers.txt -r backend/requirements-hosts.txt
npm ci --prefix frontend
npm install --prefix /tmp/opscontrol-infra-browser playwright@1.56.1
/tmp/opscontrol-infra-browser/node_modules/.bin/playwright install chromium
PLAYWRIGHT_MODULE=/tmp/opscontrol-infra-browser/node_modules/playwright/index.mjs \
  backend/.venv/bin/python scripts/infrastructure-acceptance.py
```

For an installed system Chromium, additionally set `PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium`. The runner creates its own PostgreSQL container/database, random passwords and fixture token, trusted ephemeral TLS certificate and protected temporary directory. It ignores ambient AWS credentials in controlled subprocesses. It never provisions cloud resources. Database and service cleanup only targets resources created by that run; private logs remain under the printed temporary path on failure, while successful runs remove ephemeral secrets. Set `INFRA_EVIDENCE_DIR` to write browser/report artifacts outside the default documentation directory.

The gate checks migrations up/down/up, authenticated discovery/import and repeat import, versioned activation/reapply, six monitored resources, health → failure → recovery, sanitized scoped evidence, latest metrics, one stable alert per resource, stale observations returning UNKNOWN, cross-tenant API/browser isolation, local-worker activation authorization, controlled Kubernetes read boundaries, existing authentication negatives and security hardening checks. Screenshots come from actual Playwright sessions without injected tokens or mocked browser API responses.

| Phase | Browser artifact |
|---|---|
| Active, no collected observations | [Configured](screenshots/infrastructure/configured.png) |
| Healthy telemetry | [Healthy](screenshots/infrastructure/healthy.png) |
| CPU threshold, workload readiness/pressure and actual Linux process failure | [Failed](screenshots/infrastructure/failed.png) |
| Same alerts resolved on recovery | [Recovered](screenshots/infrastructure/recovered.png) |
| Other organization has no infrastructure resources | [Other tenant](screenshots/infrastructure/other-tenant.png) |

[Structured runtime evidence](screenshots/infrastructure/report.json) records provider origins, observed metrics, evidence and alert timestamps. The [CI workflow](../.github/workflows/infrastructure-acceptance.yml) repeats these checks; remote CI status is pending until a run exists.

## Deployment and architecture

`LINUX_HOST` and `WINDOWS_HOST` report the machine running the local collector worker. Deploy a worker in the intended host environment with the optional host dependencies; a central Linux worker cannot monitor a remote Windows host. Process selectors are numeric PIDs, so operators must update activation when a supervised process changes PID. No arbitrary command or remote shell is accepted.

AWS uses deployed workload identity and checks the expected account before discovery/collection. Kubernetes production collection loads only the in-cluster service account, restricts namespace selectors and reads only explicitly approved Node names (`OPSCONTROL_K8S_ALLOWED_NODES`). Node access requires a separate ClusterRole with `get`, fixed `resourceNames`, and no cluster-wide Node list permission. Disk selectors must match `OPSCONTROL_HOST_ALLOWED_DISKS` (defaults `/` on Linux and `C:\` on Windows).

Infrastructure activation requires a platform administrator because a local worker uses deployment-level identity. Organization administrators can prepare sources and versions. Platform administrators approve discovery/import as well as activation, because the SDK uses deployment-level identity rather than a distinct identity for each tenant. The generic Collector API cannot enable or reconfigure infrastructure collection without platform authorization. HTTP keeps its organization-scoped remote-worker execution path. The remote HTTP agent cannot execute infrastructure tasks.

Activation produces provider-compatible GAUGE metrics and Alert Rules; incompatible rules, LOG rules, arbitrary provider endpoints and inline credentials are rejected. The scheduler writes a CollectorRun, one sanitized InfrastructureEvidence row, available native MetricSamples and alert evaluations in the existing transaction. Unavailable measurements remain absent. The VM Health API/UI shows freshness, collector errors, metrics, alerts and operational history; no observations or expired observations render UNKNOWN. Overview derives its infrastructure KPI from the same scoped API. A single local scheduler is required; multi-host routing/leases are follow-up work. Inventory connections without active collectors render DISABLED.

The inventory API currently returns at most 200 resources by default (maximum 500); KPI counts cover that returned page. Per-resource reads are bounded by inventory size but query each metric/evidence history; large-fleet pagination/query optimization is follow-up work.

## What to provide for genuine AWS acceptance

1. Approved 12-digit sandbox account ID.
2. AWS region (for example `ap-south-1`).
3. Existing running EC2 instance ID with recent CloudWatch CPU datapoints.
4. Read-only workload identity/role ARN and secure access configuration. Required actions: `sts:GetCallerIdentity`, `ec2:DescribeInstances`, `ec2:DescribeInstanceStatus`, `cloudwatch:GetMetricStatistics`.
5. Temporary STS credentials or workload identity configured securely in environment/CI settings. Do not paste secret keys or session tokens into chat or repository files.

Run from `backend` with temporary STS identity:

```bash
.venv/bin/python -m scripts.aws_live_acceptance \
  --region APPROVED_REGION --account APPROVED_ACCOUNT --instance-id APPROVED_INSTANCE \
  --evidence-output /tmp/aws-approved-evidence.json
```

This read-only gate requires the approved instance to be discovered and CPU evidence to exist. A passed gate produces a separate `GENUINE_AWS_SANDBOX` report. Kubernetes genuine acceptance uses [the disposable provider script](../scripts/verify-kubernetes-provider.sh), now authenticating SDK reads with its restricted service account and checking approved Node reads plus denied secrets, mutation and cross-namespace access. It must run on a host able to start a cluster.

## Completion ledger

Local controlled runtime/browser/security checks and frontend/backend checks are recorded with the current implementation. PR publication, independent review, merge and remote CI are separate repository actions; no reviewed/merged status is inferred from local tests. Genuine AWS, Kubernetes and Windows acceptance and production rollout remain pending their approved environments.

## Local validation record — 2026-10-11

| Check | Result |
|---|---|
| Controlled lifecycle | PASS: 6 resources × 3 phases = 18 infrastructure observations; 18 metric samples per phase; 6 alerts open on failure and the same alerts resolve on recovery |
| Browser | PASS: actual login, provider/search/health filters, Linux evidence drill-down, OPEN/RESOLVED states, second-tenant empty view and five screenshots; no page errors |
| Authorization | PASS: anonymous/cross-tenant denial, viewer write denial, tenant administrator denied shared-identity discovery/local activation, generic collector creation/reconfiguration bypass denied |
| Freshness and evidence | PASS: stale observations return UNKNOWN, missing evidence remains unknown, credentials excluded from persisted payload |
| Migration | PASS: disposable PostgreSQL upgrade through 0019, downgrade to 0018, upgrade to 0019 |
| Backend | PASS: infrastructure boundaries, EC2/Kubernetes/Carte provider units, Linux/Apache/Tomcat adapter units, remote egress negatives, authentication tenant negatives and security release negatives |
| Frontend | PASS: Vite production build and actual infrastructure/HTTP Playwright checks |
| Sprint 1 regression | PASS: actual TLS HTTP 200 → 503 → 200, native evidence, same alert recovery, tenant/audit/egress negatives and five Playwright captures |
| Genuine providers / remote CI / independent review / merge | PENDING |

Migration 0019 backfills the discovery identity of legacy generated inventory still named by its external ID. Previously renamed legacy inventory needs explicit reconciliation before reimport; the migration cannot infer a lost identity from arbitrary display text. New imports retain identity through renaming.
