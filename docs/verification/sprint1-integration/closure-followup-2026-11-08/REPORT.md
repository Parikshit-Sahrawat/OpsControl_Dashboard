# Sprint 1 closure follow-up — 2026-11-08

**PARTIAL/BLOCKED; Sprint 1 NOT COMPLETE.** Baseline PR89 `4081fc75117afbd43e1fc4489925a2d65d744551`; main remains `2e4fe5d8cb0f39170b0d789fdd7e07be4ac0219a`. Current source identities, changed paths and exact suite commits are in SOURCE_IDENTITIES.json. No merge, deployment, UAT or provider qualification.

## NOC fixture failure and correction

Hosted run42513541861 / job128831533710 failed with EACCES at Python's socket.bind preflight. The original candidate list was loopback11432,18800,15174 and the host-resolved interface on443. The only privileged port is443, but the generic old error and339-byte uploaded artifact omit the exact numeric hosted address and individual failed bind. That missing historical fact cannot be reconstructed as evidence. BIND_FAILURE_ANALYSIS.json preserves this limitation and raw hosted log.

The corrected fixture records address/port before startup. The actual controlled rerun used **172.26.91.251:443 → owned fixture443**, verified HTTPS with its IP SAN CA, exact host/CIDR policy, authenticated Carte-shaped GETs, real remote-worker HTTP monitoring, alert lifecycle, FastAPI/PostgreSQL and React/Playwright. Docker claims443 exclusively; Python never pre-binds a privileged port. An occupied publish fails Docker startup and cannot adopt an existing service. No root Python, sudo, capability escalation, TLS bypass or worker/network-policy relaxation.

The initial high-port candidate was rejected422 by the worker's existing443-only contract. Its failure is retained. The correction deliberately preserves443 instead of broadening the protocol. Unit negatives exercise an actual occupied TCP listener and deterministic injected EACCES with address/port/errno; the latter is **not** a genuine hosted kernel-permission reproduction. Future hosted errors now identify the exact endpoint.

## Resource/configuration integration

The existing Data Source ledger remains the single authority; no migration rewrite or second store. Additive0043 closes direct name/description/auth-mode writer gaps without altering applied0042. Both the central downgrade preflight and direct0043 downgrade refuse populated-history rollback. The new refused rollback preserves an identical whole-dump SHA256 `260fad554f844e35f848c5405cbb9db4f2488f45ee103007112ce532cc2ff5af`. Fresh upgrade, empty supported downgrade/reupgrade, schema check and108-table restore pass. Command.source_context is a strictly validated DataSourceUpdate subset. Organization/reparenting/authentication/lifecycle fields cannot be smuggled into it. Context edits require resources.update as well as existing template command authority. Applicability revalidates against the proposed context before any commit. Context, effective configuration, attachments, immutable snapshot and source head commit together under existing authorization/source locks.

Both legacy PATCH surfaces adapt revisioned edits to the same command and require Expected-Revision and Idempotency-Key (428 if missing). Existing idempotency hashes remain compatible when the new optional context is absent. Resource Management V2 replaces attachment loops with one command; the Compute Instance writer binds the source revision and resource revision in the same transaction. Stale source/resource edits409 preserve prior state. Unknown/cross-tenant ownership fields remain422/403/404 as appropriate. The two source preconditions are not automatically guessed for real clients.

Controlled tests verify same-transaction resource/source heads, context/OS validation rollback, both positive legacy adapters, missing preconditions, concurrent source conflicts, actual advisory-lock revocation and DB connection death. A separate owned API SIGKILL at a DB-instrumented pre-ledger boundary leaves head0/history0/projection0. Restart/retry commits head1/history1/projection1; kill after visible commit, restart and repeat the same key retains those counts and reports replayed=true. This demonstrates the stated transaction/restart cuts, **not** every possible cut or power-loss/disk durability, and does not alter CHK-001.

A deliberate remaining boundary: environment propagation into an already revisioned child API source refuses409 without a separately coordinated source command. It cannot silently modify child configuration. Complete multi-source coordination/UI cutover remains an explicit acceptance gap.

