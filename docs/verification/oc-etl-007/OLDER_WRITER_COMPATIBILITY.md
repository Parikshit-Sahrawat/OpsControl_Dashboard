# Writer protocol1 and rollback boundary

New forward revision `0041_etl_authority_writer`, parent0040. Applied0040 and its original populated-downgrade guard are byte-identical to baseline. Revision0041 also protects any existing `etl_native_bindings` row during downgrade, even when all new authority tables are empty. Dropping only the writer fence would revive the old bypass, so rollback refuses before DDL.

## Actual old writers and protected paths

Exact archives of a915322b5c5c80b0d37dea71f6b7f70237082340 (pre-temporal) and a061bdbabe7e250fe7141861c193ca837ef14dbe (OC-ETL-006) are started with their unchanged app packages and current installed dependencies against the owned migrated PostgreSQL17 fixture. Archive SHA-256s are retained. These are exact source-version processes, not immutable historical release images or old dependency environments.

The old manual `/etl/job-orders/{id}/executions` route can otherwise insert projected histories. DB triggers now reject unmarked writes for any Job with temporal history, including retired claims. The inventory includes Job/history/step/normalized evidence, Resource, native Job/integration/method/connection/capability/association/source identity, raw pipeline evidence, collectors/runs and Pentaho attempt/alias/review/recovery projections. Metadata lookup is scoped by stored relationships, not request headers. The actual FENCED_TABLES and trigger SQL are in0041. Public routes cannot supply the transaction marker.

Current authority-aware server code uses transaction-local `set_config('opscontrol.etl_writer_protocol','1',true)` in fenced native binding/admission operations and current scoped pipeline mutations; authenticated Workflow Job configuration retains supported edits. Old generic ingestion/manual execution paths do not become authority-aware simply because the binary is new. They refuse for opted-in targets. Current runtime routing still validates authority; the marker is **not** proof or provider certification.

The protocol marker protects against unchanged old binaries, not a compromised trusted app/DB-role holder issuing arbitrary SQL or disabling triggers. `SET LOCAL` resets after commit/rollback/pool reuse. DB constraints and source/lease/proof checks remain independent. Initial opt-in and unmarked writes take the same Job row lock: an admitted old write commits before opt-in, or the later write is refused. No partial accepted batch or orphan checkpoint is allowed. PostgreSQL may abort conflicting/deadlocked transactions; callers must not interpret an error as an accepted receipt.

## Supported and unsupported compatibility

Unrelated legacy/unassigned Jobs retain their behavior. Actual old-version HTTP writes to a separate legacy Job succeed201. Opted-in writes return500 through the unchanged old handler; logs must prove `OC_ETL_WRITER_VERSION_REQUIRED`, and independent DB checks must show no new rows. Current API maps that exact PG diagnostic to actionable409. The old500 is tested fail-closed behavior, **not full application compatibility or a healthy rollback deployment**. Old read/health200 cannot authorize deployment.

Shared old batches involving an opted-in source are conservatively refused as a whole, including unknown identity aliases. This can delay unrelated records in the same legacy batch; independent unaffected writes are supported, mixed shared-source old/new production operation is not qualified. No rejected work is called accepted and no checkpoint is silently advanced. Do not disable the fence to restore availability. Existing holds and immutable histories are retained.

Same-version current API restart and DB transaction termination are retained regressions. Old processes are killed/restarted and remain fenced. Stale authentication/role revocation remains covered by real authenticated regressions; a connection-local writer flag is neither a role nor a bearer credential.

## Migration and restore

Fresh/empty and unassigned populated upgrade/rollback paths remain in the inherited probe. With an opted-in Job, explicit downgrade0040 refuses and complete schema/revision/data hashes remain unchanged. A real custom-format backup restores to a separate owned DB; every table's counts, SHA-256, columns and FKs must compare. A legacy SQL write must still be refused in the restored DB, proving trigger restoration rather than only row preservation.

Production/owner UAT data is never used. No force downgrade, table deletion, row clearing or cascade is introduced. Full older-binary rollback to an operational writer remains **BLOCKED**. Before deployment, approve a rollback contract that uses an authority-aware image or explicitly disables opted-in writes/readiness and handles mixed batches; test the actual immutable candidate dependencies and least-privilege DB grants. Restoring a database and showing an old health endpoint200 do not meet that gate.
