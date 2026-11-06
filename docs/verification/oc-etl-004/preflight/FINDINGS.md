# OC-ETL-004 preflight — 2026-11-05

Verified clean baseline a420dbc12e66196e00832f450d46a739b7cd0e99 on dev/post-pr78-architecture-closure-20261105. PR80 remains draft.

Hosted failures are attributable to OC-ETL-003 integration:

- pipeline-contracts run 42095133058: 14 transport tests and nine HTTP acceptance groups passed, then scripts/v16-acceptance.py:464 rejected the new central populated-downgrade error because its expected error-message list contains only historical revision guards. Repair must retain nonzero exit and independently verify preservation, not merely relax success criteria.
- staging-smoke run 42095133805: phase1-staging.yml uses `alembic downgrade -1`, explicitly unsupported by the new migration preflight. Use a resolved explicit previous revision and preserve the actual downgrade/upgrade checks.
- Current dependency audit and secret-history jobs passed. This is not independent security clearance; SECURITY remains BLOCKED.

Raw hosted logs are adjacent. No UI implementation or new runtime tests have been completed in this continuation. Workflow schemas currently support timezone/weekdays/windows/duration/SLA; arbitrary recurrence and child long-running thresholds are absent from the inspected contract and cannot be invented.

Next: repair and execute affected CI acceptance paths, inspect configuration ownership/navigation and evidence from OC-ETL-002/003, implement Workflow/Job UI and backend-confirmed readiness, then run authenticated browser/PostgreSQL acceptance. No owner acceptance inferred.

CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.
