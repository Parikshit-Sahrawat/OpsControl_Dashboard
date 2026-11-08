# Severity, dependency and minimum closure sequence

| Priority | Blocker | Depends on | Owner/review role | Relative complexity / disposition |
|---|---|---|---|---|
| P0 acceptance | Previous visual candidate rejected; revised desktop directory/filter/table parity and owner review | Current correction evidence | Frontend/verification; product owner for actual visual acceptance | M; implementation tested separately, no automatic acceptance |
| P1 Sprint1 | Typed template applicability, unknown/legacy/resource-change behavior | S01-D1 | Product/architecture + backend/runtime/security | M–L; policy then shared enforcement, not just frontend filtering |
| P1 Sprint1 | Complete immutable attachment/override/effective history, trusted authorship | S01-D2; existing stores review | Architecture/DB/security + backend | L; additive schema/constraints/backfill/restore tests |
| P1 Sprint1 | All-writer stale-intent prevention and full-save failure contract | S01-D3 + history boundary | Backend/DB/security + frontend | L; source-owned transaction/fence or explicit staged outcomes |
| P1 Sprint1 | Consistent authoritative draft preview/revision/apply provenance | D1–D3; D4 scope | Backend/runtime/frontend | M–L; connect existing authorities, no automatic telemetry success |
| P1 Sprint1 scope | History retrieval/diff and safe configuration rollback contract | D2/D4, authentication/RBAC | Product/architecture/security/DB | M; history first; runtime application remains separately gated |
| P1 integration dependency | Eventual PR80 native-binding/migration convergence | Reviewed combined candidate / writer ownership | ETL/backend/DB/security | L; unmerged branch not imported; not prerequisite to ordinary VM UI correction |
| P0 release (independent) | CHK001 loss; CHK002 rollback; security clearance | Independently verified fixes/qualifications | Runtime/security/release owner | Unresolved; no waiver. Do not turn into fake Sprint1 PASS or infer all configuration behavior failed |
| P1 later Sprint2+ | Actual pinned binary/OS/agent installation, reader acknowledgement, genuine provider qualifications | Authorized isolated runtime/provider target; exact build | Runtime/provider/verification owners | L; two runtime tests currently skipped. Not simulated by UI |
| P1 later ETL scope | D07 recurrence/calendar/DST; D08 long-running and ETL override semantics | Exact owner authority | Product/ETL architecture | Decision-dependent; not ordinary resource configuration blocker |

Execution order:

1. Review corrected desktop evidence and source-mapped existing behavior; keep rejected/pending acceptance explicit.
2. Select exact D1–D4 contracts and assign accountable reviewers. Preserve original architecture/ownership rather than creating duplicate owners.
3. Implement one reviewed additive configuration revision/history/cutover boundary with compatibility tests. No destructive rewrite/backfill of unknown history.
4. Enforce applicability and stale-intent protection across every existing writer; preserve tenant checks, revoke-at-commit and rollback guarantees. Resolve atomic/staged user semantics.
5. Connect version-aware preview/validation/current history to the shared Resource Management UI; expose only supported apply/rollback controls.
6. Execute T1–T6/T8 PostgreSQL/API/browser/failure suites; rerun existing resource/security/restore regressions; preserve failures, source hashes and scoped cleanup. T7 runtime evidence remains in explicitly authorized collector sprint where appropriate.
7. Review all Sprint1 criteria and exact screenshots with owner. Explicitly accept, reject or approve a bounded deferral; **do not mark Sprint1 complete while required history/applicability/compatibility work is merely proposed**.

No calendar estimate is promised. M/L describe relative engineering/test complexity, not authority approval. Open-source self-hosted deployment targets (Kubernetes/Windows/Linux Server) do not reauthorize excluded Kubernetes workload monitoring. No deployment work occurs here.
