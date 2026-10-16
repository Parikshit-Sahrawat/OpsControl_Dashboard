# ARCH-ETL-001 V1.6-R1 — Sprint 05

Scope: explicit schedule authority, bounded retained-evidence reconciliation and
historical failure notices. Branch `feat/arch-etl-001-v16-r1`.
Baseline `289021a39cfe017208abc4d71a33dba3247fae54`.
Delivery SHA: the commit containing this report (`git log -1 --format=%H -- <this file>`).
No PR, merge, deployment, real-source activation, vendor access or production operation.

Controlling specification `docs/architecture/ARCH_ETL_001_V16.md` is unchanged:
SHA-256 `ed8af0f9c3fce3375d0375e2431bdf43567133943551b2c0bc9f0b9882ab5446`.

## Implementation

### Schedule authority and occurrence monitoring

The existing immutable ParameterVersion, calendar/DST helper and
ExpectedExecutionWindow are reused. Pentaho selects VERIFIED_SCHEDULER,
MONITORING_EXPECTATION or MANUAL explicitly. Unset legacy authority remains UNKNOWN;
a configured expectation is never silently treated as a native scheduler.
Other eight platform scheduling/adapter semantics are preserved.

Native mode requires a current independently approved exact-build/reader capability,
explicit SCHEDULE authority, matching customer/job/source generation, proof evidence,
revision, calendar and a fresh bounded export. Native occurrence IDs come from that
export; no PID/name/timestamp heuristic invents scheduler identity. Read-only
observation normalization accepts a typed schedule_evidence export, not a new or
assumed Pentaho Server endpoint. Export parsing or connectivity does not certify it.

Each occurrence freezes authority/calendar/timezone/DST/revision/grace/proof
provenance. Invocation observation, attempt outcome, completeness, source health
and schedule compliance remain independent. States include PENDING_GRACE,
OBSERVED, DELAYED, NO_RUN, UNKNOWN and INCOMPLETE. Native mode matches native
schedule occurrence aliases; configured monitoring mode uses a calendar window for
compliance only, without merging execution identities or attempts.

NO_RUN requires persistent healthy coverage from before the expected occurrence
through grace, current eligible readers/generation/continuity and fresh complete
acceptance receipts. This last requirement prevents partial-file tails and
incomplete/advisory inventories from proving absence. Holds, failed operations,
stale/inactive/unhealthy sources and coverage gaps suppress new NO_RUN assertions.
Coverage resets rather than guessing after restart/outage. Proven historical misses
remain recorded during later outages; verified late invocation evidence can
reconcile them independently of execution outcome. Evaluation is capped at 200
windows per resource cycle; no load/capacity guarantee is implied.

### Bounded replay and continuity

Existing PipelineOperation RECOVERY plans, current source leases/fences, method
eligibility, holds and the canonical reducer are reused. Optional mode
ACCEPTED_PENTAHO_EVIDENCE re-reduces only retained, accepted, integrity-verifiable
normalized native records in the requested **event-time** range. Original
occurrence, observation, raw acceptance and ingestion/discovery times remain separate.

This is not a provider history fetch, file rewind or a continuity proof for missing
native ranges. Pentaho provider replay returns UNSUPPORTED by default, including
Server/Carte/file capabilities lacking genuine continuity/range evidence.
`coverage_status=ACCEPTED_RECORDS_ONLY_NO_GAP_CLOSURE` explicitly prevents claiming
missing gaps recovered. Existing gaps and physical checkpoints are not cleared.

Requests need existing ETL configuration access plus explicit customer-scoped
etl.replay. Outside existing method bounds (File Log six hours; platform/database
24 hours), a different currently authorized reviewer needs etl.approve_replay plus
existing ETL configuration access. Neither new permission is granted implicitly.
Risk, current grants, generation and holds are checked again at execution.

Live collection has priority; replay yields if a live poll is due. Each transaction
handles at most 50 records; global dispatch is bounded to eight recovery operations
and orders by prior lease to avoid one range monopolizing work. A separate durable
reconciliation_cursor lives on the recovery operation. Source live_checkpoint and
method-specific recovery_checkpoint remain unchanged. They cannot be replaced by
an event UUID cursor.

