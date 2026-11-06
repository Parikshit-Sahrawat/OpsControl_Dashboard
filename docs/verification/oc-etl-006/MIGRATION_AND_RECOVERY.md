# Native binding migration and recovery contract

New forward revision: `0040_etl_native_bindings`, parent `0039_etl_workflow_foundation`. Applied revisions are unchanged. No inferred backfill and no deletion of legacy Job, Workflow, native Job, association, evidence, audit or holds.

## Storage and transaction invariants

`etl_native_bindings` retains scoped Workflow/Job/Resource/native Job/integration identities, native claim tuple/hash, method revision/connection version/checksum/capability/source generation/fence/reader hash snapshots, actor, reason and causal operation. Every new version references its predecessor. `valid_from` equals the previous `valid_until`; the only allowed update is the first validity closure. PostgreSQL deferred chain enforcement requires an atomic successor before commit. Deletes and identity/snapshot edits refuse. A retired terminal version retains the immutable tuple and releases current target ownership without allowing that Job to silently retarget.

Partial unique indexes reserve one current version per Job and one current owner per organization/native tuple, independently of the hash. Cross-scope FKs use RESTRICT. Insert triggers validate actual Job/Workflow/Resource/native/integration organization/environment and method/source versions. Referenced parent identities cannot be changed. Receipt links are append-only, unique by evidence, scope-checked, and must match a confirmed version, native ID, source/generation and receipt-time validity. No historical relationship is backfilled as proven.

HTTP requests retain existing authorization-state shared/exclusive transaction locks, including fresh session/revision validation. Per-Job row and per-claim advisory locks, SQL uniqueness and a five-second lock timeout bound competing mutations. Authentication/authorization mutations retain exclusive authority locks. Domain audit, operation result, closure and successor commit together; rejection/connection termination rolls back them together. Commit conflicts have deterministic 409 responses. This is not collector-delivery durability or exactly-once certification.

A source fence in a binding snapshot is its cutover lower bound. Source generation and reader definition must match. Normal monotonically increasing lease fences are checked by existing live ticket validation; they do not rebind the Job every poll. Lowered fences, changed source generation, reader revisions and connection/capability changes invalidate the projection. Staged replacements refuse in-flight leases and holds. No source generation is silently rebased and no checkpoint is reset.

## Supported migration exercise

1. Stop task writers and take a full PostgreSQL custom-format backup; inventory image/source/schema identities and holds.
2. Rehearse restore into a separately owned empty PostgreSQL17 database, comparing every table's deterministic row hash, columns and foreign keys.
3. Upgrade with `backend/.venv/bin/python -m alembic upgrade head` from backend. Existing unassigned/populated legacy rows remain unchanged. `alembic check` must pass.
4. For an entirely empty new binding schema, guarded downgrade to explicit `0039_etl_workflow_foundation` is supported; older supported empty/unassigned paths remain in the inherited probe.
5. If either new table is populated, downgrade refuses **before destructive DDL**, retaining schema, revision and content. No force flag. Retain revision0040; recover through the rehearsed backup/restore process with accountable review. Never delete binding rows to make downgrade green.

The tests terminate a PostgreSQL backend after validity closure but before successor commit, then independently verify the original version remains current. They test deferred closure refusal, immutable tuple/delete refusal, populated rollback refusal and actual backup/restore comparisons. This is one supported crash boundary, not every power-loss/storage-failure boundary. A separate task-owned same-version API is SIGKILLed after acknowledged commit and restarted; exact binding history survives. Old-application writer compatibility remains BLOCKED/NOT TESTED.

## Deployment/recovery limits

The disposable verification lab uses tmpfs PostgreSQL and loopback API/Vite/Chromium. It is not the owner UAT environment or a release image deployment. Do not downgrade a populated real database. Reverting application code while retaining new binding data must not silently resume old routing: older code is unaware of the opt-in fence. Mixed old/new writers and old-binary rollback are **BLOCKED** pending an explicit version-fenced deployment/rollback rehearsal. Preserve new schema and metadata during recovery; do not deploy old writers against it based on an empty downgrade test.

Raw backup files contain only task-generated synthetic data and hashed synthetic account credentials, with no genuine provider secrets. Private browser credentials are temporary and removed. Cleanup removes only the randomly named task container, its tmpfs and owned loopback processes. Original evidence is unchanged.
