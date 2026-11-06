# OC-ETL-006 — native binding and readiness implementation

2026-11-06 UTC; product baseline `a915322b5c5c80b0d37dea71f6b7f70237082340`; existing draft PR80, branch `dev/post-pr78-architecture-closure-20261105`.

[Owner approval and exact scope](APPROVAL_AND_SCOPE.md) · [Migration/rollback/recovery](MIGRATION_AND_RECOVERY.md) · [Readiness transitions](READINESS_TRANSITIONS.md).

## Bounded implementation

Additive revision `0040_etl_native_bindings`, immutable scoped binding versions, one current claim owner/Job, temporal method/source snapshots, retirement and receipt-link constraints; authenticated stage/replace/retire/confirmation-denial commands with current authorization and commit rollback; integration/resource activation and live routing refuse opted-in unconfirmed/stale bindings. The Resource Management UI exposes claims, history and six independently evaluated readiness dimensions. No ETL workload controls, collector changes or applied migration edits.

The precommit full lab passed 102 tests, zero failures/errors/skips, PostgreSQL17.11, including the retained OC-ETL-002–005 suite and new migration/concurrency/browser/security cases. Final committed-source rerun and raw evidence will be attached in the evidence commit; this provisional source-commit report does not claim final hosted CI. Prior failed attempts are retained rather than relabelled PASS.

## Definition of Done remains incomplete

D01–D06 product-owner authorization is recorded; it is not independent certification. Native authority mapping/attestation D09 is unavailable, so confirmation and genuine-provider-dependent positive activation remain BLOCKED. Current immutable versions reserve **claims**, not independently certified cross-surface provider aliases. Qualified receipt routing and active-reader replacement have NOT been positively qualified. Existing live sources/leases/holds require the reviewed handoff protocol; they are not bypassed.

A separate containerized deployment is BLOCKED: immutable application candidates and safe old-writer rollback/version fencing are not qualified. The disposable migrated PostgreSQL + loopback API/Vite/Chromium acceptance lab is controlled verification, not deployment to owner UAT. Populated schema downgrade refuses and backup/restore is tested; that is not evidence that old applications can safely write through a new temporal binding contract. No deployment or release advancement occurred.

Next bounded task: obtain exact D09 provider authority evidence and review the qualification adapter/certification path, then qualify confirmation, accepted receipt routing and source handoff; separately version-fence old application writers and rehearse rollback before deployment. D07 calendar, D08 threshold and independent UAT remain unresolved. No independent security/DBA/provider signatures are fabricated.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
