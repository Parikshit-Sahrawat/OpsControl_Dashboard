# ARCH-ETL-001 V1.6-R1 — Sprint 03

Branch: `feat/arch-etl-001-v16-r1`. Starting commit:
`7cd81efc65aba53a768b23ab1c0037f34a2a4559`.
Authority: [unchanged approved architecture](../../../architecture/ARCH_ETL_001_V16.md).
Prior milestone: [Sprint 02](../sprint02/REPORT.md).
No PR, merge, deployment, production operation, live provider access or real
monitoring-source activation was performed.

## Implementation

`JobOrderHistory` remains the canonical logical execution. `MonitoringResource`,
`JobOrder`, source ownership, accepted raw evidence, durable `CollectorRun`
compatibility queue, `NormalizedEvent`, existing `reduce_execution()` entry point,
alerting and native incidents are reused. There is no second resource identity,
execution worker, scheduler or workload-control endpoint.

Five justified persistence extensions represent distinct missing concepts:

| Extension | Purpose |
| --- | --- |
| `pentaho_execution_attempts` | Immutable attempt UUID/key/order/native identity, independent current outcome, completeness, native times and retry-authority projection |
| `pentaho_native_aliases` | Append-only invocation/logical/scheduler-attempt aliases to existing histories and attempts; unique within customer/resource |
| `pentaho_attempt_revisions` | Immutable observations, disposition, occurrence/observation/reception times, authority/generation and native evidence references; duplicate-observation idempotency |
| `pentaho_recovery_links` | Many-to-many current relationship projection between distinct existing logical histories |
| `pentaho_recovery_decisions` | Append-only proposal/confirmation/reversal reasons, supporting evidence hashes, actors, revisions and request idempotency; existing security audit also records each transition |

### Identity and authority

The Sprint 02 resource/customer/environment/authority/invocation/epoch identity is
preserved. Native aliases cannot be updated or deleted. Configurable name/time
matching cannot rewrite an R1 invocation key. One logical retry group requires
verified scheduler authority, run ID, attempt ID, native order, policy revision,
evidence hash and an explicit predecessor for later attempts. PID, job name,
nearby timestamps, identical messages or exit code never group runs or prove
completion. A scheduler occurrence is retained as a separately scoped native
reference; no schedule window is invented here.

The fenced source-acceptance transaction stamps `pentaho_verification` using the
current approved profile's explicit `verified_pentaho_claims`:
`INVOCATION`, `EXECUTION_OUTCOME`, `SCHEDULER_RETRY`. Producer-supplied verification
claims are discarded. VERIFY leases grant none of these authorities. Profile
verification requires native proof shaped for the claimed authority as well as
all existing independent exact-build/reader/generation/native acceptance gates.
Those shape checks alone never certify a runtime.

Profiles without these explicit claims gain no new reconstruction authority.
Native methods must be independently reviewed for the specific facts they assert;
source authentication, static declarations or connectivity are insufficient.
Scheduler IDs must be proven stable/non-recycled within the attested authority.
Unknown native identity schemes remain unverified.

Confirmed aliases, pipeline registrations and operator selections are not
retargeted on ambiguity. The new observation stays UNRESOLVED; related known
histories are marked REVIEW_REQUIRED without overwriting their outcomes.
Unverified retry proposals keep separate invocation histories and are quarantined.
Existing terminal histories are not silently adopted or recertified; ambiguous
legacy adoption is explicitly blocked for later authorized identity review.

### Attempts and lifecycle

| Evidence | Logical state |
| --- | --- |
| Verified first native success | TERMINAL / SUCCESS |
| Failed attempt plus verified pending retry | WAITING_FOR_RETRY; no terminal failure |
| Verified later successful scheduler attempt | TERMINAL / SUCCESS_AFTER_RETRY |
| Verified final failure and exhausted retry authority | TERMINAL / FAILED |
| Failed attempt without retry authority/exhaustion proof | IDENTIFIED / no terminal outcome; native attempt remains FAILED |
| Start observation | RUNNING |
| Process exit without native result | UNKNOWN attempt; no invented terminal success/failure |
| Verified cancellation | TERMINAL / CANCELLED; no cancellation action exists |

