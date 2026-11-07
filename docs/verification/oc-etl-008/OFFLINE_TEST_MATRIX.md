# Offline test and future acceptance matrix

## Executed synthetic preparation

Runner: scripts/pentaho-qualification-offline.py. New cases: backend/tests/test_pentaho_qualification_offline.py; input SYNTHETIC_FIXTURES.json. Every build/identity in these fixtures is invented test data, not a claimed genuine installation. Existing tests also parse historical supplied bytes without connecting to their origin.

| Case | Actual assertion / boundary |
|---|---|
| Success/failure/running | Existing normalizer preserves observed state; runtime_certified false |
| Missing/conflicting | Absent execution ID and conflicting native object scope rejected |
| Duplicate | Same record yields same scoped identity/key; no DB exactly-once claim |
| Stale | Parser can still parse old SUCCESS; expired authority proof refuses. Parsing is not freshness validation |
| Scheduler success | Scheduler claim stays UNKNOWN, never ETL execution success |
| Carte epoch/tenant | Changed epoch or tenant changes scoped identity; stable repository identity still unproven |
| Signature/alias | Test signature valid but unqualified; provider assurance escalation, tampering and duplicate aliases refuse |
| Strict schema | Unsupported schedule fields and TRANSFORMATION envelope object kind refuse |
| Endpoints | All5 candidate rows UNVERIFIED, exact build absent, live requests false |
| Retained source regressions | Pentaho R1, surface contracts, historical Carte parser tests and OC-ETL-007 envelope policy run unchanged |

Runner guards socket connect/connect_ex, DNS and subprocess creation throughout import/test execution. croniter's local architecture probe uses actual interpreter pointer width without external `file`. No SQL engine connection is made. A forbidden operation fails the run; it is not converted into a skip. These guards are test process controls, not an operating-system network sandbox.

## Prepared future PostgreSQL/authenticated cases — ALL BLOCKED / NOT RUN here

| ID | Future case and expected invariant | Required evidence |
|---|---|---|
| Q01 | Valid genuine proof + distinct authorized reviewer confirms exact stage | Approved exact-build target/issuer, original runtime evidence, scoped audit/DB snapshot |
| Q02 | Test/unapproved/expired/revoked proof cannot persist or confirm | HTTP/status and unchanged attestation/binding/qualification counts |
| Q03 | Native aliases of same object cannot gain two current owners | Independently proven aliases, concurrent requests, unique canonical target conflict, no partial versions |
| Q04 | Receipt admitted only against exact CONFIRMED immutable version/generation | Producer expected IDs, raw evidence hashes, binding receipt links, accepted attempts, distinct IDs/physical duplicates |
| Q05 | Stale/ambiguous/cross-tenant evidence and revoked roles denied | Authenticated requests, denial audits, unchanged rows; no raw loss or cross-scope leak |
| Q06 | Crash before/after commit and replay preserve accepted evidence | Independent source inventory and DB receipts; report missing/duplicate IDs; no exactly-once inference |
| Q07 | Expiry/revocation during commit and source replacement fail closed | Transaction boundary logs, generation/fence/lease/continuity proofs; active replacement remains blocked |
| Q08 | Historical versions/holds/audits survive backup/restore and refused unsafe rollback | Separate disposable populated PG, whole-content/schema hashes;0040/0041 guards unchanged |

Do not call these cases PASS or skipped success based on synthetic fixtures. OC-ETL-007 retained controlled tests are referenced historically, not rerun as genuine native certification. This preparation task makes no DB, browser integration, live qualification or deployment claim.


**Offline preparation only. Genuine qualification BLOCKED / NOT RUN. CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
