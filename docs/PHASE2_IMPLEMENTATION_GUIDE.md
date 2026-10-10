# OpsControl Phase 2 — Implementation and Verification Guide

**Development branch:** `feat/phase2-activation-provider-integrations` · [Draft PR #21](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/21)

**Status:** Technical preview. Vendor-neutral infrastructure monitoring and independently versioned rules. **No production security sign-off**, no merge to `main`, and no real organizational credentials, customer endpoints or confidential fixtures committed.

## 1. Quick start for a new developer

Prerequisites: Git, Python 3, Docker Engine with Compose and the ability to pull public container images.

```bash
git clone https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard.git
cd OpsControl_Dashboard
git switch feat/phase2-activation-provider-integrations
bash scripts/demo-up.sh
```

The script generates a random local admin password in **`.demo-private/admin-password`** (mode 0600, gitignored), builds PostgreSQL/FastAPI/React containers, applies Alembic migrations and seeds only **fictional** organizations, hosts, sample ETL executions and a disabled HTTP collector. Open `http://127.0.0.1:5173` (localhost **only**), login `demo-admin`, and read the password from the local file. No live infrastructure is contacted by the seed. The database and API are not publicly published; the database remains internal to Docker Compose.

```bash
bash scripts/demo-down.sh
```

The demo database volume is preserved by default. If intentionally clearing disposable demo data: `docker compose -f docker-compose.demo.yml down --volumes`. Do **not** use this Compose profile or its illustrative database password on an external network.

## 2. Operator journey: Independent Rule Catalog → Activation → Evidence

1. In **Resource Management**, create an authorized organization and HTTPS Data Source; no monitoring is active merely because the Data Source exists.
2. Install a private-network agent from [Remote Agent Quickstart](REMOTE_AGENT_QUICKSTART.md); its platform-admin-issued worker token is scoped to one organization. Approve its **exact hostname** and **specific CIDR**. Also deploy and **verify actual OS/CNI egress restrictions**.
3. Navigate **Monitoring Setup**, choose the organization, HTTPS Data Source and its approved worker.
4. Create independent, immutable-version **Metric Rules** (e.g. `probe_up`), **Log Rules** (`HTTP` structured events) and **Alert Rules** (`probe_up LT 0.5`). Alternatively attach legacy template bundles containing supported HTTP metric/log/alert definitions.
5. Select pinned rule versions and click **Validate & Preview**. The preview validates rule compatibility, tenant/worker policies, source and collector configuration without altering live state.
6. Click **Activate monitoring**. The idempotent reconciler materializes an enabled remote HTTP collector, metric definitions, structured log sources and matching alert rules. Reapplying an identical plan does not create duplicates. Source health remains unknown before fresh results arrive.
7. Run the remote scheduler: `cd backend && python -m scripts.run_remote_scheduler`. The approved agent claims a scheduled job; it executes a read-only pinned-IP TLS GET and submits sanitized results. The backend stores CollectorRun, MetricSample and LogEvent and evaluates Alert Rules.
8. Review the collector evidence via Monitoring API and configured alerts. **Deactivate** cancels queued/leased jobs, disables generated rules and worker assignment while retaining historical evidence.

**Current supported activation:** remote **HTTP/HTTPS GET, expected status and response time**, with structurally bounded operational events. Complex assertions, authenticated browser synthetic journeys and secret-backed HTTP probes are future increments. Unsupported templates/providers fail validation and must never be reported healthy.

**API surface:**
- `POST /api/v1/rule-catalogs`, `GET /api/v1/rule-catalogs`, `POST /api/v1/rule-catalogs/{id}/versions`
- `POST /api/v1/data-sources/{id}/activation-preview`
- `POST /api/v1/data-sources/{id}/activations`
- `GET /api/v1/data-sources/{id}/activation`
- `POST /api/v1/data-sources/{id}/deactivation`
- `GET /api/v1/remote-probes/workers?organization_id=...`

## 3. AWS EC2 monitoring and inventory

**Adapter:** `AWS_EC2` (`EC2` alias) in the existing local collector worker. Uses the AWS SDK's **default workload IAM credential chain**. No static access keys, arbitrary endpoint overrides, cross-account AssumeRole or caller-supplied IAM profiles.

Sample collector `configuration`:

```json
{"region":"ap-south-1","account_id":"123456789012","instance_id":"i-0123456789abcdef0"}
```

The adapter verifies caller identity matches the expected AWS account, performs **read-only** `DescribeInstances`, `DescribeInstanceStatus` and `CloudWatch:GetMetricStatistics`, and returns instance lifecycle, instance/system check states and CPU utilization when available. **No CPU datapoint means unknown CPU, not 0%**. Memory/disk usage is not present without a separately authorized agent.

**Inventory:** Create a source `source_type=AWS_EC2` with `connection_config={"region":"ap-south-1","account_id":"123456789012"}`. An authorized org admin may call `POST /api/v1/resource-discovery/sources/{source_id}/scan` to view sanitized candidates. Explicit `POST .../import` with `approved_external_ids` and `dry_run=false` imports a candidate as a **disabled** monitoring collector, never as healthy or active. Inventory reads at most 100 candidates per scan in this initial preview; pagination beyond that is not yet complete.

Least-privilege example AWS IAM permissions (scope account and regions through deployment and AWS Organizations policies):

```json
{
  "Version":"2012-10-17",
  "Statement":[{
    "Effect":"Allow",
    "Action":["sts:GetCallerIdentity","ec2:DescribeInstances",
              "ec2:DescribeInstanceStatus","cloudwatch:GetMetricStatistics"],
    "Resource":"*"
  }]
}
```

These Describe/CloudWatch APIs often require `Resource:"*"`; compensate with scoped workload identities and organizational guardrails. **Do not attach administrator policies or grant EC2 write APIs.**

## 4. Kubernetes Pods and Deployments

**Adapter:** `KUBERNETES` (`K8S` alias). Uses in-cluster service-account credentials only, no arbitrary kubeconfig or caller-defined cluster URL. Supports a single authorized namespace and a named Pod/Deployment per collector.

```json
{"namespace":"demo","pod_name":"web-0"}
```

or

```json
{"namespace":"demo","deployment_name":"frontend"}
```

It reports Pod phase, Ready condition, restarts/waiting reasons, or Deployment available/desired replicas. It does not infer working application HTTP health from Kubernetes readiness.

**Discovery:** a source with `source_type=KUBERNETES` and `connection_config={"namespace":"demo"}` can list up to 100 Pod candidates through the authorized service account. Import requires manual selection and produces a disabled collector.

Deploy the worker into the approved namespace using Kubernetes RBAC granting only `get,list` of Pods and `get` of Deployments. For example:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata: {name: opscontrol-read-only, namespace: demo}
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get","list"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get"]
```

Bind this Role only to the specific collector service account in that namespace. Do not grant cluster-admin or unrestricted cross-namespace visibility.

## 5. Pentaho Carte — read-only ETL execution collection

**Adapter:** `PENTAHO`, using the local/approved private-network worker and the pinned-TLS transport.

```json
{
  "url":"https://carte.example.test",
  "job_name":"Example Scheduled ETL",
  "execution_id":"example-execution-001",
  "job_order_id":"<fictional-registered-job-uuid>",
  "credential_ref":"demo_readonly",
  "allowed_hosts":["carte.example.test"],
  "allowed_cidrs":["10.20.0.0/16"]
}
```

Set **independent local worker egress limits** via `OPSCONTROL_LOCAL_ALLOWED_HOSTS` and `OPSCONTROL_LOCAL_ALLOWED_CIDRS`. The adapter only makes a GET to **`/kettle/jobStatus/`** with encoded job name/id and `xml=Y`, verifies all DNS answers and TLS, refuses redirects and reads at most 64 KiB XML with DTD/entities disallowed. It accepts Basic credentials only from `credential_ref` via the local resolver (environment-backed preview; replace with Vault/secret provider for production). No job launch/stop/kill routes are exposed.

Status is normalized into RUNNING/SUCCESS/FAILED/NO_RESPONSE, and saved into `JobOrderHistory` once per stable provider execution ID. Repeated checks update the same record, not create fabricated repeated runs; monitoring transport outages are recorded against **collector health**, not forged as a Pentaho failed execution. Observation time is labeled as detection/end observation—not falsely claimed as a precise Pentaho source start/end timestamp. Automated NO_RUN schedule evaluation remains a separate milestone.

**Pentaho limitation:** only existing/exact Carte execution identities are polled; comprehensive server-wide job discovery, recurring execution-ID rollover, new-job registration and production credential handling require further work. The functional read-only status adapter and history persistence are testable with synthetic XML.

## 6. Network egress verification

- **Python policy tests:** `python backend/scripts/test_remote_egress.py` validates metadata denial, mixed A/AAAA DNS, loopback, raw URL bytes, invalid CIDRs and local policy overlays without using the network.
- **Actual Docker network enforcement test:** `bash scripts/verify-firewall-docker.sh`. Builds two isolated internal bridge networks and asserts approved peer TCP succeeds while forbidden peer/external egress fails. Executed in [Network-Layer Egress Firewall Test](../.github/workflows/egress-firewall-smoke.yml).
- **Actual CNI enforcement test:** `bash scripts/verify-cni-egress.sh` against an **authorized test Kubernetes cluster** with enforcing NetworkPolicy CNI. Creates a disposable namespace, three Pods and temporary NetworkPolicy; confirms approved TCP succeeds and denied TCP cannot connect, then deletes namespace. **Not yet claimed passing on the user's cluster.**
- **Example deployment policy:** [remote-agent-networkpolicy.yaml](../deploy/examples/remote-agent-networkpolicy.yaml); placeholders must be changed and the CNI must actually implement NetworkPolicy semantics.

A passing Docker isolation test does **not** prove that Kubernetes NetworkPolicy works in a specific target cluster, that Pod DNS is correctly restricted, or that the Python process cannot bypass its own allowlist when compromised. These require deployment-specific review.

## 7. Verification and commands

```bash
cd backend
python scripts/provider_unit_probe.py
python scripts/test_remote_egress.py
# The following are CI integration tests requiring a disposable migrated PostgreSQL,
# seeded fixture accounts and running FastAPI:
python scripts/auth_tenant_probe.py
python scripts/remote_protocol_probe.py
python scripts/phase2_pentaho_persistence_probe.py
python scripts/phase2_activation_probe.py
```

Other gates: backend Python compilation/SQLAlchemy mapper tests, `npm ci && npm run build`, Playwright authenticated UI, `pip-audit`, `npm audit`, Gitleaks and Docker demo CI. **Never treat skipped or pending tests as passed.**

## 8. Remaining release issues

- Independent security threat-model/authorization review, production secrets-provider integration and rotation, active remote-agent network firewall enforcement on the actual deployment, signed/managed agent rollout.
- AWS real-account IAM-denied/region/pagination and Kubernetes real-cluster RBAC-denied/Pod restart tests (mocked unit tests are not field verification).
- Runtime EC2/K8s onboarding, multi-page discovery, automatic rule activation for non-HTTP adapters, hardened collector scheduling and structured provider error taxonomy.
- Full Pentaho job run discovery, scheduling/NO_RUN and source start/end timestamps from provider data.
- Static frontend CSP and container-vulnerability scan, nonempty upgrade/rollback verification, SLA load tests and organization-scoped retention.

**Approach:** keep separate designed, implemented, CI-verified, deployment-verified and released statuses in [living roadmap](IMPLEMENTATION_ROADMAP.md).
