# Live-readiness authorization checklist

**NOT AUTHORIZED / NOT READY.** No target, credential, accountable issuer or reviewer approval has been provided for live qualification. All entries below remain Pending. Do not ask for secrets in chat or use guessed endpoints.

| Gate | Required accountable evidence | Current selection |
|---|---|---|
| Target ownership | Project owner authorizes exact isolated host/port/Server/Carte/repository, tenant/environment and UTC window; proves no production/customer data | Pending |
| Installed provenance | Runtime owner records exact build/edition/plugin/Java/OS and immutable binary/image/config hashes; vendor API spec matching build | Pending |
| Read operations | Owner and security reviewer approve exact GET paths, queries, native IDs, pagination/rate/size bounds and no control endpoints | Pending |
| Native authority | Runtime owner independently proves repository/scheduler instance, object identity/type, aliases, epoch and restore/clone semantics | Pending |
| Issuer governance | Accountable native verifier with documented evidence collection; public key, target inventory, expiry/revocation/rotation; private key outside app | Pending |
| Independent review | Named reviewer distinct from stager validates original raw evidence and actual scope; no fabricated security/DBA/provider signoff | Pending |
| TLS/network | Security/network owner approves CA/hostname/DNS/host-CIDR-port allowlists, no redirects/skip-verify, expiry and response limits | Pending |
| Credentials | Least-privilege provider read-only service account via protected secure reference, rotation/revocation tested; never supplied to chat/logs | Pending |
| Receipts/privacy | Evidence owner approves redaction, restricted originals, UTC time, source inventory, dedup IDs, retention/holds and independent DB reconciliation | Pending |
| Disposable application | Owner authorizes separate PG/API/browser fixture; role isolation, capacity, backup/restore and safe rollback qualified | Pending |
| Policy D07/D08 | Product owner supplies exact recurrence/calendar/occurrence and long-running/freshness/aggregation decisions; no invented semantics | Pending |
| Execution prohibition | Monitoring operator acknowledges no schedule edits, run/retry/stop/terminate, Pan/Kitchen invocation or provider workload generation | Pending |

Approval roles are identified; people/signatures are not invented. Past Parikshit dual-role approval for an isolated collector feasibility study is not a Pentaho issuer or live-target authorization.

## Nine owner-acceptance selections

RM-01, RM-04, RM-05, AM-01, CMP-01, CMP-02, API-01, OPS-03 and UI-010 all remain **Pending** for current acceptance selection / independent UAT. Historical disposition **OWNER_APPROVED_CONTROLLED_SCOPE — INDEPENDENT_UAT_PENDING** is preserved and not rescinded or upgraded. See OWNER_ACCEPTANCE_SELECTIONS.json. New ETL native qualification has no inferred owner acceptance.

Stop/escalate to the accountable owner on target/build changes, insufficient read permissions, native alias ambiguity, evidence gaps, stale generation, failed TLS or revocation. Preserve failed raw evidence safely; do not broaden allowlists, restart the provider, execute workloads or promote release gates to fill gaps.


**Offline preparation only. Genuine qualification BLOCKED / NOT RUN. CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