Lifecycle, terminal outcome, completeness, schedule references and monitoring
health remain distinct. `UNKNOWN` is supported as a terminal outcome in storage;
unknown/incomplete observations do not themselves prove terminal completion.
Retries with missing earlier attempts retain partial completeness rather than
fabricating history. Revisions append when later evidence arrives. Native retry
policy revisions determine policy freshness, rather than timestamp proximity.
Duplicate observations do not duplicate attempts/revisions; distinct transport
records remain raw evidence. Late starts do not regress terminal outcomes.
Contradictory terminal claims retain the last defensible projection and a review
marker; full precedence/conflict adjudication belongs to Sprint 04.

Legacy `status` remains compatible: SUCCESS_AFTER_RETRY maps to SUCCESS,
WAITING_FOR_RETRY maps to RUNNING, and CANCELLED maps to UNKNOWN. New explicit
`pentaho_*` history fields expose the precise meaning. Existing evaluation respects
R1 terminality and does not infer SLA success or missing-response alarms from a
cancelled run. No schedule/SLA/replay redesign was introduced.

### Observed manual recovery

A manual run has a distinct logical/attempt identity and MANUAL execution type.
A recovery link never changes the failed original, marks restoration, transitions
an incident or invokes Pentaho. Many failed runs may reference one recovery run,
and one failed run may reference several recovery runs.

An authorized investigator proposes a link with verified identity evidence for
both runs and a defensible association reason. A different authorized investigator
must confirm it. A confirmed link can be reversed with a reason and expected
revision; original evidence and all decisions remain immutable. Reversal remains
possible after a later identity-review issue. Identity quarantine cannot be
bypassed by confirming a link. Self-links, cycles, self-confirmation, foreign
customer targets, invalid evidence, stale revisions and conflicting request keys
are denied. A reversed link is retained; no silent reactivation is implemented.

The permission is existing customer-scoped `etl.investigate`; reading uses
`etl.view`. Actual HTTP tests use non-platform-admin investigators. No new role,
implicit grant, employee/department change or provider-wide permission is added.

## APIs

Existing execution inventory is unchanged except additive nullable history fields.
New routes under `/api/v1/unified`:

- `GET /resources/{id}/executions/{history_id}/attempts` — scoped current attempts,
  aliases and recent immutable revisions; attempt pagination.
- `GET /resources/{id}/executions/{history_id}/recovery-links` — paginated related
  links and decision timeline.
- `POST /resources/{id}/executions/{history_id}/recovery-links` — propose with
  `recovery_history_id`, `evidence_ids`, `reason`, `idempotency_key`.
- `POST /resources/{id}/executions/{history_id}/recovery-links/{link_id}/decision` —
  `action` CONFIRM/REVERSE, `expected_revision`, `reason`, `idempotency_key`.

Requests forbid extra fields. These routes accept no command, process action,
start/restart/rerun/cancel/repair API or execution credential.

## Migration and integrity

Revision `0033_pentaho_attempts`, parent `0032_pipeline_ownership`:

- Adds nullable Pentaho extension fields to existing `job_order_histories`.
- Adds the five extensions with tenant/resource/history composite foreign keys,
  uniqueness, state/order constraints and lookup/retention indexes.
- Does not modify customer UUIDs, users/password hashes, sessions, historical
  outcomes, existing aliases or source checkpoints. No identity backfill is guessed.
- Database triggers protect aliases, revision/decision journals, R1 history
  identity/deletion, attempt identity/deletion and normalized source payloads.
- Existing legal holds remain in force. Referenced R1 raw evidence is pinned via
  foreign keys and excluded from cleanup; history/revision deletion is not enabled.
- Empty downgrade is tested. Populated downgrade refuses before dropping anything.
  Rollback after accepting R1 records means retain additive schema or restore a
  verified pre-migration backup; never delete protected rows to force downgrade.

The migration ran only in newly owned disposable PostgreSQL containers. The
populated 0032 fixture included a customer, employee hash, failed history, source,
raw evidence and legal hold; all survived unchanged. Shared local Docker volumes
and production databases were not modified.

## Changed files

- `backend/app/models/entities.py`: nullable canonical-history extension.
- `backend/app/unified/{models,pentaho_models}.py`: scoped constraints/extensions.
- `backend/migrations/{env.py,versions/0033_pentaho_attempts.py}`: metadata and safe additive migration.
- `backend/app/unified/{reconstruction,pentaho_execution}.py`: existing reducer hook,
  verified identity/attempt reduction and monotonic projection.
- `backend/app/pipeline_adapters/pentaho_observations.py`: native/scheduler provenance,
  manual-origin/cancellation observations; no workload controls.
