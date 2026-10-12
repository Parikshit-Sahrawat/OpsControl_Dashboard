# OpsControl security release checklist

Reconciled 2026-10-11. Security PR #19 and remote-worker PR #20 are merged; current development baseline includes approved UI PR #25 at main `fbe83ba`. GitHub access and development merges are resolved. This checklist does not certify independent human review or production deployment.

| Control | Implementation/evidence | Acceptance state |
|---|---|---|
| Sessions, roles, membership and nested tenant boundaries | `security/http.py`, `security/scope.py`; auth, deep tenant and security release probes | Automated controlled negatives; independent review pending |
| Login throttling / revocation / last admin | PostgreSQL throttles; serialized last-admin mutation; concurrent release probe | Controlled concurrency; deployed trusted-IP/lockout recovery pending |
| Worker authorization / replay / lease fencing | Remote protocol and egress probes; migration 0015/0016; assigned job ingestion | Implemented and CI verified; real deployment egress remains required |
| Secret references / URL redaction | Exact-reference resolver; shared Settings environment; case-insensitive URL parser | Offline and controlled tests; real workload identity/rotation and legacy secret migration pending |
| Configuration/audit integrity | Same-transaction scoped mutation audit; SQL append-only trigger; restricted runtime capabilities | Controlled rollback/tamper tests; owner-independent archive/attestation pending |
| Runtime DB / proxy / TLS / SPA CSP | Production non-owner guard, explicit proxy list, Nginx hash CSP and TLS release harness | Controlled implementation; target deployment and human threat review pending |
| Backup / restore / raw evidence retention | Checksum/empty-target restore; populated fingerprints; bounded maintenance/pinned correlation evidence | Controlled gate; production-size RTO/RPO and approved historical retention pending |
| Dependency / secret scans | Security workflow: provider+host pip-audit, npm audit, Gitleaks | Require green checks at each new head; optional dependency lock completeness pending |
| Fleet scale / resilience | Bounded local scheduler, PG advisory locks, SDK timeouts, service prefetch and paging | Controlled multi-process recovery; sustained load/regional failover not accepted |

## Threat boundaries and open findings

- Browser → TLS ingress: TLS termination, frontend CSP, public hostname validation, certificate rotation and ingress network restriction must be verified in the target deployment. API headers alone do not protect the SPA.
- Ingress → API: trust only exact peers or approved bounded CIDRs; overwrite forwarding headers. Direct untrusted HTTP with forged forwarded TLS is denied in the release fixture. IP trust is not network access control.
- API/worker → DB: migration owner is separate from runtime and maintenance logins. Ordinary runtime cannot alter schema or mutate audit. An owner can still disable triggers: external archival/attestation is an unresolved requirement.
- Collector → provider: production legacy local API collector is retired; assigned remote HTTP workers retain allowlist/DNS/lease/replay controls. Non-HTTP local adapters require platform authority. Validate real IAM, CNI/firewall, provider total deadlines and deployed secret access.
- Resource transaction → audit: scoped ORM changes now append sanitized audit in their own transaction. Review direct SQL/service bypasses independently; middleware outcome audit is supplementary.
- Notification → external service: IO still occupies a DB transaction; fenced outbox claim redesign/load tests remain open. Legacy template/investigation/correlation concurrent writes also require targeted review/tests.
- Historic data → maintenance: raw metric/log cleanup excludes linked correlation evidence; audit/ETL/incidents/runs remain retained pending approved archive/deletion policy. Do not disable audit guards to satisfy retention.

## Release sign-off

- [ ] Independent eligible human security/authorization reviewer approved
- [ ] New reliability PR's exact head has all required CI checks green
- [ ] Real deployed legacy secrets identified, removed/rotated and reference access verified
- [ ] Target TLS/SPA headers/proxy/client-IP/firewall/CNI configuration reviewed
- [ ] Production-sized populated backup, restore and upgrade/rollback approved
- [ ] Archive/deletion/attestation policy approved
- [ ] Sustained concurrency, reconnect/restart/multi-replica/failover SLOs passed
- [ ] Clean Docker onboarding and operator UAT completed
- [ ] Formal release/production acceptance granted

[Detailed priority matrix, root causes, source paths and verification](RELEASE_RELIABILITY.md). Development merge approval is separate from these production gates; live AWS setup remains paused.

## OWASP self-audit package and ordered fixes

[OWASP API Security 2023 verification](security/OWASP_API_2023_CHECKLIST.md) supplies case IDs, exact steps, expected HTTP/DB outcomes, evidence recording and unrun production variants for each risk. [124-route inventory](security/api-inventory.json) is a coverage input; all rows retain REVIEW REQUIRED. The [ordered implementation](OPERATIONAL_RELEASE_SEQUENCE.md) contains controlled evidence for the new transport, liveness, delivery and discovery controls. Owner-approved PR #26 is merged at `277ec2c`; self-audit/CI do not replace independent production review.
