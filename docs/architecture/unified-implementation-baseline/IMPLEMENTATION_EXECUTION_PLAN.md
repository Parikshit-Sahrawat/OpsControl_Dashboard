# Implementation Execution Plan

Baseline: PR #80 source `e69528ad2b826398474382f34126feeca740f6a6`; main/merge-base `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`. Working branch `dev/post-pr78-architecture-closure-20261105`. Assessment date: 2026-11-05. Source presence, controlled verification, genuine-provider certification and owner acceptance are separate dimensions. No product code or migration is changed by OC-ARCH-001.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.** Journey 20 Service Catalog excluded; Journey 32 Kubernetes/container observability skipped. No provider execution, scheduler writes, job retry/termination controls, merge or deployment.

## Preserve the existing milestone

PR80 already contains these logical increments (full SHAs in evidence/pr80-milestones.txt):
- 2ca97bf/7050a73/7f8ed28: ETL clear-filter fix and test wiring.
- 5be08d2/ec92787/d6b10be/1cc1d66/fdd0ab6: model, migration 0039, schema, workflow API and exports.
- 2ec78e9/0851e3d/485bffc: route guards, HH:MM validation and model checks.
- ad2e8a1 plus operations/pentaho migration probes: historical-schema fixture compatibility.
- 253e878/05d8915/5bc503b: workflow partial edit/detail and validation tests.
- 3408fe3/b105160/63ffddd: child-job updates, read-only monitoring projection and safeguards.

These are implemented foundations, not completed HTTP/DB acceptance. Preserve nullable legacy linkage and migration history. This task adds baseline documentation and focused evidence only; no continuation is authorized to ignore CF-01 or destructive downgrade risk.

## Next executable Codex tasks

1. **OC-ARCH-001-B01 — Scoped workflow foundation repair.** On this branch, reproduce CF-01 with authenticated disposable PostgreSQL; register safe parent/org scope and resource restrictions, audit atomicity, immutable references and concurrent DAG integrity. Keep all deny-by-default controls. Exit: authorized create/edit succeeds; forged tenant/role/parent/empty scope denied; two concurrent cycle edges cannot both commit; no production/UAT access. Preserve existing 16 tests and add actual integration tests. Do not implement events/UI until this foundation is usable.
2. **OC-ARCH-001-B02 — Workflow migration and legacy-policy compatibility.** After B01, prove fresh and populated 0038→0039 preservation and backup restoration; refuse populated rollback before data loss; design non-destructive assignment for legacy jobs without inferred grouping. Never rewrite an applied schema revision. Exit: independently compared hashes, required FKs, audit/history preservation, documented reversible or explicitly bounded recovery. Stop destructive portions if ownership/export authority is ambiguous.
3. **OC-ARCH-001-B04 — Existing configuration-plane workflow editor.** After B01/B02, implement Workflow timing and child Job duration UI with reload/error/tenant/RBAC tests; reuse configuration ownership and read-only monitoring pages. No independent Task, Service Catalog, Kubernetes or external job execution controls.
4. **OC-ARCH-001-B03 — Native read-only source contract.** In parallel with B04 only after exact sanitized schema/identity decisions are supplied, implement/test mutable row polling against controlled Oracle/MSSQL/log fixtures and native IDs. Genuine-provider certification remains separately authorized. B05→B06→B07 follows persisted source identity and policy authority; never use a fake final-state-only fixture to prove RUNNING updates.
5. **OC-ARCH-001-B00/B09 — Source and licensing decisions.** Recover exact missing journey, licensing and v1.7 catalog/override definitions. Do not map titles by intuition. Only then create requirement-specific implementation tasks; source gap is not permission for redesign.

## Milestone controls

For each logical code commit: record exact requirement IDs and baseline, run relevant focused tests, preserve failures, then integration/negative authorization/migration checks. At UI milestones add actual browser evidence. At native milestones reconcile source inventory with persisted receipts, duplicates and missing IDs. Run applicable existing CI at milestone; do not equate it with owner/provider certification or weaken assertions. Update the existing register by appended evidence and this matrix, rather than creating competing approved requirements.

Owner product/architecture decides unrecovered contracts; backend/security owns scope and audit; DB owner signs migration/recovery procedure; provider owner supplies source/build access; independent verification reviews execution; legal/license owner adjudicates licensing obligations. These are roles, not fabricated named approvals.

Keep PR #80 draft. No PR merge, live deployment, branch-protection changes, security waiver, collector version change or gate promotion. No reason to rerun expensive passing suites for documentation-only edits; record current focused checks and explicitly mark integration not executed. Completion of this baseline means implementation planning is reviewable, not that 31 journeys or ETL are accepted.

