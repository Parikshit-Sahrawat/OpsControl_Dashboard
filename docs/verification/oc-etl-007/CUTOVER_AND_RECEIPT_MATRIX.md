# Cutover and receipt provenance contract

Current source UUID/generation, fence/owner/mode/lease, checkpoint, reader-equivalence and continuity/legal/manual holds are unchanged. Monitoring configuration never invokes a provider workload.

| Boundary | Required/implemented behavior | Qualification boundary |
|---|---|---|
| Unqualified Stage | One current claim reservation; no automatic collection/activation | Retained real PostgreSQL/HTTP/browser cases |
| Envelope preview | Typed references, exact source/method context, signature/time checks | Test-only crypto positive is NOT provider qualification |
| Confirm | Independent reviewer, current runtime proof plus genuinely qualified signed native authority; append version/qualification/audit atomically | Conditional implementation; genuine positive BLOCKED/NOT RUN |
| Canonical aliases | Signed canonical tuple maps aliases to one target key; unique current qualified owner | Contract math/negative paths tested; actual qualified alias admission BLOCKED |
| Admit new receipt | Existing ticket validated before protocol marker; current confirmed binding, generation/reader/proof; original raw hash/key and immutable version link in one transaction | Unqualified/raw negatives and legacy DB fence tested; positive qualified projection BLOCKED |
| Replay | Existing source/generation/external_key and payload digest retained; never attach an old duplicate to a new version | Existing dedup regressions retained; qualified-version replay NOT RUN |
| Expiry/revocation | New admissions fail validation; deferred constraints prevent expired/revoked confirmation/receipt commit; prior accepted histories retained | Crypto clock/revocation negatives tested; genuine admitted-positive lifecycle BLOCKED |
| Initial opt-in race | Job row lock serializes old writes with registration; earlier acknowledged record stays historical/unattributed | Real PostgreSQL transaction plus authenticated stage request |
| Staged same-target reader replace | Existing per-Job/claim uniqueness, source snapshots, expected generations and no leases/holds/active reader | Retained concurrent cases; no global lock added |
| Confirmed retirement | Only quiescent configuration; close binding/qualification together and retain historical target/proof/receipts | Conditional implementation; qualified positive NOT RUN |
| Active/stale generation cutover | Refuse until independently reviewed authority/continuity and complete transaction boundary evidence exists | **BLOCKED**; no new live handoff bypass or silent rebase |
| Old writers | DB fence persists across process restart/restore; no accepted projection or checkpoint survives refused batch | Exact old source APIs and direct SQL tested |
| Aggregate Workflow | Configuration/binding/connectivity/freshness/health separate; positive receipt alone cannot make ACTIVE/HEALTHY | Always activation BLOCKED; health UNVERIFIED absent qualified evidence |

Source-row locking serializes normal admission with source changes/revocation. Active replacement has not been qualified; do not extrapolate quiescent locks or ordinary restarts to arbitrary crash cuts, multi-source live atomicity, zero-loss collector queues or exactly-once execution. CHK-001/002 remain unchanged. External trust-file changes require drain/revocation procedure; no distributed filesystem/DB atomicity is claimed.
