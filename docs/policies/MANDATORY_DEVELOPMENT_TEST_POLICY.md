# OpsControl mandatory development test policy

Status: PRODUCT-OWNER APPROVED. Source: owner instructions in the OC-DEV-COMP-000 conversation, 2026-11-08 Asia/Calcutta, followed by explicit direction to apply the policy globally to OpsControl. This is the current global development policy across every subsystem, not only ETL or development-completion planning. Applies to OC-DEV-COMP-000 and all subsequent development-completion sprints and other development changes. Historical evidence is retained at its original source/version; this policy does not retroactively certify it.

1. Run automated unit, integration, browser, security and applicable controlled fault-injection tests DURING development, before sprint acceptance.
2. Use a real PostgreSQL instance, production-representative schema and migrations for persistence, transaction, migration, tenant-isolation and recovery contracts.
3. Test running FastAPI and React/Vite application components with actual HTTP interfaces, real database persistence and Playwright for browser workflows.
4. Use real component boundaries for telemetry ingestion, collector interoperability, alert processing and notification durability wherever certifying those contracts.
5. Mocks and synthetic fixtures are allowed for isolated tests but cannot replace integration evidence or establish genuine-provider certification.
6. Record test command, environment, source commit, results, failures, skips, logs, artifact hashes and known limitations.
7. Run controlled failure scenarios including crashes, restart, replay, duplicates, partial failure and tenant isolation where applicable.
8. Do not mark a requirement verified or sprint accepted without sufficient evidence. Do not hide failures, assume unavailable tests passed or silently waive security gates.
9. Formal owner UAT remains a later phase and does not replace development testing.
10. Keep CHK-001 FAIL, CHK-002 BLOCKED, SECURITY BLOCKED and release NO-GO until independent evidence supports an authorized gate transition.
11. No merge to main until the final development-completion integration review and explicit approval.

## Evidence and gate application

Each sprint must declare the exact source/migration baseline, in-scope contracts and applicable test boundaries. Separate test definitions, executed results, synthetic integration, genuine-provider qualification and owner acceptance. An unavailable mandatory boundary is BLOCKED/NOT TESTED with a precise prerequisite; a skip is not PASS. Run bounded, task-owned test environments, preserve failed attempts and redacted artifacts, then clean only allocated resources. Do not use production/shared UAT data or real provider credentials without separate target authorization.

The centralized PostgreSQL spool remains an architecture decision until implemented and verified. Existing collector pin and reliability/security gates are unchanged. This policy authorizes development tests, not release, merge, deployment, formal UAT or genuine-provider qualification. Preserve CI Trigger-and-Exit where required: after final local verification and push, record available workflow links/results pending and stop; never poll for completion.

## Approved execution-program alignment

The [owner-approved program v1](../planning/OC_DEV_COMP_PROGRAM_2026-11-08.md), source commit8a09bd142fb6dbf7a79b131c0490e67e8de3fde0, governs the precise Sprint0–10 sequence. Its security baseline explicitly includes dependency/image vulnerability scans, secrets and applicable supply-chain checks. Actual findings, absent scanners, unavailable immutable image identities or missing provider environments remain failed/blocked/unexecuted evidence, never clearance. This applies across all OpsControl subsystems. No intermediate sprint merge into main; final development-completion review and explicit owner approval are prerequisites.
