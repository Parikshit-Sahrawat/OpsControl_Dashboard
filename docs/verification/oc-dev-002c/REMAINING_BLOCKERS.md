# Remaining blockers and next bounded work

Review date: 2026-11-08 (Asia/Calcutta). Execution logs retain their original UTC timestamps. Tested source `80835f0065de24ebf271fc621b6d1e5e83d73bd2`; main `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`.


1. Structured template applicability: exact versioned org/resource/OS/environment/collector rule and unknown/legacy handling not approved. Do not parse scope prose into policy.
2. Immutable attachment/override/effective history: no timeline model. Need approved snapshots/retirement/retention/holds, forward additive schema, old-writer fence and restore/rollback contract. Current changes protect pins and opt-in concurrent edits only.
3. Full workflow acceptance: every collector method, full keyboard-only creation and exact global-tenant switching during each template save boundary remain NOT TESTED. New edit/save, reload, local A/B race and revocation cases are narrower.
4. Original browser reload timeout not reproduced; cause unknown, no owner non-blocking disposition. New synchronization failures separately explained.
5. RM-DEF-036 not reproduced under bounded matched workloads; tail latency grows, no fix claimed. All-page polling, long duration, full SQL plans, fleet cardinality and non-API CPU/Windows profiles remain missing.
6. PR80 runtime convergence/older-writer rollback: three textual conflicts, no approved combined source or merged migration graph; no cherry-picks or fabricated schema compatibility.
7.30 included numbered journeys SOURCE_NOT_RECOVERED. Service Catalog excluded; Journey32 skipped/Kubernetes product monitoring excluded. Supplemental cleanup cannot infer deletion from missing definitions. No new legacy removal qualified.
8. Nine owner selections and D07/D08 Pending; genuine Pentaho/Windows/EC2/provider qualification and independent UAT not performed.201 spool contract pending review;101 NOT STARTED. Independent reliability/security/license/image gates remain unchanged, no waiver.

Next bounded task requires explicit approval: settle versioned applicability/history decisions and implement the reviewed additive history contract after branch-convergence design, with all-writer concurrency, replace/retire, historical snapshot and backup/restore tests. Do not start OC-RPM-001, OC-DEV-003 or OC-DEV-101 automatically. No overall development closure or later checklist step certification.


**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
