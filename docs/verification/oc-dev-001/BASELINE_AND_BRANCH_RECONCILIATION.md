# Baseline and branch reconciliation

Observed 2026-11-07T13:46:29Z. `git fetch origin main` completed; exact latest observed main **`ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`**, merge PR78. PR80 **OPEN / DRAFT / UNMERGED**, exact head **`958193f266c89302b2f1919e3703faece591e0af`**. Merge base is main itself. Audit-only branch `audit/oc-dev-001-full-product-reconciliation` starts from main in a separate worktree; it does not include or modify PR80 implementation. No reset/clean/rebase/merge/deploy or application/schema edit.

## Immutable comparison

[Provenance](BASELINE_PROVENANCE.json), [every changed path](BRANCH_CHANGE_INVENTORY.json), [complete inspected source/symbol index](SOURCE_SYMBOL_INDEX.json), [tracked path inventories](TRACKED_PATHS.json). Delta categories: {'AUTOMATION_OR_CONFIG': 23, 'APPLICATION': 24, 'MIGRATION': 4, 'EVIDENCE_OR_DOCUMENTATION': 2544}. Large evidence insertions are not treated as product features.

Main and PR80 share the same134-row Stage2A closure `requirements.json`; that register has not been updated for newer ETL implementation. PR80's56-row CI register adds24 non-overlapping IDs (ETL01–16 and LIC001–008). The audit union is **158 registered IDs**, including proposals/unrecovered historical IDs, not158 approved/implemented features. UI requirements retain approved canonical IDs even when overlapping a broader capability; each ID has one primary module and historical DEV ownership.33 numbered journey records are a separate crosswalk, not33 extra requirements.31 included;30 exact definitions unrecovered;20 excluded;32 skipped;33 partial licensing source.

## Material code present only in draft PR80

| Area | main | PR80 at pinned head |
|---|---|---|
| ETLWorkflow / ETLWorkflowDependency | No first-class models/API | models/entities.py; schemas/etl.py; api/etl.py; migration0039; authenticated scope/write enforcement and per-Workflow DAG locking |
| Temporal native binding | Not present | etl_bindings/models.py, service.py, api.py; migration0040; immutable historical versions and ownership constraints |
| Authority / writer protocol | Not present | authority.py, authority_api.py, writer.py; migration0041; signed contract/proof gates and23-table old-writer fence |
| Workflow configuration UI | Legacy ETL investigation/config only | pages/ETLWorkflowConfiguration.jsx, ETLNativeBindings.jsx, workflowConfiguration.js and authenticated browser harness |
| Verification/tooling | Existing Stage2A main evidence | OC-ETL002–008 scope/migration/DAG/UI/provenance/security evidence, pipeline checkout correction, CI traceability validator |

Generic resources/RBAC/telemetry/alerts/reports and profile/help already exist in main. A changed shared file in PR80 does not make its entire capability unmerged. `source_disposition` and `main_classification` in the requirements CSV separate this from the candidate classification. Old matrix phrases “Workflow editor absent”, “scope registry missing” or “unguarded DAG/downgrade” are historical at their recorded SHA, superseded for the bounded draft implementation by002–007 controlled evidence. None of those draft changes is silently credited to main.

## CI observations — not reruns

Main: **8 SUCCESS,3 SKIPPED,1 FAILURE** from MAIN_CI_SNAPSHOT.json. Failed `publish`, run42055504016, step **Verify exact current main and approved PR**, exit1; subsequent build/login/publication skipped. Full-log downloads returned empty output; annotations only show exit1 and Node20 deprecation. Exact failed assertion/root cause is unresolved. Do not infer an application regression, successful publication or harmless waiver. OC-DEV-503 diagnoses it without rerunning publication.

PR80: **18/18 SUCCESS** from PR80_CI_SNAPSHOT.json. The synthetic PR merge tree was previously verified identical to its branch head in the008 closure; passing controlled CI does not certify genuine providers or release.

Previous closure evidence contains failed attempts and later passes at different SHAs (e.g. TEST_EXECUTIONS sourcefa3a9a2). Those remain immutable historical results. Newly run bounded checks have separate logs and exact baseline IDs; no old PASS is relabeled as a new whole-product run.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
