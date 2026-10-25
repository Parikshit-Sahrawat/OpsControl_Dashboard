# DEV-05.2 release hardening — 2026-10-25

**Decision: NO-GO for release.** The two pinned Contrib runtime gaps are closed;
genuine provider certification, required-check visibility, dependency triage and
operational acceptance remain unresolved. This is not production authorization.

Issue #68 was read in full, including its comments (none). Work uses only existing
branch `release/dev-05-2-hardening`, based on current main
`09a578f70282c7889a515c332c948f1940ae6719`. Implementation commits are `b8a517c`
and `7efd284` (full SHAs in `revision.json`). No application/worker behavior,
assertion, original skip decorator, PR #65 failure evidence or PR #67 remediation
evidence was modified. No production or unauthorized endpoint was accessed.

## Pinned runtime — completed

The repository already approved Contrib **0.123.0 Linux amd64** using immutable
upstream image digest `sha256:e39311df1f3d941923c00da79ac7ba6269124a870ee87e3c3ad24d60f8aee4d2`.
Docker validated the content-addressed distribution. Extracting `/otelcol-contrib`
from that trusted image produced independently pinned binary SHA-256
`6bca4ddd928b4b0880f7ec6c16511922f740c497b4efa4b33915b2d54a729213`.
This is not a hash substituted for an arbitrary untrusted download.

`verification/dev052/provision_contrib.py` enforces version/platform/image/binary
pins, rejects mismatches before execution, supports approved offline copies,
refuses to overwrite a mismatched existing output, and removes only its uniquely
named extraction container in finally. Binary and license provenance are recorded;
no executable is committed or redistributed. Upstream is Apache-2.0; redistribution
must retain applicable licenses/NOTICE. Transitive license clearance remains open.
The existing V1.5 quality workflow now uses this verifier instead of plain extraction.

The exact existing tests ran using the real verified executable, unchanged:

1. `tests.test_collection_v15.CollectionV15Tests.test_actual_contrib_accepts_five_methods` — **PASS**.
2. `tests.test_collection_v15.RealCollectionRuntimeTests.test_actual_scrape_and_log_rotation_truncation_restart` — **PASS**.

**2 executed, zero skipped, zero failures/errors.** The second test exercises actual
scraping, multiline log collection, rotation, truncation and restart. The new focused
runner fails on skips/zero-test runs. Online extraction and offline provisioning both
succeeded, and mismatch rejection passed. See provenance, test JSON and logs in
[evidence](evidence/) and portable commands in `verification/dev052/README.md`.

## Other fresh checks

- Targeted backend auth/tenant, worker, API configuration, release hardening,
  redaction, provider failure classification and Pentaho parser contracts:
  **57 passed**, zero skips/failures. These are unit/contracts, not native certification.
- Existing frontend suite: **36 passed**; lint and build passed.
- Workflow checker `bash scripts/check-workflows.sh`: exit 0.
- Provisioning mismatch regression: **1 passed**.
- npm audit: **zero reported vulnerabilities** at observation time.
- Python environment audit: **9 advisories in 2 packages**: Black 25.1.0 (3),
  pip 25.0.1 (6). CycloneDX environment SBOM and exact advisory IDs are retained.
  This includes tooling; it does not establish exploitable production application
  vulnerabilities. Applicability/remediation requires triage; do not call it clean.
  No dependency pin was silently upgraded to conceal this finding.

## Genuine Pentaho and historical RT-LAB

**Fresh Carte, Pan and Kitchen certification: BLOCKED / no tests executed.**
Runtime metadata exposes no provider credentials/identities; no Pentaho/Carte/PDI
variable bindings or supplied runtime artifact was found in accessible supplied
artifact locations. No target probing was attempted. Owner must supply an approved
isolated installation/build/license/Java/OS, target and execution authority, CA,
read-only account, exact reader paths, allowed host/CIDRs, benign job/transformation
fixtures and secure credential delivery.

Reviewed `RT-LAB-016D-final-reconciliation.md`, its selected-artifact manifest and
RT-LAB-011E native parser evidence. **Five selected historical artifact hashes match**.
The report itself says it is not an independent execution of OpsControl runtime
tests: native lab database durability is unverified; OpsControl durability,
reconciliation, cross-source isolation and RT-001–RT-020 were not run. Those gaps
remain. No historical or synthetic result was relabeled fresh certification.

[Pentaho certification runbook](../PENTAHO_CERTIFICATION.md) gives required inputs,
exact-build/method matrix, approved GET transport shape, owner-operated Pan/Kitchen
sequence, identity/time/status/log checks, wrapper/RBAC/secrets checks, independent
review and scoped cleanup. Native cloud and Windows need separate access; Kubernetes
monitoring remains deferred, not certified.

## Release gates and CI

[gates.json](gates.json) is the complete explicit gate matrix for this review.
Fresh unit security contracts and Contrib observability pass. Prior DEV-05.0/05.1
migration, audit, alert/dashboard/recovery and isolated cleanup evidence remains
historical evidence, not a fresh full-stack run at the new main SHA. Backup/restore,
rollback and recovery runbooks were located in `docs/RELEASE_RELIABILITY.md`,
`docs/ARCH_001_OPERATIONS.md` and Sprint 13 preservation documents; a fresh populated
rehearsal and operational DR were **NOT TESTED**. No new expensive unrelated green
workflow was manually dispatched or rerun.

Observed main-SHA Actions: OpsControl Validation and V1.6 pipeline ownership succeeded;
V1.5 continuous quality was in progress; disabled Stage B was skipped. Branch
protection read returned **HTTP 403, Resource not accessible by integration**.
Therefore the complete required-check list cannot be certified. PR check observations
are captured separately with exact observed SHAs; pending checks are not passes.
Owner/repository administrator must confirm required checks and all applicable
successful outcomes on the final PR revision before release.

Release-image SBOM/container scans, transitive license clearance and universally
reproducible release image provenance remain **BLOCKED**; the Python environment SBOM
and Contrib image pin do not satisfy those whole-image gates. Production control-plane
TLS, load testing, real external notification delivery and operational DR remain
**NOT TESTED**, pending approved environments and acceptance criteria.

GO requires all mandatory P0 provider/security/runtime gates and required CI checks
passed at the exact release SHA, signed license/security review, approved operational
criteria and completed rehearsals. CONDITIONAL GO could cover an explicitly approved
isolated internal evaluation with documented exclusions only, never production rollout
or a claim of native certification. Current unresolved mandatory gates mean **NO-GO**.

## Cleanup and provenance

Only network-none artifact-extraction containers were created; all were removed.
Runtime tests cleaned their temporary files, collector subprocesses and local HTTP
servers. No product Compose stack or synthetic accounts/secrets were created in this
turn. Verified binary caches are local non-secret dependencies, not committed artifacts.
No broad Docker cleanup was run. Resource observations are in `cleanup.json`.
All original DEV-05.0/05.1 evidence paths have zero changes from the branch baseline.
No PR was merged, and production deployment remains prohibited.

Draft PR: https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/69.
PR check snapshot `evidence/pr-ci-snapshot.json` observes head
`1ba89a23abb8734929ab29515d1152570f3b0965`; checks were queued/in progress,
not successful outcomes. This evidence-only follow-up commit can enqueue new checks;
inspect the live PR at its final SHA. Required-check completeness remains blocked
by the protection API permission denial. No all-green CI assertion is made.
