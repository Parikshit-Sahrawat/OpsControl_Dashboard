# Secure Remote Monitoring — Agent Quickstart (HTTP Probe MVP)

**Status:** Feature branch `feat/secure-remote-collector-protocol`, [draft PR #20](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/20). This is an independently deployable HTTP(S) protocol prototype, **not approved for Internet-facing production use**. It does not implement privileged network discovery, a credential vault, browser synthetics, remote shell or arbitrary scripts.

## How it works

```text
             PUBLIC / MANAGEMENT NETWORK          CUSTOMER PRIVATE NETWORK
          OpsControl API + PostgreSQL               private application
          (no inbound access to app)               HTTPS port 443
                       ^                                  ^
                       | outbound TLS to API              | authorized local HTTPS
                       |                                  |
                   Remote Agent ---------------------------+
                (operator-installed)
```

A platform administrator creates an **organization-scoped worker identity**. Its token is not a user login token. The administrator approves **exact destination hostnames** and **CIDRs**, assigns a supported HTTP collector, and starts the control-plane scheduler. A private agent independently enforces **locally installed** allowlists, polls for a leased job, checks every DNS answer, connects to a pinned approved IP with TLS hostname validation, and sends **only** sanitized HTTP outcome/timings. It does **not** send response bodies, cookies, auth tokens, headers, rendered pages or arbitrary logs.

### Concepts and guarantees

- **Assignment:** an admin explicitly binds a collector to one worker. Unassignment disables the collector and cancels queued/leased jobs. A remote-bound collector is excluded from the legacy local collector scheduler.
- **Dispatch:** `python -m scripts.run_remote_scheduler` selects enabled due collectors with PostgreSQL row locks. It writes durable per-organization jobs and advances `next_run_at`; multiple scheduler processes can coordinate via row locks.
- **Claim:** `POST /api/v1/worker/claim` requires worker bearer token; only assigned organization-matching jobs can be claimed. Exclusive job locks, random lease nonce and a **90-second** deadline fence retries (maximum 3 attempts).
- **Ingestion:** `POST /api/v1/worker/results` requires worker token, matching organization/collector/assignment/lease nonce and UTC timestamp within ±5 minutes. Payload is schema-limited (outcome/status/duration/bytes). Each job accepts exactly one result; repeated identical event id returns an idempotent ACK and conflicting replay returns 409. Writes a CollectorRun, and existing compatible `probe_up` or `http_response_time_ms` metric definitions receive a sample.
- **Egress:** HTTPS only, port 443, GET only, exact host allowlist, approved CIDR allowlist (including specifically authorized private networks), DNS A/AAAA verification, IP-pinned connection and TLS hostname verification. Redirects are **not** followed. Raw URL userinfo, query parameters, embedded secrets, link-local, metadata, loopback, unsupported ports, oversized paths and raw control bytes are denied.
- **Failure/unknown:** an exhausted lease is `EXPIRED`, and invalid runner/credential state is a monitoring error. Missing monitoring evidence must **not** be presented as evidence that the application is healthy.

## Local setup

Follow the regular [OpsControl Quickstart](QUICKSTART.md) for database, backend and frontend setup. Update to the draft PR branch; do not use production/customer credentials or real internal URLs for development.

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
# admin user already created via: python -m scripts.create_admin --username admin
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

A platform administrator can use a secure API client or development-only OpenAPI UI to create an organization, an HTTP data source and an HTTP collector. The collector must be `collector_type: "HTTP"` and have a configuration like:

```json
{
  "name": "Synthetic private portal readiness",
  "collector_type": "HTTP",
  "data_source_id": "<example-source-uuid>",
  "enabled": true,
  "interval_seconds": 60,
  "configuration": {
    "url": "https://portal.example.test/ready",
    "expected_status": 200,
    "timeout_seconds": 8
  }
}
```

Do not attach a real server until the network policy, credential management and deployment security have been reviewed. The hostname `portal.example.test` is **fictional** and will not resolve in the public Internet.

### Enrollment and policy

After an admin logs in using `POST /api/v1/auth/login`, supply the bearer token to your protected API client, **not** in a pasted/public shell command. Create a worker with:

```http
POST /api/v1/auth/workers
Content-Type: application/json
Authorization: Bearer <admin bearer token>

{"organization_id":"<org-uuid>","name":"sample-private-network-runner","expires_in_days":30}
```

The response contains a **one-time** `worker_token`. Save it in your platform secret store or OS-protected file. OpsControl stores only its SHA-256 digest. Never commit the token or log it.

Approve the host and its actual **network-local subnet**:

```http
PUT /api/v1/remote-probes/workers/<worker-uuid>/network-policy
Authorization: Bearer <admin bearer token>
Content-Type: application/json

{"allowed_hosts":["portal.example.test"],"allowed_cidrs":["10.20.0.0/16"]}
```

Assign:

```http
PUT /api/v1/remote-probes/collectors/<collector-uuid>/assignment
Authorization: Bearer <admin bearer token>
Content-Type: application/json

{"worker_id":"<worker-uuid>"}
```

On the trusted control-plane host, run the **remote scheduler process** in its own managed service:

```bash
cd backend
source .venv/bin/activate
python -m scripts.run_remote_scheduler
```

The worker's first scheduled job will be queued. An administrator can also request a single job with `POST /api/v1/remote-probes/jobs` using `collector_id`, `worker_id` and a unique `idempotency_key` UUID.

### Deploy the private-network agent

Install OpsControl source and backend requirements on a hardened, unprivileged machine/container inside the **approved private network**. Its egress firewall must allow **only** the control-plane HTTPS endpoint and the approved target addresses/port 443; deny cloud metadata and unrelated networks at the OS/network layer. Do not expose an inbound port. Give the runner the platform trusted CA for internal TLS endpoints; do not disable certificate verification.

Read the worker secret at runtime from an OS-protected secret source. This example illustrates environment variable names and must not be committed with real values:

```bash
cd backend
source .venv/bin/activate
export OPSCONTROL_SERVER_URL=https://opscontrol.example.test
export OPSCONTROL_ALLOWED_HOSTS=portal.example.test
export OPSCONTROL_ALLOWED_CIDRS=10.20.0.0/16
# Inject OPSCONTROL_WORKER_TOKEN securely from your deployment secret manager.
python -m scripts.run_remote_agent
```

The agent continuously polls over outbound TLS. Its **own** exact host/CIDR configuration is mandatory and cannot be broadened by a remote job, protecting against central misconfiguration. The control plane never needs a route into the private LAN.

For a local-only API prototype on `http://127.0.0.1:8000`, `OPSCONTROL_ALLOW_INSECURE_CONTROL_PLANE=1` temporarily allows the **control plane** to use loopback HTTP, never the monitored destination; this must not be used for real infrastructure.

### Verification (disposable, synthetic)

```bash
cd backend
python scripts/test_remote_egress.py
# Staging CI launches PostgreSQL/API and runs:
python scripts/remote_protocol_probe.py
```

The negative suite covers: human/worker token separation; anonymous and viewer denial; org mismatch; policy-validation denial; one-time assignment; due scheduling; queue idempotence; leased claim; cross-tenant result rejection; nonce and timestamp rejection; oversized/secret-bearing schema rejection; replay conflict; one CollectorRun/MetricSample; revocation; DNS rebinding/mixed answers; metadata/link-local/loopback IPs; and request-target injection.

## Non-goals and production security gate

1. Agent TLS and policy safeguards do not replace **network firewall/eBPF/container egress enforcement** or a host process confinement profile. A compromised agent cannot be contained by its own Python checks alone.
2. The MVP checks unauthenticated HTTPS GET and exact HTTP status; application login workflows require an explicit credential-provider and synthetic-browser threat-model review before enablement.
3. Initial job dispatch is **pull only** and scoped to HTTP collectors. EC2/Kubernetes/Pentaho/Apache adapters are independent workstreams.
4. Automatic alert-rule evaluation, dashboard integration, full missing-data health transitions, high-availability performance testing, audit review, retention and deployment security require additional release gates; do not call this production-ready because job ingestion works.
5. Existing GitHub [issue #18](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/18) remains the security review/production rollout gate.
