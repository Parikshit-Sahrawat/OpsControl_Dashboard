# Implementation matrix

| Workstream | Implemented / verified | Disposition and limits |
|---|---|---|
|103 authorization | Strict ownership/null PATCH validation; disabled-parent create/enable guard; retained role catalog. Actual viewer/cross-customer denials; role mutation revokes session; PostgreSQL queued revocation precedes attempted write, no committed mutation; retained direct/inherited/delegation/grant tests | BOUNDED VERIFIED; exact paths/cases in AUTHORIZATION_REGRESSIONS.md; no whole-product certification |
|105 Resource Management | Existing actual UI create/edit/reload/disable/re-enable, preserved collector ID/config and count reconciliation; invalid duplicate input; narrow viewport/focus; modal closure on tenant/auth revision change | PARTIAL: exact delayed A/B-switch configuration-modal browser case and complete keyboard form traversal not executed |
|106 templates | Ordinary resource edits preserve immutable pin; failed attachment read propagates; package shapes/null fields validated; inactive attachment denied; source lock serializes attach; template lock serializes version commits; real v1→v2/v3/v4 and effective required attributes/overrides | PARTIAL: structured applicability contract and immutable attachment/override selection history not implemented; full browser template-version editing scenario not executed |
|121 preservation |100 tables equal after dump/restore by rows/hash/columns/FKs;499 constraints in separate release restore; unsafe downgrade, corrupted archive, overwrite/nonempty restore and transaction rollback cases | Main0038 BOUNDED VERIFIED; PR800039–0041 convergence BLOCKED, no migrations copied/renumbered/applied |
|135 responsiveness | Real authenticated OTLP and3 authenticated read paths concurrently with browser navigation; before/after distributions, query plan, dedup/rejection accounting and recovery | NOT REPRODUCED at this workload; SQL request counts and CPU/memory/global representative profiles NOT MEASURED; not fixed/certified |

Application/configuration commits: c6e20718f727da88fc6972e583cee0470a7eacfd and final null-validation increment c4c773601c53d0c8f44fdcb51b447c7664fb6eb8. Test increments bde03e4,a20e1f4,d5926d9 are preserved. Exact final runtime source c4c773601c53d0c8f44fdcb51b447c7664fb6eb8; evidence commit adds no application behavior. No permission/migration/collector pin changes.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
