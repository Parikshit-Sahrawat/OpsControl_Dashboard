# ARCH-ETL-001 V1.6-R1 — Sprint 04

Scope: evidence reconciliation, conflict adjudication and identity review.
Branch: `feat/arch-etl-001-v16-r1`.
Baseline: `0c20d00d7281b31ccacb6e9c7a0dff2b7efc9cbb`.
Delivery commit: the commit containing this report (`git log -1 --format=%H -- <this file>`).
No PR, merge, deployment, real-source activation or production operation performed.

The approved controlling document is unchanged. SHA-256:
`ed8af0f9c3fce3375d0375e2431bdf43567133943551b2c0bc9f0b9882ab5446`.

## Delivered behavior

The existing canonical JobOrderHistory reducer, Pentaho attempt/alias/revision
extensions and source acceptance transaction are reused. No parallel execution
engine, resource identity, incident engine or ETL workload controller was added.

| Claim | Authority / applicability | Conflict / weak evidence behavior |
| --- | --- | --- |
| Invocation identity | Independently verified native invocation, scoped customer/resource/environment/job, host/start epoch or server/restart identity | Missing/ambiguous identity quarantined; immutable aliases and selected registrations cannot be reassigned |
| Execution outcome | Explicit execution-outcome capability and native completion; scheduler status or process exit is insufficient | Weaker observations retained without overriding verified terminal outcome; equal contradictory native claims freeze the defensible projection and create an execution-outcome review |
| Scheduler retry | Verified scheduler authority/run/attempt/predecessor, policy revision and native evidence hash | Old revisions cannot supersede newer policy; same-revision disagreement and terminal-regressing retry changes are quarantined independently of outcome |
| Historical correction | Authorized review selecting existing verified evidence with durable integrity/build/reader/source-generation/fence snapshot | Append-only decision with before/after projection; no fabricated native authority or automatic incident reopening |

Receipt order is not a source authority ranking: it materializes the initial
verified projection before processing a conflicting claim in the same batch.
Raw acceptance time is retained independently of normalized receipt, observation
and occurrence time, including when connector inventory returns recent runs first.
A later timestamp does not win a conflict. Legacy stamps without raw acceptance
time fall back to normalized receipt time. Completeness and monitoring health are
not collapsed into execution outcome or review status.

`pentaho_review_state` independently exposes `CLEAR`, `REVIEW_REQUIRED` or
`CONFLICTED_EVIDENCE`. Outcome conflicts do not invent identity failure, success,
failure, recovery or completeness. Candidate/prior immutable revision references,
raw evidence hashes, capability/build/reader/proof/fence snapshots, occurrence,
observation and receipt times are retained. An applicable prior claim anchor is
kept even beyond the bounded recent-revision context.

## Review workflow and authorization

Six categories: AMBIGUOUS_IDENTITY, NATIVE_ALIAS_CONFLICT, RETRY_RELATIONSHIP,
EXECUTION_OUTCOME, LEGACY_ADOPTION, RECOVERY_IDENTITY.

- `GET /api/v1/unified/resources/{id}/evidence-reviews`: filtered/paged queue,
  category/status filters and total; requires customer-scoped `etl.view`.
- `GET .../evidence-reviews/{review_id}`: immutable context and paged decisions.
- `POST .../evidence-reviews/{review_id}/decision`: customer-scoped
  `etl.resolve_identity`; strict expected_revision, idempotency_key, action, reason.
- `POST .../evidence-reviews`: explicitly report an observed recovery identity
  issue; category RECOVERY_IDENTITY, event_id, expected_revision=0, key/reason.
  Opening records an audited deferred case, not a recovery execution or link.

Actions:

- DEFER: append reason/evidence/actor and retain quarantine.
- REJECT_CLAIM: reject only disputed evidence/association; retain immutable raw
  evidence, decisions, aliases and previous defensible projection.
- ACCEPT_VERIFIED_CLAIM: explicitly correct an outcome using scoped native
  completion evidence and verified durable authority/integrity snapshot. Unresolved
  invocation/retry identity blocks correction. No arbitrary outcome field is accepted.
- ADOPT_LEGACY: a unique exact matching native alias, agreeing terminal evidence
  and verified finality are required; existing history UUID is preserved. Ambiguous
  or contradictory adoption is refused, not guessed.

`etl.resolve_identity` is catalogued/migrated without automatic employee, legacy
investigator, department or role grants. Effective access reuses existing direct/
inherited role plus customer-grant evaluation. Explicit permission revocation is
honored in existing sessions. Platform break-glass remains intact.