Cursor, projection and notice changes commit atomically after fence revalidation.
Unresolved evidence remains under review. Failed preparation rolls back; fenced
cleanup cannot release a replacement owner or overwrite its operation. Replay
failure does not mark live source health failed. Unprovable ranges stop as
UNRECOVERABLE until the existing reviewed retry/new-evidence mechanism. All active
holds compose; no bypass for held backlog was added. Retained evidence can be
reconciled only after applicable holds and continuity gates permit it.

### Historical failure reconciliation and notifications

The existing native identity/attempt/revision reducer is reused. A late terminal
FAILED execution must have confirmed invocation identity, verified completion and
finality, durable build/source/fence/integrity evidence and no queued or unqueued
conflicts. A failed retry still waiting for authorization is not a final failure.
A manual recovery execution does not rewrite the failed original.

Historical metadata records occurrence, later discovery and evidence reference,
with explicit operational reassessment and notification eligibility. Classification
precedes live incident-condition evaluation. Historical failures and reviewed
corrections cannot silently re-open closed/resolved incidents or change unrelated
current executions. Existing incident records, associations and correlation evidence
remain; full incident/recovery reassessment belongs to Sprint 06.

A durable obligation is unique per execution/destination. Its immutable payload is
classified HISTORICAL_FAILURE and does not fabricate an AlertState. It retains
resource/execution identity, occurrence/discovery timestamps and evidence references.
A persisted round-robin historical scan (200 histories/pass) prevents old unresolved
rows from permanently starving newer histories. Creation and replay are idempotent
across duplicate ingestion, retries and worker restart.

Delivery is opt-in through customer-scoped policy and existing configured
destinations. IN_APP requires explicit users/teams, current alerts.view grants,
active accounts and enabled preferences; zero eligible recipients is not reported
as sent. The existing inbox supports an alternate scoped historical origin while
preserving old live-alert origins. Eligibility and delivery token are rechecked
under the canonical job lock before in-app persistence. Unique notice/recipient
keys prevent duplicate in-app messages.

Existing TLS/allowlisted/secret-reference destination adapters are reused for
SMTP/webhook compatibility. **No external email/webhook was sent.** Tests use real
local in-app persistence and controlled timeout/error injection. Remote provider
acknowledgments cannot be made atomically with database commits: SMTP/external IO
remains at-least-once, with stable IDs rather than an external exactly-once claim.

The existing worker prioritizes live alert delivery, then up to five historical
obligations. Short fenced leases, five attempts, bounded backoff, sanitized errors,
status and audit are persisted. Exhausted expired claims become FAILED. Conflicted,
revoked or disabled obligations block. Historical-worker failures are reported and
isolated from live alerts. Native ETL workload controls were not introduced.

## APIs and migration

- Existing `POST /api/v1/unified/parameters/{resource_id}` and preview/version
  activation contracts accept pentaho_schedule_authority; native proof checked
  server-side. `GET .../resources/{id}/schedule-windows` returns occurrence provenance.
- Existing `POST /api/v1/data-pipelines/sources/{id}/recovery` supports optional
  mode ACCEPTED_PENTAHO_EVIDENCE. Existing operation status/independent approval and
  reviewed retry endpoints are reused. Source/customer authorization is enforced.
- `PUT /api/v1/unified/resources/{id}/historical-notifications`: strict enabled,
  destination_ids, historical_after_seconds, expected_revision, idempotency_key;
  requires templates.manage and etl.configure. Destinations/recipients scoped and
  checked; duplicate save idempotent, stale revision fails.
- `GET .../historical-notifications`: paged policy/obligation status and retry details,
  requiring customer alerts.view. Existing `/api/v1/notifications` returns personal
  historical entries with classification/evidence and alert_state_id=null.

Additive migration `0035_pentaho_history`, parent `0034_pentaho_review`:

1. Nullable immutable Pentaho authority snapshot on existing expected windows.
2. Scoped historical notice table with history/event/destination FKs, unique
   execution/destination identity, lease/retry/status fields and immutable payload.
3. Existing in-app inbox supports either live delivery_id or historical_notice_id
   with exactly-one-origin constraint and customer-scoped historical FK.
