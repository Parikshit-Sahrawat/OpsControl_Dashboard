# ARCH-ETL-001 V1.6-R1 — Sprint 06

Scope: incident correlation, historical reassessment and evidence-based recovery.
Branch: `feat/arch-etl-001-v16-r1`.
Baseline: `f2a9404eff2bb8f8089f2f1158c4bc920b904ca8` (clean repository on resume).
Delivery SHA: the commit containing this report (`git log -1 --format=%H -- <this file>`).
No PR, merge, deployment, production change, external notification or real-source activation.

The controlling `docs/architecture/ARCH_ETL_001_V16.md` is unchanged, SHA-256
`ed8af0f9c3fce3375d0375e2431bdf43567133943551b2c0bc9f0b9882ab5446`.
Previous implementation and verification evidence remain intact.

## Implementation and architecture compliance

The canonical `OperationalIncident` and seven-state native lifecycle are reused.
No parallel incident or execution engine was introduced. Existing assignments,
incident identities, source evidence, native aliases, recovery links and audits
remain. Two evidence extensions persist immutable failure associations and
independent recovery assessments; `IncidentActivity` and security audit remain the
audit mechanisms. The other eight platform integrations keep their existing paths.

The Sprint 05 bounded historical scan feeds incident association while retaining
its existing cursor, eligibility checks and notification outbox. Current failures
are eligible too. Failure authority requires terminal FAILED, confirmed invocation,
verified native completion/finality, durable build/source/fence/integrity provenance
and no pending identity/evidence conflict. WAITING_FOR_RETRY is nonterminal;
CONFLICTED_EVIDENCE is not authoritative failure. Distinct accepted failure evidence
is attached without replacing the original execution or evidence. Replayed event
IDs are unique and pending distinct evidence drains in bounded batches of 200.

Correlation requires exact customer/environment-scoped native cause authority,
cause occurrence identity and cause evidence hash. The strict observation parser
accepts optional `failure_cause` with `authority_id`, `occurrence_id` and
`evidence_sha256`; an independently verified `FAILURE_CAUSE` capability is required
before that reference can establish grouping. A name, host, customer, timestamp,
shared schedule or generic correlation confidence does not establish common root.
Absent verified cause proof, each failed logical execution gets its own episode.
Existing explicit history associations win. Eligible active root incidents are
preferred; a new live failure after closure gets a new episode. Historical failures
can retain a closed root association with a separate HISTORICAL_REASSESSED audit,
never a silent reopening. Occurrence and discovery timestamps remain distinct.

Resource/job locks, nonblocking transaction advisory root locks, incident row locks,
unique evidence keys and expected revisions serialize competing workers/operators.
Generic shared-job failure alerts and possible-common-cause groups cannot create
additional authoritative Pentaho failure incidents. Other generic alerts remain.
Existing incident IDs, assignments and audit history are preserved.

## Recovery decisions

Assessment result is independent of incident status:
RECOVERY_CANDIDATE, VALIDATION_PENDING, VALIDATED_RECOVERY, VALIDATION_FAILED or
INSUFFICIENT_EVIDENCE. All associated failed executions must be accounted for.

- Each original failure remains FAILED. A separate complete, unconflicted native
  SUCCESS/SUCCESS_AFTER_RETRY needs an existing CONFIRMED recovery relationship.
  Scheduler retry success remains a logical-attempt outcome, not a manual recovery.
- The successful native outcome must be within the observation duration plus 120
  seconds. Current monitoring additionally requires eligible readers, correct
  generation, fresh complete acceptance receipts, healthy source state, continuity
  and no effective suspension/hold. A successful execution alone does not restore service.
- Existing direct dependency edges are checked in both directions, including
  downstream dependents. An available telemetry path alone is insufficient:
  dependency condition evidence must be fresh/resolved, or a Pentaho dependency
  must have complete native success. Active conditions and a known dependency
  recovery after MONITORING began block validation until monitoring is restarted.
- Configured schedules need an OBSERVED occurrence with authority, the active
  parameter version and a fresh evaluation. Missing, delayed, unknown or stale
  compliance blocks recovery; native outcome and schedule compliance stay separate.
- Observation duration is configurable from 60 to 86400 seconds. Authorized
  persisted assessments no more than 120 seconds apart preserve a healthy window.
  A gap, failed/missing evidence or changed recovery/policy/generation signature
  resets progress. Preview is read-only and cannot create observation history.
- Existing authorized resolution/closure re-evaluate current proof and expected
  revision. Neither automatic alert resets nor a recovery-link confirmation close
  an incident. Authenticated actor, evidence pointers, dimensions and results are
  retained for review.