- `backend/app/data_pipelines/{api,service}.py`: claim proof gate, trusted projection
  stamp inside acceptance, no synthetic R1 start duplicates and retention protection.
- `backend/app/unified/{api,pentaho_recovery,engines}.py`: scoped recovery/read APIs,
  append-only review and compatible terminal handling.
- `backend/app/security/{scope,access_control}.py`: new scoped models and route permission mapping.
- `backend/app/main.py`: model registration and adjacent import formatting.
- `backend/tests/{test_pentaho_execution_contracts,test_pentaho_execution_r1}.py`:
  deterministic contracts and PostgreSQL acceptance.
- `backend/scripts/{pentaho_migration_probe,pentaho_sprint03_http_probe}.py` and
  `scripts/v16-acceptance.py`: reproducible owned migration/HTTP checks and focused targets.
- `docs/{ARCH_001_V16.md,architecture/ARCH_001.md}`, `ARCH-001_IMPLEMENTATION_STATUS.md`
  and this evidence directory: implemented contracts and limitations.

## Verification

```sh
cd backend
ENV=test .venv/bin/python -m unittest \
  tests.test_pentaho_execution_contracts tests.test_pentaho_r1 \
  tests.test_pentaho_surface_contracts tests.test_pipeline_adapters \
  tests.test_pipeline_transport_v16 tests.test_pipeline_runtime_v15 \
  tests.test_unified_monitoring tests.test_unified_v15_contracts \
  tests.test_access_control tests.test_in_app_notifications \
  tests.test_native_incidents_v15 -v
cd ..
V16_PENTAHO_R1_ACCEPTANCE=1 V16_API_ACCEPTANCE=1 \
  V16_EVIDENCE_DIR=/tmp/sprint03-delivery \
  backend/.venv/bin/python scripts/v16-acceptance.py
# A focused rerun can select a dotted test with V16_TEST_TARGETS=tests.test_...
backend/.venv/bin/black --check backend/app/models/entities.py \
  backend/app/unified/{api,models,reconstruction,engines,pentaho_execution,pentaho_recovery,pentaho_models}.py \
  backend/app/data_pipelines/{api,service}.py backend/app/pipeline_adapters/pentaho_observations.py \
  backend/app/security/{access_control,scope}.py backend/app/main.py backend/migrations/env.py \
  backend/migrations/versions/0033_pentaho_attempts.py \
  backend/scripts/{pentaho_migration_probe,pentaho_sprint03_http_probe}.py \
  backend/tests/{test_pentaho_execution_contracts,test_pentaho_execution_r1}.py scripts/v16-acceptance.py
backend/.venv/bin/ruff check --select E9,F63,F7,F82 backend/app/unified \
  backend/app/data_pipelines backend/app/pipeline_adapters/pentaho_observations.py \
  backend/app/models/entities.py backend/app/security/{scope,access_control}.py \
  backend/tests/test_pentaho_execution* backend/scripts/pentaho*probe.py \
  backend/migrations/versions/0033_pentaho_attempts.py scripts/v16-acceptance.py
backend/.venv/bin/python -m compileall -q backend/app/unified backend/app/data_pipelines \
  backend/app/pipeline_adapters backend/migrations/versions/0033_pentaho_attempts.py \
  backend/scripts/pentaho_migration_probe.py backend/scripts/pentaho_sprint03_http_probe.py
# In backend: ENV=test .venv/bin/python -m alembic heads
git diff --check
```

| Check | Status | Actual result |
| --- | --- | --- |
| Focused deterministic/regression unit tests | PASSED | 150 passed, 0 failed, 0 skipped; seven new contract cases plus existing adapters/RBAC/monitoring/incident tests |
| Actual PostgreSQL tests | PASSED | 76 passed, 0 failed, 0 skipped; 20 new Sprint 03 cases plus 56 source ownership/compatibility regressions |
| Existing authenticated HTTP | PASSED | Nine groups |
| New authenticated Sprint 03 HTTP | PASSED | Four groups; scoped non-admin investigators and viewers, IDOR, idempotency, independent review, reversal and original-failure preservation |
| Migration/schema | PASSED | Populated 0032→0033 preservation, empty roundtrip, populated downgrade refusal, zero drift; head `0033_pentaho_attempts` |
| Imports/mappers/routes | PASSED | Actual application import, ORM configuration and new FastAPI paths |
| Black/Ruff correctness/compile/whitespace | PASSED | Scoped touched code; no claim of whole-repository strict lint compliance |
| Genuine Pentaho RT-001–RT-020 | NOT RUN | All 20; requires separately authorized installations/native evidence and independent acceptance |
| Frontend/browser/full image build | NOT RUN | No frontend or container-image configuration changed; no new UI was in scope |
| Live adapters, production, load/failover, restricted deployed DB-role acceptance | NOT RUN | No live credentials/infrastructure accessed; test DB used its disposable migration owner |