4. Two explicit-grant replay permission catalogue entries; no implicit roles/grants.
5. Database guards protect occurrence identity, historical notice and inbox evidence.

No historical migration was edited. Populated old customer/user/hash/history,
raw evidence/legal hold and R1 attempts/aliases/revisions survive. A dedicated
0034→0035 probe also preserves old alerts, delivery/inbox messages and schedule rows.
Schema comparison is clean. Empty downgrade/upgrade succeeds; populated downgrade
refuses before erasing evidence or cursors. For rollback retain compatible schema
and revert compatible application code, or restore a separately verified backup.
Do not delete evidence or disable guards to force downgrade. Only disposable owned
PostgreSQL was migrated; no user development/production database was modified.

Legal holds and existing source retention continue to protect raw/revision history.
Historical notices/inbox/occurrences are conservatively pinned against deletion,
including when a source is retired. This has storage costs; archival/release policy
is not invented here. Existing physical cursor retention and audit rules remain.

## Verification and acceptance

Controlled fixtures model native authority; none are genuine installed Pentaho
acceptance. Evidence files record the actual final commands and outcomes.

| Check | Actual result | Evidence |
| --- | --- | --- |
| Deterministic and adapter/RBAC/monitoring regressions | PASSED — 160 tests, 0 failed, 0 skipped | unit.txt |
| Owned PostgreSQL combined regression | PASSED — 127 tests, 0 failed, 0 skipped | postgresql.txt; 101 prior + 26 Sprint 05 tests |
| Existing authenticated HTTP | PASSED — 9 groups | api-existing.json |
| Sprint 03/04 authenticated HTTP | PASSED — 4 + 5 groups | api-sprint03.json, api-sprint04.json |
| Sprint 05 authenticated HTTP | PASSED — 4 groups | api-sprint05.json |
| Migration/schema/preservation | PASSED | migration.json, preservation.json, review-preservation.json, history-preservation.json; single head 0035_pentaho_history |
| Imports/mappers/routes, Black, scoped Ruff correctness, compilation, whitespace | PASSED | static.txt |
| Genuine Pentaho RT-001–RT-020 | NOT RUN — all 20 | No separately authorized native installations/evidence |
| Live nine-platform acceptance, production, external mail/webhook, load/failover | NOT RUN | Controlled local lab only; no production-readiness certification |
| Frontend/browser/full image build | NOT RUN | No frontend/deployment source modified; UI remains later scope |

Commands (existing .venv; no dependency installation required):

```sh
# From backend:
ENV=test .venv/bin/python -m unittest \
  tests.test_pentaho_history_contracts tests.test_pentaho_review_contracts \
  tests.test_pentaho_execution_contracts tests.test_pentaho_r1 \
  tests.test_pentaho_surface_contracts tests.test_pipeline_adapters \
  tests.test_pipeline_transport_v16 tests.test_pipeline_runtime_v15 \
  tests.test_unified_monitoring tests.test_unified_v15_contracts \
  tests.test_access_control tests.test_in_app_notifications \
  tests.test_native_incidents_v15 -v

# From repository root: disposable PostgreSQL + actual authenticated FastAPI
V16_PENTAHO_R1_ACCEPTANCE=1 V16_PENTAHO_REVIEW_ACCEPTANCE=1 \
V16_PENTAHO_HISTORY_ACCEPTANCE=1 V16_API_ACCEPTANCE=1 \
V16_EVIDENCE_DIR=/tmp/sprint05-delivery \
backend/.venv/bin/python scripts/v16-acceptance.py
```

A final focused follow-up reran 26 Sprint 05 PostgreSQL tests (0 failures/skips)
and all 22 HTTP groups. The primary 127-test gate includes the actual fence-41/42
ownership race; the focused follow-up does not claim to rerun that race.
A final HTTP extension also executes an independently approved accepted-evidence
plan through the actual worker, verifies unchanged live cursor, then delivers the
resulting obligation to the authorized inbox. Native/provider IO is never used.
The runner starts/removes only its own PostgreSQL 17 container and local API process;
existing deployments/volumes remain untouched. Restricted socket sandbox execution
required the existing authorized elevated runner. No runtime environment settings,
credentials or dependency manifests were changed.