## APIs and authorization

Existing `/api/v1/native-incidents/{id}` exposes failure evidence, historical
reassessment metadata, recovery assessments and the existing audit timeline.
Existing recovery-preview/validation/transitions apply the recovery gate.
Environment-filtered inventory includes the new execution associations.

`GET .../execution-failures` and `GET .../recovery-assessments` provide paged evidence
(limit 1–200 and offset). They enforce `incidents.view` and effective customer scope.
`POST .../recovery-assessments` requires `incidents.manage`, `revision`,
`idempotency_key`, and optional `observation_seconds`. Health and evidence decisions
are server-derived; extra/mass-assigned fields are rejected. Identical replay returns
the original assessment, conflicting keys/stale revisions fail, and the mutation is
audited. New models are included in existing ORM customer-scope enforcement.
No implicit permission grants, additional workload controls or external delivery
endpoints were introduced.

## Database and preservation

Single head: `0036_native_recovery`, parent `0035_pentaho_history`. Migration 0036
adds `native_incident_failures` and `native_recovery_assessments`, scoped incident,
execution and event foreign keys, unique event/request keys, result constraints and
append-only database guards. Historical migrations are unchanged.

Both tables reject update/delete, conservatively retaining evidence even beyond a
legal hold. Existing source/legal-hold protection remains. Populated downgrade
fails before any table is removed. Empty downgrade/upgrade and Alembic schema
comparison pass. The dedicated 0035→0036 probe verifies unchanged native incidents,
assignment/revision/escalation, incident activity, alert associations, execution
history, aliases/revisions, legal holds, raw evidence, notice outbox, permissions and
user rows. Previous migration-preservation probes also pass. Only disposable owned
PostgreSQL was migrated. Rollback requires compatible retained schema/code or a
separately verified backup; do not disable guards to force evidence deletion.

## Verification

Controlled fixtures model native authority; none certify installed Pentaho builds.

| Check | Actual final result | Evidence |
| --- | --- | --- |
| Unit/adapter/RBAC/native monitoring regressions | 165 passed, 0 failed, 0 skipped | unit.txt and unit-remaining.txt |
| Combined PostgreSQL regression | 147 passed, 0 failed, 0 skipped (127 previous + 20 Sprint 06) | postgresql.txt |
| Authenticated HTTP | 27 groups passed: existing 9, Sprint 03 4, Sprint 04 5, Sprint 05 4, Sprint 06 5 | api-existing.json; api-sprint03/04/05/06.json |
| Migration/head/schema/preservation | Passed; no schema drift, empty round trip, populated refusal | migration.json; preservation.json; review-/history-/incident-preservation.json |
| Imports/mappers/OpenAPI, Black, scoped Ruff, compilation, whitespace | Passed | static.txt |
| Real Pentaho RT-001–RT-020 | NOT RUN — all 20 | Independently authorized native acceptance unavailable |
| Live platform acceptance, production, external mail/webhook, load/failover | NOT RUN | Controlled local lab only |
| Frontend/browser/full image build | NOT RUN | No frontend or deployment change in this sprint |

The unit gate completed 91 tests before the socket sandbox stalled the existing
asyncio runtime test's shutdown. That process was interrupted and only the six
unfinished modules were resumed with authorized local socket access: 74 passed.
The interrupted attempt is retained in unit.txt; no failed test was suppressed or
counted as passing. This is 165 distinct completed tests, not 165 plus the retry.

The final broader PostgreSQL gate ran once. A focused follow-up checks the final
environment-filter correction and dependency evidence pointers; its exact results
are recorded in `followup.json` and `postgresql-followup.txt`. It does not claim to
repeat the earlier fencing race. Initial development failures involved explicit
fixture permission, resource binding, unittest helper naming, scanner wraparound,
thread-local sessions, the new downgrade message and HTTP OpenAPI path. These were
corrected without weakening assertions; final results above retain all checks.

Commands (existing environment; no dependency or runtime configuration changes):

