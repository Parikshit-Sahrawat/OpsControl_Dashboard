# Authorization and revocation

Review date: 2026-11-08 (Asia/Calcutta). Execution logs retain their original UTC timestamps. Tested source `80835f0065de24ebf271fc621b6d1e5e83d73bd2`; main `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`.


Existing principal scope/write hooks, transaction_authority and permission catalogue unchanged. Attachment POST/PATCH/DELETE validate the scoped source; all serialize on that source row. PATCH confirms available committed version and refuses enabling a disabled template. Revision checking is optional for older clients; new editor and existing DataSource wizard send the exact observed timestamp. Concurrent protected edits yield one200 and one409. No global database-wide new lock was introduced.

Core HTTP15 groups include viewer403, other-customer denial, protected-field422, disabled-parent collector409, real PostgreSQL revocation/update ordering (401/403 with no committed change) and stale-session401. New transaction-failure trigger applies only to priority98765 in the disposable database and is dropped in finally; expected500 is a negative test, followed by identical persisted-state/effective-config reads. No production guard is bypassed.

Retained Sprint08 real HTTP14 groups and browser5 groups cover direct/inherited/delegated permissions, customer/environment/resource boundaries, department-versus-customer separation, revocation cache invalidation and restricted selectors. Combined backend110 executions include42 retained suite cases; imported fixtures overlap. New Resource browser demonstrates session revocation while unsaved editor is open, sign-in replaces editor, stale authenticated update401 and original persisted name intact.

Audit continues through existing hooks in the mutation transaction. Existing audit immutability/rollback tests remain in broad release. No granular audit-history approval or independent security certification is inferred. Full arbitrary race schedules and every route are not certified by these cases.


**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