Required acceptance mapping (`backend/tests/test_pentaho_history_r1.py` unless noted):

| Requirements | Executed coverage |
| --- | --- |
| 1–2 authority modes | verified native/freshness and explicit expectation tests; HTTP forged authority rejection |
| 3 DST/timezone | `test_pentaho_history_contracts.test_spring_gap_skipped_and_fall_fold_is_explicit` |
| 4–5 grace and false NO_RUN suppression | expectation/grace, unhealthy/suspended, incomplete-poll and composed-hold tests |
| 6 independent occurrence/attempt/outcome | `test_schedule_occurrence_does_not_claim_attempt_success` |
| 7–12 held/replay/bounds/fencing/unsupported/fair share | replay cursor, beyond-bound approval, priority/holds, stale fence/generation, provider unsupported, batch resume, safe preparation failure/stale cleanup; existing ownership fence-41/42/atomicity regressions |
| 13–15 late failure/time/dedup | historical obligation, distinct occurrence/discovery and repeated reconciliation tests |
| 16 retry/audit | real local in-app delivery, timeout/retry, stale completion, recipient revocation; authenticated inbox |
| 17 conflict suppression | conflicted failure and queued identity-quarantine cases |
| 18 incident preservation | closed incident remains closed; late failure never drives live incident conditions |
| 19 customer scope | authenticated policy/native-proof/replay approval tests; prior IDOR and composite FK regressions |
| 20 holds/migration | notice/inbox/occurrence immutability; old and new migration preservation probes |
| 21 eight-platform compatibility | existing adapter/runtime/inheritance/correlation/security suites |
| 22 no controls | scoped backend/OpenAPI checks and unchanged read-only adapter/control exclusions |

Initial failures were corrected without weakening assertions: test fixtures now
respect immutable parameter versions, use matching native job proof identity and
isolate delivery claims by owned customer. Zero-recipient delivery now fails
explicitly. Hold tests verify continuity before releasing one reference and retain
the other hold. Full coverage additionally requires complete poll receipts rather
than merely healthy/idle status. Existing `utcnow()` deprecation warnings remain
outside this slice. No required final test failure was suppressed.

## Changed modules, cleanup and limitations

Changed source: unified schemas/models/API/engines, Pentaho execution extensions;
new pentaho_schedule.py, pentaho_replay.py and pentaho_history.py; pipeline
service/API/runtime; Pentaho observation normalization; permission catalog/route/
ORM scope; notification models/inbox/delivery/worker; migration 0035. Tests/tooling:
new test_pentaho_history_contracts.py, test_pentaho_history_r1.py,
pentaho_history_migration_probe.py, pentaho_sprint05_http_probe.py and extended
scripts/v16-acceptance.py. Documentation: ARCH-001_IMPLEMENTATION_STATUS.md,
docs/ARCH_001_V16.md, docs/architecture/ARCH_001.md and this report/evidence directory.
`changed-files.txt` and `source-sha256.json` give the exact inventory and source hashes.

Targeted cleanup removed only the unused private `_post_json` helper referencing
undefined `_notification_open`; targeted caller search found no consumers. Existing
active SMTP/webhook adapters use validated pinned egress. No adapter, canonical
execution engine, migration or historical record was removed or rewritten.

Remaining limitations: native provider/file replay and scheduler export producers
still need genuine version-specific implementation/acceptance where unavailable;
no invented Server APIs or file continuity proofs. Retained-evidence reconciliation
cannot recover missing/retired/unverifiable payloads or close native gaps. Historical
scan/reference bounds and conservative receipt coverage can leave old windows
INCOMPLETE rather than guessing a missing run. SMTP/webhook live delivery and
ambiguous remote ACK duplicate handling remain unverified. Pinned history has
storage implications; deployment DB roles/load/native installers/remote CI and
live integrations are separate gates.

Sprint 06 can use persisted authority/occurrence, failure provenance, replay range
state, notice obligations and explicit operational reassessment flags. Full incident
recovery lifecycle redesign is intentionally not implemented here. Stop after
Sprint 05; no PR, merge, deployment or real-source activation.
