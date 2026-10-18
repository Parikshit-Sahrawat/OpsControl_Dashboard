# REC-03 — migration preservation

**PASS for the tested migration paths.** The repository's linear Alembic history runs through `0037_access_boundaries`; inspected revisions `0032_pipeline_ownership` → `0033_pentaho_attempts` → `0034_pentaho_review` → `0035_pentaho_history` → `0036_native_recovery` → `0037_access_boundaries` retain explicit dependencies. Neither migration files nor schema were edited.

| Check | Actual result | Boundary |
|---|---|---|
| Outer harness upgrade | Populated V1.5 fixture upgraded to current head; `alembic check` found no drift | Synthetic owned database; not all historical production shapes |
| Outer harness empty downgrade/upgrade | PASS | Empty disposable path only |
| Restored `alembic_version` | Exactly one `0037_access_boundaries` row | Restored custom archive |
| Restored `alembic check` | PASS: no model/schema drift | No new migration generated |
| Restored populated downgrade to `0031_in_app_notifications` | **REFUSED** by existing preservation guard; nonzero exit | Unsafe populated downgrade was not forced |
| Post-refusal data | Critical IDs, A/B grants/deny, source generation/fence/checkpoints, hold, history/evidence, incident and audit projections still equal to source | Selected synthetic fields/counts, not every possible legacy row |

The guarded refusal is the safe expected result. It is not a successful populated downgrade or a guarantee that every future migration preserves every production data shape. [Exact commands](VERIFICATION.md) and [restore comparisons](RESTORE_PRESERVATION.md) contain the reproducible boundary. Shared-resource associations remain the unresolved P0-03 design/migration dependency from [Sprint 12](../sprint12/SHARED_RESOURCE_AUTHORIZATION.md); no association migration was created.