## History and staged UX

The source configuration panel now has backend-validated nonpersistent staged preview, explicit discard, detach review/confirmation, keyset history pagination, immutable revision detail, comparison to current, and audited new-revision restoration. A stale409 offers explicit refresh while retaining staged fields; no automatic overwrite. Version/override changes invalidate preview. Scope changes immediately clear old history/detail/diff; request generations reject late results. Read-only users retain permitted views; mutations remain backend-authorized.

Staged drafts here are explicitly **browser-memory only**, non-operational and discarded on leaving. This is not a claim of durable draft storage. Saving/rollback never activates or deploys collectors, restores credentials/checkpoints, or manufactures HEALTHY telemetry. Existing legacy import remains explicitly UNVERIFIED.

## Security work and independent blockers

See IMAGE_REMEDIATION.md, IMAGE_BASELINE.json, ALL_SEVEN_FINDINGS.csv and raw hosted artifacts. All1,890 original scanner matches remain individually reviewable. Python3.12.16 and maintained nginx official immutable indexes are pinned; compatible OS upgrades and UAT installer removal are prepared. Seven-role CI still builds/scans all roles, uploads CycloneDX/Grype/licence/provenance and fails on unchanged High/Critical/unknown and pending licence rules.

Fresh final application builds/scans are not locally possible on the Docker backing filesystem observed at0 free. Direct registry base-image scans were executed in task-owned/tmp storage, explicitly distinct from built application candidates. No finding is waived or filtered. OTel0.123.0 and its immutable digest stay unchanged; compiled dependencies retain unresolved findings. Debian vendor-wont-fix findings and accountable licence/NOTICE/source-offer review remain unresolved. Production PostgreSQL composition/volumes were not changed; an Alpine candidate is not a certified live glibc-to-musl/locale cutover.

## Executed results

- Source/ETL contracts:44 PASS,0 FAIL/SKIP, plus deterministic API SIGKILL/restart/replay cuts; PostgreSQL17.11, migrations through0043.
- Broad backend discovery at13de0a2:594 PASS,73 SKIPPED,0 FAIL among667 executions; its later HTTP fixture failed and remains recorded. Separate owned suites execute the gated boundaries; skips stay SKIPPED.
- ETL regression at13de0a2:117 PASS,0 FAIL/SKIP. Final integrated PostgreSQL/HTTP/browser atf45a992:98 backend cases PASS;15 pipeline HTTP groups; Pentaho4/5/4/5; RBAC14; resource security8 and workspace14 browser groups, other browser groups17/5/3; archive/recovery checks PASS. These suites overlap.
- Frontend55 PASS, lint/build PASS; CI unit28 PASS;28 workflow definitions valid;795 scope records,782 UNKNOWN still RUN. Compose/static checks PASS; npm audit0; pip check intact.
- NOC corrected isolated Docker443 run PASS with13 theme checks and6 contrast measures. Historical numeric hosted address remains unrecovered.
- Seven original image gates FAIL; fresh nginx/PostgreSQL base scans still FAIL. Final application image builds/scans are pending hosted execution, not locally cleared.

## Verification and handoff

TEST_EXECUTIONS.json and raw/ contain actual commands, per-suite counts, failures/retries, versions, screenshots and cleanup. Counts overlap and must not be added. Backend discovery skips remain SKIPPED; separate owned suites establish their applicable execution evidence. Earlier failed port, fixture, status-contract and service-stub attempts are preserved.

All13 existing required checks remain, with the existing strictness/review rules. No ruleset update or removal is attempted in this follow-up. The prior Administration-write403 prerequisite remains. All28 workflow definitions and scope inventory retain tests; UNKNOWN records still RUN. Final-head TierA/B/C and legacy jobs are triggered only after final push. Under mandatory Trigger-and-Exit, results are PENDING and must be inspected by the owner, never replaced with older green runs.

Owner visual acceptance and independent engineering review are still required. Catalogue publication concurrency, provider-specific applicability/qualification and coordinated child-source cutover remain open. Nine owner selections, D07/D08 and independent UAT remain pending.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