The worker reducer and reviewers lock the same JobOrder. Stale review versions,
conflicting idempotency reuse, parallel conflicting decisions, forged actor IDs,
extra request fields and cross-customer references fail closed. Decisions and
context are append-only/protected in PostgreSQL; projection updates and audits
commit together. No alias reassignment, merge/split or missing native proof can be
approved merely by operator assertion.

The existing Pentaho connector path backfills at most 100 pre-Sprint-04 unresolved
review cases per active resource cycle, without replaying evidence. Inactive
resources are not automatically scanned. Backfill preserves existing projections.
Pending unqueued historical identity evidence also blocks adjudication and prevents
premature quarantine clearance while the bounded queue catches up.

## Database and operational safety

Additive migration: `0034_pentaho_review` after `0033_pentaho_attempts`.

- Nullable `job_order_histories.pentaho_review_state` and supporting scoped unique key.
- `pentaho_evidence_reviews`: resource/job/history/event/raw-evidence scoped FKs,
  unique queue identity, status/category constraints and queue/raw indexes.
- `pentaho_evidence_decisions`: scoped review FK, immutable actor/reason/evidence,
  before/after projection, unique review revision and customer idempotency key.
- Database guards prohibit review deletion/identity-context rewriting and decision
  update/deletion; existing immutable evidence/alias/attempt protections remain.
- One permission catalog entry; no implicit grant or existing outcome rewrite.

No existing customer, native alias, selected job or historical evidence is deleted.
Review-referenced raw evidence is excluded from normal retention alongside existing
revision references and legal holds. Storage remains conservatively pinned until
an approved archive/release policy exists.

Empty upgrade/downgrade/upgrade and schema comparison are exercised in a disposable
PostgreSQL lab. Populated 0032 legacy customer/user/history/evidence/legal hold and
0033 R1 resource/history/attempt/alias/event/revision snapshots survive upgrade.
Downgrade refuses before dropping populated reviews/decisions or assigned review
permissions. For populated rollback retain schema and roll back compatible code,
or restore a separately verified database backup; do not delete review rows to
force a downgrade. No user development or production database was migrated here.

Existing incident associations remain intact. Review does not call incident
transition APIs. Unresolved claims and adjudicated historical corrections cannot
automatically drive changed failure/recovery/SLA conditions into incident reopening;
the previous operational conditions remain. Corrections retain a separate explicit
operational-reassessment/notification eligibility gate for Sprint 05. This is not
an implementation or successful test of historical notification delivery.

## Verification

Final results are recorded in the accompanying evidence files. Native authority
and exact-build proofs in this lab are explicitly controlled fixtures, not real
Pentaho installation acceptance or certification.

| Check | Result | Evidence |
| --- | --- | --- |
| Deterministic and existing adapter/RBAC/monitoring/incident regressions | PASSED — 155 tests, 0 failed, 0 skipped | unit.txt |
| Owned PostgreSQL ownership + Sprint 03 + Sprint 04 regression | PASSED — 101 tests, 0 failed, 0 skipped | Real source ownership/fencing, transactional checkpoints, scoped execution and review behavior |
| Existing authenticated HTTP | PASSED — 9 groups | api-existing.json |
| Sprint 03 authenticated HTTP | PASSED — 4 groups | api-sprint03.json |
| Sprint 04 authenticated HTTP | PASSED — 5 groups | api-sprint04.json; ordinary investigator denied, explicit customer-granted reviewer, stale/idempotency/IDOR/mass assignment, recovery identity reporting, session revocation |
| Alembic/schema/preservation | PASSED | migration.json, preservation.json, review-preservation.json; single head 0034_pentaho_review |
| Python application/worker imports, ORM mappers, OpenAPI routes | PASSED | static.txt |
| Black, scoped Ruff correctness, compile and whitespace | PASSED | static.txt; no claim of whole-repository strict lint compliance |
| Frontend/browser/full image build/load/live providers/production | NOT RUN | No frontend or deployment source changed; UI is Sprint 07; no live provider access authorized |
| Genuine Pentaho RT-001–RT-020 | NOT RUN — all 20 | No installation, genuine evidence or independent runtime acceptance |

Exact unit command (from backend, existing .venv):

```sh
ENV=test .venv/bin/python -m unittest \
  tests.test_pentaho_review_contracts tests.test_pentaho_execution_contracts \
  tests.test_pentaho_r1 tests.test_pentaho_surface_contracts \
  tests.test_pipeline_adapters tests.test_pipeline_transport_v16 \
  tests.test_pipeline_runtime_v15 tests.test_unified_monitoring \
  tests.test_unified_v15_contracts tests.test_access_control \
  tests.test_in_app_notifications tests.test_native_incidents_v15 -v
```

