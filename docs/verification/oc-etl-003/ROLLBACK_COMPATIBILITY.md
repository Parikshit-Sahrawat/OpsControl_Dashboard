# Rollback compatibility and recovery contract

## Supported and executed paths

| Path | Data state | Result |
|---|---|---|
| Fresh base → head 0039 | Empty owned database | PASS; model alignment check passes |
| 0039 → 0038 → 0039 | Empty workflow tables | PASS; identical rows/schema/FKs |
| Populated 0038 → 0039 → 0038 | Legacy VM/Job/History, no assigned workflow | PASS; every table content hash, columns and FKs preserved |
| Populated 0039 → 0038 | Workflow, two Jobs, dependency plus historical execution | REFUSED as required; every table hash, revision, columns and FKs unchanged |
| 0017 → 0018 → 0017 | Legacy history with NULL new native identity | PASS; preserved |
| 0018 → 0017 | Non-NULL native execution ID | REFUSED; unchanged |
| 0020 → 0019 | Non-NULL source evidence | REFUSED; unchanged |
| Relative downgrade / offline downgrade SQL | Populated fixture | REFUSED; unchanged |
| pg_dump custom archive → empty separate database via pg_restore | Populated 0039 synthetic fixture | PASS; every table hash, columns and FKs equal |

These are six grouped preservation checks in rollback-results.json. Expected refusal commands exit nonzero and are explicitly labeled in rollback-commands.json; they are not successful destructive downgrades.

## Review inventory and limits

The retained migration inventory records all revision downgrade/drop operations. The central protected revision map covers ETL Workflow foundation 0039; native recovery 0036; Pentaho history/review/attempts 0035–0033; pipeline ownership 0032; notifications/native incidents 0031/0030; unified monitoring 0027; incidents 0021; evidence 0020; native identity 0018; correlation 0008; initial ETL entities 0001. Existing revision guards remain unchanged. Shared resource/security/monitoring migrations are dependencies, not a general authorization to roll back the whole product. Arbitrary historical chains, shared configuration retirement and populated downgrade of every old revision are **NOT TESTED**; require separate rehearsal and approval. The complete applied migration source hashes are preserved in SOURCE_SHA256.json and compared against the task baseline.

The preflight locks protected existing tables before checking them and holds locks through transactional DDL. A five-second local lock timeout fails closed; retry only after resolving active writers. No force bypass, row deletion, cascading deletion, or automatic grouping is provided. Raw SQL, historical migration scripts called outside the current runner, and older source checkouts can bypass this contract and are unsupported.

## Operator procedure

1. Identify application SHA, explicit current/target Alembic revisions, owners and all affected relationships. Stop deployment changes and preserve the current schema if populated workflow state exists.
2. Before any rollback attempt, take an authorized full custom-format PostgreSQL backup and record SHA-256, PostgreSQL/pg_dump versions, source identity and retention. Keep credentials outside command logs. Preserve the original backup as immutable recovery evidence.
3. Restore into an empty isolated database using pg_restore --exit-on-error. Compare all-table row counts/content hashes, columns, foreign keys and Alembic revision. Validate the intended application version there. The included probe implements these steps with synthetic data.
4. Use the current guarded runner with an explicit revision. Empty/unassigned states may use tested schema rollback paths. A populated-data refusal means retain schema; do not delete data or edit history to force rollback.
5. Prefer a separately verified application-only rollback on the retained additive schema. Compatibility of a particular older application binary is NOT established by this task and must be tested before use.
6. On failure, preserve logs, verify Alembic revision and all-table hashes, and stop. If hashes differ or recovery is uncertain, escalate to the database/ETL owner. Restore the verified archive to a separate empty database first; never overwrite a live/customer database without separate authorization and recovery approval.

No destructive schema downgrade is represented as reversible. The recovery proof here is actual pg_dump/pg_restore, not a claim that removed records can be reconstructed from migrations.
