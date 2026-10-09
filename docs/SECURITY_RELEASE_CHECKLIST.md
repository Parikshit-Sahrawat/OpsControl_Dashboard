# OpsControl Security Release Checklist — Draft Review Branch

**Scope:** authentication, tenant isolation and first-pass release hardening. Branch `security/phase2-release-hardening` / draft PR #19. No production deployment and no merge to `main` authorized by this checklist.

## Implemented controls (require latest green CI)

| Requirement | Implementation location | Required validation |
|---|---|---|
| Authentication, session expiration, logout | `backend/app/security/http.py`, identity models | Invalid/expired/missing bearer 401; logout revokes token |
| Per-user and per-IP login throttling | `security/throttle.py` and PostgreSQL buckets | 10 account failures/15m, 30 direct-client-IP failures/15m, 429 retry-after, concurrent workers |
| Role/member isolation | `security/scope.py`, `organization_memberships` | Two-tenant IDOR, mixed-admin/viewer, nested ETL/metric/log/alert and forged FK negative tests |
| User and membership lifecycle | `/auth/users`, `/auth/memberships`, Access Management React tab | Role update/remove, password reset, disable and last-admin guard, sessions revoked |
| Security audit event history | `security/audit.py`, `security_audit_events`, migration `0014_audit_mutation_guard` | Login/deny/config changes recorded without raw bodies or tokens; admin-only read |
| Worker identity boundary | `worker_identities`, `/api/v1/worker/whoami` | Worker token cannot authenticate to human APIs; revoke/expiry/organization scope |
| Hardened API HTTP headers | `backend/app/main.py` | CSP, no-store, nosniff, frame deny and production TLS/HSTS checks |
| Config secret references | `security/secret_refs.py`, monitoring serializers/validators | Reject plaintext config credentials and URL userinfo; redact legacy API responses |
| Dependency/secret scanning | `.github/workflows/security-validation.yml` | `pip-audit`, npm production audit, Gitleaks history scan |
| Reproducible frontend install | `frontend/package-lock.json`, GitHub Actions `npm ci` | lockfile version 3, deterministic install and build |
| Fresh database migrations and browser tests | staging workflow | PostgreSQL 17 Alembic head, auth security probes, authenticated Playwright |

## Release blockers that cannot be certified solely by code/CI

1. **Independent security/authorization review:** assess all routers including ORM bypass via direct SQL, nested service queries, evidence serializers, all role combinations, audit event tampering, session token handling and denial-of-service. Peer review is required.
2. **Threat model and deployment hardening:** review live reverse proxy TLS termination, allowed forwarded headers, CSP for the separately hosted **React SPA** (API CSP does not protect static frontend by itself), secure cookies if ever introduced, browser XSS and image/agent supply chain.
3. **Credential secrets migration:** legacy `connection_config`/`configuration`/`package_config` may already contain unencrypted secrets. Redaction only prevents API readback; identify, remove/rotate and securely migrate existing secrets to an approved external secret provider. No production secret provider has been implemented yet.
4. **Database audit policy:** an SQL-level trigger rejects UPDATE/DELETE for ordinary application queries, but a database owner can disable triggers. Audit archival, independent attestation and deletion/retention remain open. Need approved retention, restricted DB roles, archival/deletion for privacy regulations and an audit integrity mechanism for regulated use.
5. **Rate limit operational robustness:** test multi-replica concurrency, client-IP derivation through a *trusted* proxy and appropriate account recovery under malicious lockouts. A proxy sharing one client IP can cause collateral throttling.
6. **Dedicated agent authorization:** worker identity-only route is implemented, but outbound remote-agent protocol, job claim/authorization, ingest signature/replay checks and egress/SSRF policy are not implemented. Do not connect private networks until these are verified.
7. **Performance, disaster recovery and retention:** stress/load test session lookups, audit write volume, bucket cleanup and backup/restore. Inspect upgrade/downgrade against a **backup of an existing non-production dataset**, not merely an empty test DB.
8. **Public-release privacy/provenance:** scan entire Git history, example data, screenshots, README and seed scripts for proprietary/private information; evaluate licensing/third-party notices; maintain vulnerability disclosure channel.

## Evidence and status rules

- `backend/scripts/auth_tenant_probe.py`: baseline identity and resource isolation.
- `backend/scripts/deep_tenant_security_probe.py`: metrics/logs/alerts and referenced-entity tenant isolation.
- `backend/scripts/security_release_probe.py`: lifecycle, rate-limit, audit, worker isolation, CSP headers, raw secret rejection and redaction.
- GitHub Actions: **OpsControl Security Release Gate**, **OpsControl Validation**, **Security and Dependency Validation**.
- Every check must pass at PR head SHA; do not count earlier successful runs after a later code change.
- A red check must remain visible and be remediated or documented as a blocker; no skip/xfail means "passed".
- This checklist is a review record, **not a claim of completed independent security audit or permission to deploy**.

## Maintainer sign-off (pending)

- [ ] Independent code/security reviewer approved
- [ ] Full latest-head CI green and archive links recorded
- [ ] Existing database dry-run upgrade and restore verified
- [ ] Secret migration and any necessary credential rotation completed
- [ ] Reverse proxy/static UI headers and trusted client-IP derivation verified
- [ ] Threat model, retention and incident response policy approved
- [ ] Tenant/worker attack-surface tests complete
- [ ] Explicit maintainer merge/deploy approval granted
