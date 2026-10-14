# OpsControl OWASP API Security Top 10 verification checklist

This is a project-specific self-audit derived from the **OWASP API Security Top 10 (2023)** risk categories, for an independent reviewer to execute. OWASP's Top 10 is a risk catalog, not a complete official certification checklist. A developer self-audit, passing CI, or owner-approved merge is not an independent production security sign-off.

Source: [official OWASP risk catalog](https://owasp.org/API-Security/editions/2023/0x11-t10/) and [OWASP-maintained source](https://github.com/OWASP/API-Security/blob/33cea37b2ffde3e2e62f6b5d79a029a22a846633/editions/2023/en/0x11-t10.md). Category names were checked against the official source. The cloud proxy denies direct owasp.org access; the official repository was read through GitHub instead.

## Review contract and evidence

Record commit SHA, image digest, environment/ingress configuration, migration head, reviewer, UTC time, case ID, redacted request shape, status/body assertion, affected DB rows and result. Use PASS, FAIL, UNRUN, BLOCKED or justified N/A. Never turn missing production evidence into PASS; preserve failing cases. Do not store passwords, bearer/worker tokens, Authorization headers, secret values, provider response bodies or backup contents in public artifacts.

Use a disposable staging database with two organizations (North/South), one platform administrator, tenant administrators, a viewer, an operator, a mixed-role user and separately assigned workers. The existing test harness provisions these fixtures. Expected 404 responses conceal cross-tenant object existence; a 200 empty collection is appropriate for a filtered list. A 403 is expected for a forbidden function inside visible scope. Denial must leave the target rows unchanged.

The local destructive/mutating probes below are **only** for disposable fixture data. Never point the fixture seeding probes, rollback scripts, deliberate credential lockouts or load loops at the production database. Read-only deployment checks require the actual target URL, approved operator identity and CA trust. No live AWS, ServiceNow or Carte credentials are requested by this checklist.

## Reproducible local commands

Run once per reviewed head from the repository root. Reuse the resulting evidence across cases; do not seed the same fixture database repeatedly.

```bash
set -euo pipefail
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements-providers.txt -r backend/requirements-hosts.txt
npm ci --prefix frontend --no-audit --no-fund
npm run build --prefix frontend
(cd backend && .venv/bin/python -m unittest discover -s tests -v)
(cd backend && .venv/bin/python -m scripts.test_remote_egress)
(cd backend && .venv/bin/python -m scripts.provider_unit_probe)
(cd backend && .venv/bin/python -m scripts.infrastructure_unit_probe)
(cd backend && .venv/bin/python -m scripts.etl_unit_probe)
(cd backend && .venv/bin/python -m scripts.secrets_provider_probe)
# Install browser tools outside application dependencies.
npm install --prefix /tmp/opscontrol-review-tools --no-audit --no-fund playwright@1.56.1
/tmp/opscontrol-review-tools/node_modules/.bin/playwright install --with-deps chromium
export PLAYWRIGHT_MODULE=/tmp/opscontrol-review-tools/node_modules/playwright/index.mjs
# Docker and OpenSSL required. These runners create and clean only their own labs.
RELEASE_BROWSER_ACCEPTANCE=1 RELEASE_EVIDENCE_DIR=/tmp/owasp-release \
  backend/.venv/bin/python scripts/release-acceptance.py
OPSCONTROL_UI_THEME_ACCEPTANCE=1 OPERATIONAL_EVIDENCE_DIR=/tmp/owasp-noc \
  backend/.venv/bin/python scripts/operational-acceptance.py
```

**R1:** focused `unittest` cases. **R2:** release lab (invokes auth, security, deep-tenant, worker, runtime and browser CRUD probes). **R3:** operational lab (incident/ETL/report/mixed-role/browser journeys). **R4:** `test_remote_egress`. **R5:** provider/infrastructure/ETL/secret probes. Counts and outputs must belong to the tested SHA; zero tests do not establish acceptance. Optional genuine-provider workflows are not replaced by mocks.

For the target staging deployment, configure `REVIEW_BASE` as the actual HTTPS ingress URL and `REVIEW_CA` as its approved CA bundle (system public CA trust is also valid). Put review tokens in private 0600 files through your normal operator login flow; do not paste them into this document or command-line arguments. The following helper avoids writing the Authorization value into process arguments:

```bash
export REVIEW_BASE=https://opscontrol.example.test
export REVIEW_CA=/private/approved-ca.pem
export REVIEW_TOKEN_FILE=/private/north-review-token
cat > /tmp/opscontrol-review-request.py <<'PY'
import json, os, ssl, sys, urllib.request, urllib.error
from pathlib import Path
method, path = sys.argv[1:3]
headers = {'Content-Type': 'application/json'}
if os.getenv('REVIEW_TOKEN_FILE'):
    headers['Authorization'] = 'Bearer ' + Path(os.environ['REVIEW_TOKEN_FILE']).read_text().strip()
body = sys.stdin.buffer.read() if method in {'POST', 'PUT', 'PATCH'} else b''
req = urllib.request.Request(os.environ['REVIEW_BASE'].rstrip('/') + path,
    data=body or None, headers=headers, method=method)
ctx = ssl.create_default_context(cafile=os.getenv('REVIEW_CA') or None)
try:
    response = urllib.request.urlopen(req, context=ctx, timeout=15)
except urllib.error.HTTPError as e:
    response = e
with response:
    # Do not print raw bodies: they may contain fixtures, secrets or provider data.
    raw = response.read(1048577)
    try: value = json.loads(raw)
    except (ValueError, UnicodeError): value = None
    print(json.dumps({'status': response.status, 'bytes': len(raw),
      'json_type': type(value).__name__,
      'top_level_keys': sorted(value) if isinstance(value, dict) else [],
      'retry_after': response.headers.get('Retry-After')}))
PY
```

For case-specific requests below, replace IDs with known fixture identifiers, switch `REVIEW_TOKEN_FILE` to the named role, and inspect the JSON/DB assertion inside private review tooling. The helper deliberately emits only sanitized metadata; seeing an expected status alone does not prove the no-change/no-disclosure assertions.

## API1:2023 — Broken Object Level Authorization

| Case | Exact steps | Expected result and evidence |
|---|---|---|
| A1.1 Direct and nested reads | Run R2. `deep_tenant_security_probe.main` uses North token to GET South `/api/v1/monitoring/{metrics,logs,alert-rules,alerts}/{id}`, metric `/samples`, log `/events` and alert `/notifications`. Repeat target staging using known South IDs. | Every direct/nested foreign object is 404; no South fields in body. Same North object is 200; a nonexistent ID is also 404. |
| A1.2 Cross-org lists/query filters | Run R2/R3. As North request `/api/v1/operations/incidents?organization_id=SOUTH_ID`, `/reports?organization_id=SOUTH_ID`, `/api/v1/infrastructure/resources?organization_id=SOUTH_ID` and resource collector list for South source. | Empty foreign results, no foreign totals/metrics/summary evidence. Platform-admin visibility is an explicit separate positive control. |
| A1.3 Foreign-key and ownership writes | Run R2. POST North metric with South source, North alert rule with South metric; PATCH existing North ownership fields to South. | Foreign reference 404/409; ownership reassignment 403 where prohibited; rollback preserves source ownership and referenced rows. |
| A1.4 Browser scope races | Run R3: delay old-scope response, switch authorized organizations and open incident/execution investigation. | Old response cannot reappear under new scope; foreign historical evidence cannot be opened. Capture browser and DB/API assertions. |

Private staging example: `python /tmp/opscontrol-review-request.py GET /api/v1/monitoring/metrics/SOUTH_METRIC_ID`; then PATCH the same object with `{"name":"cross-tenant-negative"}`. Inspect the original row afterward. Existing controlled evidence covers these paths; all newly inventoried object routes still require an independent exhaustive review.

## API2:2023 — Broken Authentication

| Case | Exact steps | Expected result and evidence |
|---|---|---|
| A2.1 Missing/invalid credentials | R2; GET `/api/v1/auth/me` with no header, malformed header and `synthetic-wrong-token`. Then use valid North token. | Negatives 401, WWW-Authenticate where human middleware applies; positive 200. Token/password never appear in error or audit output. |
| A2.2 Session lifecycle | R2; login disposable user, change membership role/remove membership, reset password and disable user. After each action replay old token; separately login/logout and replay token. Set a fixture AccessSession expiry in the past, then replay. | Revoked/expired/logged-out tokens return 401; old password and disabled account cannot login. Persisted token is a digest, not plaintext. Expiry/logout cases not exercised by a chosen runner must remain UNRUN. |
| A2.3 Login throttling | R2: ten wrong-password attempts for disposable account return 401, eleventh returns 429 with Retry-After=900. Repeat through two replicas; separately test 30 direct-client-IP failures in a new fixture. | Shared PostgreSQL bucket enforces policy across replicas; another valid session is unaffected. IP/replica variant needs deployed evidence; reset only disposable buckets. |
| A2.4 Human/worker separation | R2; human bearer POST worker claim and worker bearer GET human `/auth/me`; revoke/expire worker then claim/heartbeat. | Human token on worker API and worker token on human API return 401; revoked/expired worker cannot ingest or update liveness. |
| A2.5 Password/token storage and recovery | Read `security/passwords.py`, sessions and workers with restricted reviewer SQL; inspect password hashes and token digests without exporting values. Check reset/user creation boundaries (12..1024 chars). | Salted PBKDF2-HMAC-SHA256, constant-time verification, opaque random tokens, no stored raw tokens/passwords; 11-char user creation 422. MFA/SSO acceptance is pending if required by deployment policy. |

JWT `alg=none` tests are N/A for the current opaque-token design, with the reason recorded. They become required if JWT authentication is introduced.

## API3:2023 — Broken Object Property Level Authorization

| Case | Exact steps | Expected result and evidence |
|---|---|---|
| A3.1 Forbidden input properties | R2; viewer/org-admin sends `platform_admin`, `organization_id`, `data_source_id`, `remote_worker_id`, actor/status overrides to routes whose schema excludes those fields. Record schema disposition and compare persisted row/authorization before and after. | Privilege/ownership must not change. Strict schemas return 422; schemas that ignore unknown fields may return normal status but ignored fields remain unchanged. Do not count a harmless 200 as unauthorized mutation. |
| A3.2 Secret input and legacy output | R1/R2: nested password keys and mixed-case HTTPS URL userinfo must be rejected. Seed legacy credentials in disposable DB, then read every source/config/rule endpoint. | 422 without rejected secret in error; legacy values/URL credentials redacted. Worker claim exposes an approved reference only, never the resolved username/password. Basic jobs reject anonymous-only result markers. |
| A3.3 Worker result projection | R2: submit `response_body`, arbitrary headers, fake actor and unsupported result properties; submit valid bounded evidence. | 422 for forbidden result fields; accepted evidence contains only declared native facts. DB sample/event IDs match authenticated worker job and server-linked organization. |
| A3.4 Report/evidence serialization | R3; export reports and drill down collector/ETL incidents; search outputs for fixture secret markers and unrelated-tenant IDs. | No passwords, tokens, raw transport response bodies or unrelated-tenant data in report/export/evidence. Inventory additional serializers independently. |

## API4:2023 — Unrestricted Resource Consumption

| Case | Exact steps | Expected result and evidence |
|---|---|---|
| A4.1 Bounds and body size | R2 automatically tests worker claim >8192-byte JSON (413). Additionally test missing Content-Length on the direct disposable ASGI/API (411) and non-JSON type (415). An ingress may buffer/dechunk and add Content-Length; verify its streaming size policy separately. At real ingress POST a generated 1,048,577-byte body; test chunked transfer separately. | Ingress 1 MiB limit enforces 413 including chunked bodies. App worker size checks alone are not proof of general/streaming limits. Capture upstream request count to prove rejection before expensive work. |
| A4.2 Query/config limits | Authenticated GET `/api/v1/operations/services?limit=501`, `/reports?days=91`, `/api/v1/infrastructure/resources?limit=501`; POST >100 activation rule versions; malformed UUID/NaN/infinity threshold. | 422; no 500, no work beyond validated bounds. Existing list pagination defaults are not complete-fleet aggregation. |
| A4.3 Collector admission/pool recovery | R2 runtime probe: eight controlled collectors, capacity two, six concurrent calls for one collector; run another process and kill lock owner. | Peak active <=2, only one competing run persists, process death releases lock and a fresh run succeeds; no unbounded pending queue. |
| A4.4 Deployed quotas and overload | On an approved staging replica set define request rate, concurrency, duration, tenant quota and p95/error budget **before testing**. Drive authenticated report/login/job-creation workloads, including valid-password CPU cost and long-running providers. Record per-tenant queued jobs, DB connections, RSS/CPU and other tenant latency. | Meets recorded budgets, bounded queue/cost, fair recovery and no unauthorized writes. Currently needs target-scale evidence; absence of general rate/quota enforcement must be a finding, not PASS. |
| A4.5 Retention/recovery | R2 custom dump/restore and bounded prune rollback/apply; inspect pinned evidence and immutable audit. | Complete row/constraint preservation; maintenance bounded, linked evidence retained, audit unchanged. Production-sized backup RTO/RPO and approved historic archive remain pending. |

Oversized ingress test (dummy data only): `python -c 'import sys; sys.stdout.write("x"*1048577)' | python /tmp/opscontrol-review-request.py POST /api/v1/worker/claim`. It is a test of ingress size, not a valid JSON request or authentication test.

## API5:2023 — Broken Function Level Authorization

| Case | Exact steps | Expected result and evidence |
|---|---|---|
| A5.1 Platform functions | R2: viewer/operator/org-admin call GET `/auth/users`, `/auth/audit`, POST `/auth/workers`, remote assignment/network-policy/job administration, global template writes and provider discovery. Repeat with platform admin positive control. | Forbidden platform functions 403 (or 401 if wrong identity class); platform-admin positive control succeeds within approved configuration. |
| A5.2 Monitoring mutation | R2/R3: viewer POST metric, rule or source; org-admin modifies foreign scope; org-admin enables/mutates legacy local API/infrastructure collector. | Viewer 403; foreign object 404; local network/provider authority requires platform administrator. Registration-only disabled OTEL is not collection authority. |
| A5.3 Operator incident scope | R3: authorized operator acknowledges/investigates/notes a visible incident; viewer repeats same request; mixed operator/viewer user mutates viewer-only organization. | Operator succeeds in permitted org; viewer/mixed foreign role 403; actor is server-authenticated. |
| A5.4 Last administrator/concurrency | R2 concurrently disables two active platform admins in different threads. | One 200, one 409; at least one active admin remains. Record DB count and transaction lock evidence. |

Use the same method/path/body with each role, including PUT/PATCH/DELETE and nested routes. Hiding a button is not authorization.

## API6:2023 — Unrestricted Access to Sensitive Business Flows

| Case | Exact steps | Expected result and evidence |
|---|---|---|
| A6.1 Repeated activation/jobs | HTTP golden path/activation probe: preview/apply/reapply pinned versions; R2 queue same idempotency key twice, then attempt a second outstanding job with a different key. | Reapply does not duplicate active generated resources; same job key returns duplicate=true; at most one outstanding collector job. No extra sample/alert is created by replay. |
| A6.2 Evidence replay/fencing | R2: other worker submits result, incorrect/expired lease nonce, stale timestamp, same event twice and different event for completed job. | Foreign worker 404; nonce/conflict 409; stale observation 422; valid duplicate 202 duplicate=true, exactly one evidence/run/sample. |
| A6.3 Incident/recovery transitions | R3: attempt resolve while condition ACTIVE, record recovery then resolve; relapse and duplicate acknowledgment/transition. | Active resolution 409; valid recovered lifecycle retains evidence/activity; relapse creates the intended episode, not fabricated recovery. |
| A6.4 High-volume authorized automation | In approved staging repeatedly create workers/rules, enqueue jobs, submit notes and request reports at agreed per-tenant rates. Count DB/audit/notification growth and provider cost; verify tenant ceilings and alert delivery dedup. | Bounded business cost and permitted workflow volume, not merely authenticated traffic. Tenant/business-flow quotas and legacy investigation/template race coverage remain production gaps until tested/fixed. |

## API7:2023 — Server Side Request Forgery

| Case | Exact steps | Expected result and evidence |
|---|---|---|
| A7.1 URL and address denial | R4 exercises http, unapproved host/port, URL userinfo, token query, CRLF, wildcard host, broad CIDR, loopback, link-local, metadata and IPv4-mapped IPv6. | EgressDenied before packet/credential retrieval. Tests are offline; no request to a real metadata service is sent. |
| A7.2 Rebinding/policy intersection | R4 fake DNS returns approved private + forbidden public address; server job widens hostname/CIDR beyond worker-installed policy. | Entire unsafe answer/policy denied, no new destination used; successful permitted probe uses pinned address and verified hostname. |
| A7.3 Redirect/credentials | Controlled HTTPS fixture returns 302 to a second fixture; capture requests at both. Repeat authenticated Basic probe and notification provider call. | No redirect is followed; no Authorization crosses origin; missing approved reference denies before secret lookup/network. New integration transports require their own tests. |
| A7.4 Network-layer enforcement | Execute repository `scripts/verify-firewall-docker.sh` in its documented disposable Docker lab and the kind/Calico workflow; repeat `scripts/verify-cni-egress.sh` in approved target namespace. | Allowed fixture reachable, denied fixture/public egress blocked by actual enforcement. Worker Python validation does not establish production firewall/CNI acceptance. |
| A7.5 Provider control-plane boundaries | R5 rejects EC2 endpoint/access-key overrides and K8s external server/kubeconfig; EKS discovery validates expected workload account and explicit region. Review SMTP/ServiceNow URL settings as privileged deployment config. | Untrusted source configuration cannot choose arbitrary provider endpoints/credentials or widen namespace/node policy. Actual workload IAM/CNI/secret allowlist remains a deployed test. |

## API8:2023 — Security Misconfiguration

| Case | Exact steps | Expected result and evidence |
|---|---|---|
| A8.1 HTTPS/proxy trust | R1 rejects wildcard/unbounded/hostname trusted-proxy settings. R2 real TLS ingress with trusted CA; direct untrusted request sends forged X-Forwarded-Proto=https and X-Forwarded-For. | Actual TLS succeeds; untrusted direct request is 403; supported production entrypoint rejects empty/wildcard trust. Verify private API port and unknown Host rejection in real deployment. |
| A8.2 Static SPA/API headers | R2 fetches actual TLS SPA and API; inspect CSP/HSTS/nosniff/frame/referrer/cache headers. Build script hash must match exact inline theme bootstrap. | SPA script-src allows self and matching hashes, not unsafe-inline; API CSP restrictive; HSTS max-age=31536000; no-store, DENY, nosniff. Style unsafe-inline is an explicit current UI exception. Test actual production browser boot independently. |
| A8.3 CORS/methods | R2 OPTIONS approved origin PUT/PATCH, unapproved origin PUT, approved origin TRACE; then send a real unauthorized mutation with spoofed Origin. | Approved 200 with exact allow-origin; unapproved/method 400; no wildcard credential sharing. Actual request remains 401/403 without permission. |
| A8.4 Runtime DB/config | R1 .env-only production denies environment credentials and misspelled environment fails validation. R2 app role attempts audit UPDATE and DDL, then starts as owner; runtime image imported under UID10001/read-only/no network. | Runtime cannot alter audit/schema; owner startup fails; production demo seed off. Production workload secrets, rotation and grants after every migration need target evidence. |
| A8.5 Debug/defaults/supply chain | Inspect production docs/openapi settings; scan deployed files/env *names*, image SBOM/digests, pip/npm advisories and entire Git history. | Swagger/OpenAPI are disabled in production API; edge SPA fallback may return HTML 200 and must not expose schema/debug data. No default credentials/public DB port/secrets in images/artifacts; scans pass on exact reviewed head. |

## API9:2023 — Improper Inventory Management

| Case | Exact steps | Expected result and evidence |
|---|---|---|
| A9.1 Authoritative route inventory | Run the offline export below for the exact head. For every method/path assign owner, identity class, tenant/object/property/function checks, sensitivity and required negative cases; compare against ingress routes and deployed versions. | No orphan/unreviewed routes or undisclosed alternate environments; schema existence is not authorization proof. |
| A9.2 Deprecated and debug routes | With valid review token GET `/api/v0/operations/services`, `/api/v2/operations/services`, removed routes and production API docs paths; probe only approved registered ingress hosts. | Unregistered API versions 404; production API docs absent. Legacy routes still registered are inventoried, not assumed retired. |
| A9.3 Deployment/provider inventory | Compare environment hostnames, ports, worker identities, assigned sources, expected AWS accounts/regions, K8s namespaces and secret references with authorized inventory. | No old unauthenticated/public API/DB endpoint; each worker/source has owner and policy; genuine provider compatibility separately recorded. |
| A9.4 Docs/provenance reconciliation | Compare README/security/roadmap with PR #25/#26 merges and exact CI; reassess all open audit issues, source screenshots, synthetic/live origin and pending release gates. | Stale Forbidden/pending-merge claims superseded by actual evidence; illustrations/mocks do not masquerade as browser/live acceptance. Owner review date/version recorded. |

Offline route inventory (does not connect to DB or expose credentials):

```bash
(cd backend && ENVIRONMENT=development .venv/bin/python -m scripts.export_api_inventory /tmp/opscontrol-api-inventory.json)
```

## API10:2023 — Unsafe Consumption of APIs

| Case | Exact steps | Expected result and evidence |
|---|---|---|
| A10.1 Third-party response validation | R5 Carte XML: malformed XML, DOCTYPE/entity declarations, >64 KiB response, missing execution identity/timing, nonfinite metric and unexpected provider fields. New ServiceNow fixture adds malformed JSON/shape/missing sys_id/oversized response and 4xx/5xx. | Invalid/oversized input rejected without fabricated success/evidence; bounded generic provider failure; no raw provider body in persisted error. |
| A10.2 Provider TLS/redirect/deadline | Controlled providers use trusted fixture cert; repeat bad cert/hostname, redirect and slow response. Record SDK timeout/retry settings and overall polling duration. | Certificate/hostname checks retained, credentials confined to approved origin, finite connection/read bounds. Overall multi-call deadlines/reconnect/failover need separate target acceptance. |
| A10.3 Identity/read-only scope | R5 expected AWS account mismatch; K8s pod/deployment/node selector and allowlist tests; EKS read-only list/describe. Genuine Carte credential review ensures fixed GET-only inventory/status. | No arbitrary endpoint, role switch, static access keys, cluster-wide enumeration or write-capable provider calls. Mock/SDK stub tests are labeled controlled, not genuine-provider acceptance. |
| A10.4 Alert-to-external incident lifecycle | Controlled ServiceNow Table API: consecutive breaches open once, repeat delivery idempotently correlates, recovery updates same incident; inject delivery failure/retry and wrong/missing external reference. | Native alert/incident/evidence persist; one correlated external incident is resolved; wrong provider data does not mark SENT. Use only a fictional fixture unless actual external delivery is explicitly authorized. |
| A10.5 Browser log/provider text | R3 feed/log/step/operator-note text includes HTML/script-like strings from a controlled provider; open investigation and export. | Rendered as text, no browser script execution, bounded logs and redacted credentials; sanitized export preserves provenance. Record UNRUN if payload variant was not actually executed. |

## Production sign-off

- [ ] All inventoried routes have role/object/property negative coverage, with exact reviewed head.
- [ ] Deployed TLS/Host/proxy/private-ingress/CSP/browser and DB capabilities verified.
- [ ] Secret migration/rotation/workload IAM and external-provider compatibility verified.
- [ ] Business-flow quotas, sustained load, overall deadlines and multi-replica/failover budgets met.
- [ ] Production-sized recovery and approved audit/history retention/attestation validated.
- [ ] Operator UAT completed; independent reviewer signs findings/remediation evidence.

Open controls remain release findings even when the local/CI suite passes. This checklist supplies repeatable verification steps, not a numerical production-success guarantee.

The [checked-in development route inventory](api-inventory.json) includes lazy/nested FastAPI routers and documentation/health routes. Identity hints follow middleware routing, not a complete permission proof; every row retains authorization_review=REQUIRED. Production docs routes are absent under ENVIRONMENT=production.

## Executed controlled status (2026-10-12)

The final branch has 24 passing focused unit/security/SDK cases, complete 124-route inventory, real browser CRUD/tenant checks, Basic TLS/heartbeat/native evidence, ServiceNow-shaped TLS/fenced delivery, EKS SDK/API/import/browser checks, populated restore/retention/restricted-role/TLS checks, full NOC/ETL/theme regression and clean Compose/restart/old read compatibility. [Ordered evidence ledger](../OPERATIONAL_RELEASE_SEQUENCE.md). These cover parts of all ten risk categories; remaining deployment/quota/real-provider/human-review cases above are UNRUN or pending acceptance, not full OWASP PASS.