Initial alias-safety failure was fixed by rejecting scheduler-run reassignment of
a confirmed invocation. Duplicate fixture discovery and an invalid HTTP fixture
field were corrected. No assertion was weakened or failing test suppressed.
An inherited `datetime.utcnow()` deprecation warning remains outside this slice.

### Required acceptance mapping

| Requirement | Executed coverage |
| --- | --- |
| 1 Single success | `test_single_success_has_canonical_history_attempt_and_aliases` |
| 2 Verified retry success | `test_verified_failed_attempt_pending_then_success_after_retry` |
| 3 Pending retry nonterminal | Same test checks WAITING_FOR_RETRY before retry |
| 4 Final exhaustion | `test_verified_final_failure_exhausted_is_terminal` |
| 5 Manual recovery | `test_manual_recovery_keeps_failed_original_and_distinct_identity` |
| 6 Many-to-many | `test_many_to_many_recovery_links_and_reversal_are_append_only` |
| 7 Ambiguity/quarantine | `test_unverified_retry_proposal_remains_separate_and_quarantined`, `test_conflicting_native_alias_does_not_retarget_confirmed_run`, `test_known_retry_predecessor_cannot_point_back_from_an_earlier_attempt` |
| 8 Duplicate idempotency | `test_duplicate_observations_keep_raw_records_but_not_duplicate_attempts_revisions` |
| 9 Out-of-order | `test_out_of_order_start_and_earlier_retry_do_not_regress_success` |
| 10 Customer isolation | `test_cross_customer_history_and_relation_are_rejected`, actual HTTP nested/resource IDOR checks and existing composite-FK/RBAC tests |
| 11 Eight-platform compatibility | Existing `test_pipeline_adapters`, runtime and unified V1.5 regressions |
| 12 Atomicity/fencing | `test_stale_source_generation_does_not_accept_attempt_or_advance_checkpoint`; existing actual PostgreSQL rollback/fence-41/42 tests |
| 13 Missing authority | `test_missing_retry_authority_never_implies_exhaustion` |
| 14 Exit alone unknown | `test_process_exit_alone_unknown_and_scheduler_alone_not_success` and existing Server scheduler contract tests |
| 15 Reversal/audit | Many-to-many test plus real HTTP reversal/idempotency/decision-timeline checks |
| 16 Migration/holds | `test_legal_hold_and_referenced_raw_history_survive_cleanup`, immutable-trigger tests and populated migration probe |

Evidence: [unit](unit.txt), [PostgreSQL](postgresql.txt), [existing HTTP](api-existing.json),
[Sprint 03 HTTP](api-r1.json), [migration](migration.json),
[preservation](preservation.json), [runner](runner.txt), [static](static.txt).
No private credentials, access tokens or service failure logs are included.

## Cleanup, limitations and Sprint 04 readiness

Only changed execution paths were cleaned up: the existing event query is reused
and refreshed after the canonical JobOrder lock, and R1 observations avoid a
synthetic start duplicate. No legacy adapter/model was removed: active consumers
and history still rely on them. Adjacent touched imports were formatted.

Provider-specific scheduler/native proof producers remain subject to Sprint 02
limitations. Declaring a claim or constructing these fixtures is not certification.
Legacy ambiguous terminal-history adoption, full contradictory-claim precedence,
identity-resolution workflows and authorized corrections belong to Sprint 04.
Replay/schedule monitoring and incident redesign remain later milestones.

Existing connector intake scans its bounded recent-run window (100 runs); larger
backlog/restart replay is not newly guaranteed here. Read APIs page attempts/links
and bound embedded revisions/decisions to 100. No sustained-load claim is made.
Referenced R1 evidence/history remains conservatively pinned until an approved
archive/release policy exists, with corresponding storage-capacity implications.
Deployment-role privileges, native integrations and remote CI remain separate gates.

Sprint 04 has stable scoped aliases, immutable attempt/relationship revisions,
quarantine markers and evidence references to build on. Do not bypass quarantine
or immutable triggers to resolve conflicts. Stop after Sprint 03; no PR/merge/deploy.