Exact PostgreSQL/HTTP/migration command (repository root):

```sh
V16_PENTAHO_R1_ACCEPTANCE=1 V16_PENTAHO_REVIEW_ACCEPTANCE=1 \
V16_API_ACCEPTANCE=1 V16_EVIDENCE_DIR=/tmp/sprint04-release \
backend/.venv/bin/python scripts/v16-acceptance.py
```

The runner creates and cleans only its own isolated PostgreSQL 17 container and
local API process; existing deployments/volumes are preserved. Docker access and
async test wakeups required execution outside the restricted socket sandbox.
An interrupted sandbox unit run is not counted as a pass. No dependencies or
persistent environment settings were changed.

### Acceptance coverage

`backend/tests/test_pentaho_review_r1.py` covers stronger-vs-weaker authority,
equal terminal contradiction, frozen projection, duplicate/late observations,
same-observation conflict, alias preservation, matching/conflicting legacy adoption,
retry-policy conflict, explicit correction, stale/idempotent decisions, concurrent
reviewers, cross-customer APIs/FKs, immutable contexts/decisions, legal holds,
bounded old-quarantine backfill, recovery-identity review and no closed-incident
reopening or automatic incident-condition evaluation. It also exercises batched
conflicts and reverse connector inventory order.

Existing `test_pentaho_execution_r1.py` and `test_pipeline_ownership_v16.py` retain
source-generation, stale fence 41/42, evidence/checkpoint rollback and eight-platform
compatibility/security regressions. The five new deterministic contract tests
cover category/permission separation, input validation, projection freeze and
required source/build/fence/integrity snapshots. HTTP uses real authenticated
FastAPI requests and customer-scoped non-platform users.

Initial failures were fixed: incorrect sanitizer argument, fixture customer scope,
unflushed revision reference, detached HTTP fixture role ID and missing review-open
audit actor. A flaky batch conflict exposed UUID ordering of equal observed times;
R1 reduction now uses durable acceptance order, including reverse connector intake.
Assertions were not weakened and no failure was suppressed. Existing datetime
`utcnow()` warnings are unrelated and remain outside this slice.

## Changed files

Application/schema/security:

- backend/app/unified/pentaho_review.py
- backend/app/unified/pentaho_execution.py
- backend/app/unified/pentaho_models.py
- backend/app/unified/reconstruction.py
- backend/app/unified/engines.py
- backend/app/unified/api.py
- backend/app/models/entities.py
- backend/app/data_pipelines/service.py
- backend/app/security/permission_catalog.py
- backend/app/security/access_control.py
- backend/app/security/scope.py
- backend/migrations/versions/0034_pentaho_evidence_review.py

Tests/tooling:

- backend/tests/test_pentaho_review_contracts.py
- backend/tests/test_pentaho_review_r1.py
- backend/scripts/pentaho_review_migration_probe.py
- backend/scripts/pentaho_sprint04_http_probe.py
- scripts/v16-acceptance.py

Documentation/evidence:

- ARCH-001_IMPLEMENTATION_STATUS.md
- docs/ARCH_001_V16.md
- docs/architecture/ARCH_001.md
- docs/verification/arch-etl-001-v16-r1/sprint04/REPORT.md and companion evidence

Cleanup is limited to reusing the existing history projection in reducer/review and
centralizing review safety. No old adapter, migration, canonical model or public
consumer was removed without proof it was unused.

## Limitations and Sprint 05 readiness

Complex alias merge/split/remapping and contradictory legacy adoption remain
quarantined, requiring new defensible native evidence, not fabricated operator proof.
Pre-Sprint-04 claims without the required integrity/authority snapshot cannot be
promoted by review alone. Exact Pentaho Server endpoints, installed Pentaho version,
native Agent producers and bounded provider replay retain Sprint 02 limitations.
Other eight platform adapters and protected shared behavior are unchanged.

Review/attempt APIs are paged; embedded review context recent references are bounded,
with a separate applicable anchor and retained underlying evidence. Existing
connector intake remains bounded to 100 recent runs; this is not full backlog
replay. Pinned evidence/revisions have storage implications. Restricted deployment
DB roles, sustained load, remote CI and real nine-platform acceptance are separate
unverified gates.

Sprint 05 can build on durable conflict decisions, independent state dimensions,
raw occurrence/acceptance/receipt times, retained incident references, legal holds
and explicit historical reassessment/notification eligibility. Full schedule/replay/
historical notification, Sprint 06 incident redesign and Sprint 07 frontend were
not implemented or claimed. Stop after Sprint 04.
