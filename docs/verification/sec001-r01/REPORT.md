# SEC001-R01 — exact-image coverage implementation

Date: 2026-11-09. Outcome: **IMPLEMENTED; FRESH EIGHT-ROLE CI EVIDENCE PENDING / RELEASE BLOCKED**.

## Scope and provenance

See [BASELINES.json](BASELINES.json) and [coverage matrix](COVERAGE_RECONCILIATION.md) for exact source, image and archive hashes. Both workstreams branch from the unchanged PR89 assessment, not main; draft review must target the PR89 integration branch to keep the diff bounded. Issue #96's historical read-only/RFC limit is superseded solely by the latest owner SEC001-R01 Scope A implementation authorization. R02 is separate. No finding inventory or scanned artifact was silently replaced.

## Implementation

`.ci/image-coverage.json` is the explicit role/build mapping. `scripts/ci/image_coverage.py` binds immutable local candidate identity to clean source/build inputs and rejects missing, swapped, tampered, stale or mismatched coverage. `scan_image.py` now requires the binding before scanning; existing scanners, versions, policies and licence review statuses are unchanged. The security workflow adds production frontend, retains all seven prior roles, and aggregates current-run artifacts with a pinned official download action. `security-sbom` still fails if *any* image security job fails. Required check names, triggers and permissions are preserved. Scope manifest adds eleven protective tests, without reclassifying old tests.

## Verification

See raw logs and `VALIDATION.json`. Focused tests use labelled synthetic metadata to exercise validation, not to certify images. An initial test mistakenly chose the fixture's existing zero digest as its tampered digest; that failed assertion is retained. The corrected test changes the digest to a different value; validation was not weakened. Root CI/security/controller unit regressions and workflow policy/actionlint are run locally. No application or database behavior changed; PostgreSQL/browser/runtime certification is not claimed.

Fresh eight-role Docker builds/scans are NOT RUN locally: Docker storage has approximately 243 MiB free and is unsuitable for isolated full builds. Existing artifacts are not recycled as new evidence. Hosted PR-triggered verification is PENDING; follow Trigger-and-Exit, do not poll for conclusions. Thus full acceptance requiring newly produced exact candidate scans remains incomplete.

## Security boundaries and remaining approvals

All original vulnerabilities, scanner failures and accountable licence/NOTICE signoffs remain open (Issues #96/#97/#98). Final registry identities, bundled frontend provenance and architecture qualification beyond amd64 remain gaps. A passing coverage check only proves artifact consistency; vulnerability and legal gates remain independent. No runtime code, Dockerfile, dependency version, base, collector pin or branch-protection setting changed. No deployments, publication, image rebuilding or cleanup affecting other projects occurred. Only task-owned temporary test directories may be removed by test teardown.

**SECURITY BLOCKED · CHK-001 FAIL · CHK-002 BLOCKED · RELEASE NO-GO · Collector 0.123.0 unchanged.**