```sh
# backend/ — the eight initial modules are listed in unit.txt; six resumed below:
ENV=test .venv/bin/python -m unittest \
  tests.test_pipeline_runtime_v15 tests.test_unified_monitoring \
  tests.test_unified_v15_contracts tests.test_access_control \
  tests.test_in_app_notifications tests.test_native_incidents_v15 -v

# Repository root — one final combined gate:
V16_PENTAHO_R1_ACCEPTANCE=1 V16_PENTAHO_REVIEW_ACCEPTANCE=1 \
V16_PENTAHO_HISTORY_ACCEPTANCE=1 V16_PENTAHO_INCIDENT_ACCEPTANCE=1 \
V16_API_ACCEPTANCE=1 V16_EVIDENCE_DIR=/tmp/sprint06-final \
backend/.venv/bin/python scripts/v16-acceptance.py

# Focused final follow-up (only Sprint 06 database module; existing HTTP baseline):
V16_TEST_TARGETS=tests.test_pentaho_incident_r1 \
V16_PENTAHO_INCIDENT_ACCEPTANCE=1 V16_API_ACCEPTANCE=1 \
V16_EVIDENCE_DIR=/tmp/sprint06-followup \
backend/.venv/bin/python scripts/v16-acceptance.py
```

## Required acceptance mapping

New database tests are in `backend/tests/test_pentaho_incident_r1.py` (20 tests).
Five deterministic contracts are in `test_pentaho_incident_contracts.py`.

| Required behavior | Executed coverage |
| --- | --- |
| 1 verified failure | verified_failure_creates_native_incident_and_replay_is_idempotent |
| 2 common root | common_root_groups_distinct_failures_and_preserves_evidence; strict native authority contracts |
| 3 unrelated failures | unrelated_same_job_and_time_stay_separate |
| 4 distinct evidence | distinct_failure_observations_are_all_preserved |
| 5 waiting retry | waiting_for_retry_creates_no_terminal_incident; prior execution regressions |
| 6 retry success/manual distinction | prior test_pentaho_execution_r1 scheduler retry/recovery suite |
| 7 original FAILED retained | manual_recovery_preserves_failed_original_and_requires_observation |
| 8 incomplete recovery | incomplete_recovery_is_not_restoration |
| 9 downstream dependency | unhealthy_downstream_dependency_blocks_recovery |
| 10 observation period | manual_recovery...; gap_in_observation_restarts_period; bounded input contract |
| 11 unhealthy monitoring | unhealthy_monitoring_blocks_and_resets_window; current_source_requires_complete_receipt |
| 12 conflict | conflicted_failure_cannot_create_authoritative_association; conflicting_recovery_evidence_blocks_validation |
| 13 authorized validation/closure | manual_recovery... executes real healthy receipt, assessment, RESOLVED and CLOSED |
| 14 stale/unauthorized closure | native lifecycle unit suite; stale_idempotent_and_unauthorized_assessments; authenticated transition denials |
| 15 late history | historical_root_never_reopens_resolved_incident; live_failure_after_closed_root_creates_new_episode; prior historical outbox suite |
| 16 replay/idempotency | verified_failure...; stale_idempotent...; authenticated repeated assessment |
| 17 concurrency | concurrent_correlation_preserves_single_incident; concurrent_assessments_serialize_revision; prior fence-41/42 regression |
| 18 isolation/RBAC | authenticated foreign-customer denial, viewer denial, scoped evidence/inventory; prior customer/FK regressions |
| 19 legal holds/migration | failure_and_assessment_evidence_is_immutable; unchanged hold/retention regressions; four preservation probes |
| 20 eight-platform compatibility | existing adapter/runtime, unified monitoring and ownership regressions |
| 21 no workload controls | Sprint 06 HTTP OpenAPI check; unchanged read-only adapters; no control routes or execution code added |

## Changed files, limitations and Sprint 07 readiness

`changed-files.txt` records the complete delivery inventory; `source-sha256.json`
records changed implementation/test/status-document hashes. Source changes are
limited to native incident models/service/API and its Pentaho evidence extension,
existing Pentaho observation/capability/historical hooks, ORM scope, migration 0036,
focused tests/probes and the existing acceptance runner. The three implementation
status documents and this verification directory are updated; the approved Pentaho
architecture is unchanged.

Native failure-cause producers, exact-build capability acceptance, actual dependency
health and actual recovery observations still need separately authorized runtime
acceptance. No universal Server endpoint or provider support is invented. Observation
is a bounded sequence of explicit assessments, not an autonomous continuous
validation worker; long periods need repeated fresh execution/monitoring evidence.
Direct configured dependencies are checked; transitive topology and unavailable
non-Pentaho execution proof remain conservative limitations. Evidence/history scans
are bounded, so association may wait for the next fair cursor pass. Immutable pinned
evidence has storage costs. Load/failover, live notification delivery, native
installers and UI consumption remain unverified.

Sprint 07 may build on the scoped failure/assessment APIs and existing lifecycle,
subject to its own acceptance. Sprint 06 does not certify production readiness or
real Pentaho runtime behavior. Stop after this sprint; no PR, merge, deployment or
real-source activation was performed.
