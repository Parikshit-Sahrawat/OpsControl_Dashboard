# Deployment, upgrade/rollback and operator UAT

The local demonstration is **development-only**, bound to loopback, with a private PostgreSQL container, generated admin password and fictional data. It is not the production deployment profile. Use `bash scripts/demo-up.sh`; the operator password is stored in ignored `.demo-private/admin-password` with restricted permissions. Preserve existing files and persistent volumes. Provider/host SDK requirements are included in the demo API image; metadata credential retrieval is disabled by default.

In a cloud environment with a trusted TLS inspection CA, an operator-owned `OPSCONTROL_DEMO_COMPOSE_OVERRIDE` can mount the host CA as an ephemeral BuildKit secret during pip/npm installation. TLS verification stays enabled; the bundle is not baked into the image. Keep such overrides outside the checkout. `demo-up.sh` and `demo-down.sh` both honor the override. `COMPOSE_PROJECT_NAME` can isolate a disposable project; delete volumes only when they belong to that disposable test.

## Executed controlled installation evidence

- Fresh isolated Compose project built and started API/frontend/PostgreSQL.
- Generated password authenticated the fictional demo administrator; authenticated API returned DEMO-LAB.
- API restart preserved a specifically created Data Source UUID.
- Current schema reached `0024_notification_leases`.
- API/frontend published only on 127.0.0.1; demo PostgreSQL had no host port. The separate local-development DB compose now binds 5432 to 127.0.0.1.
- Archived previous main `277ec2c` authenticated/read the persisted source against the new additive schema without attempting downgrade. This demonstrates basic read/auth compatibility, not acceptance of old code with new feature configurations.
- [Redacted controlled installation report](acceptance/operational-sequence/sprint5-compose.json).

## Production and rollback procedure

1. Record exact reviewed commit/image digest and independent acceptance. Provision migration-owner, restricted runtime and maintenance identities separately; never run API with migration owner.
2. Take a populated checksum-verified backup and restore it into a separate empty staging database. Compare row/constraint fingerprints and audit enforcement before upgrade. Retain approved encrypted/off-site copies; do not upload dumps to GitHub.
3. Run Alembic head as owner, then reapply database capabilities. New nullable worker liveness/delivery lease fields are additive. Production startup checks required columns as well as owner/schema/audit privilege restrictions. Changing the app image does not grant permission to downgrade production data.
4. Deploy the supported runtime entrypoint with exact trusted ingress IPs, HTTPS-only origins, private API ingress and generated static-SPA hash CSP. Verify actual Host rejection, certificate rotation, browser boot, CNI/firewall and deployed secret reference/rotation; the local TLS test is not acceptance of the real deployment.
5. Before application rollback, stop/coordinate notification dispatch and align worker/API versions. Previous API/agent versions lack the new heartbeat/Basic-auth/EKS contracts; deactivate those configurations or restore compatible component versions. Retain compatible additive schema. Never silently strip authentication or enable an unsupported collector.
6. Rehearse with the intended images and target-sized data; record restart/reconnect/failover, RTO/RPO and sustained latency/cost budgets. Migration downgrade of heartbeat or lease columns loses ephemeral state and must not run with active dispatch.

## Operator UAT journeys

| Journey | Steps and expected result | Current evidence |
|---|---|---|
| Register/edit source | Select organization, create source/agent metadata, edit stored registration, disable source | Actual browser/DB CRUD; inactive OTEL and tenant negatives PASS |
| Activate monitoring | Attach pinned template/rule versions, preview/apply, reapply, enable assigned collector | Fresh real HTTPS golden path PASS |
| Collect authenticated service | Configure approved reference + local worker allowlist; observe real healthy/fail/recover facts | Actual Basic TLS and native DB observations PASS; production IAM/rotation pending |
| Investigate/resolve | Consecutive breach, open/dedup, evidence drawer, authorized note/transition, recover then close | Native incident/ETL/NOC browser PASS |
| External incident | Configure approved destination/credential/choices, open/retry/recover same incident | Fictional ServiceNow TLS PASS; real instance ACL/mandatory fields/routing acceptance pending |
| Discover EKS | Platform scan, dry run, approve import; no fabricated workload health/collector | AWS SDK stubs + real API/DB/both-theme browser PASS; genuine AWS paused |
| Operate both themes | Primary tabs, filters, scope switch, histories, mobile/keyboard, reload persistence | Authenticated NOC/theme regression; latest head CI required |
| Recover/release | Restore populated DB, reapply roles, deploy compatible image, restart/rollback, verify retained evidence | Controlled restore/runtime/Compose checks; target-scale DR and human UAT pending |

Independent reviewer/operator sign-off must record environment, identities, exact versions, case results and remediation. Development CI, self-audit and fictional provider acceptance do not authorize production rollout.
