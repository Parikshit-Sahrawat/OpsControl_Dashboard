# ARCH-ETL-001 V1.6-R1 reconciliation — revision 1

Status: **Sprint 01 architecture/foundation implemented; runtime work pending**.
This is a shared-architecture reconciliation, not an amendment to the approved
Pentaho specification and not formal architecture sign-off or runtime certification.
Branch: `feat/arch-etl-001-v16-r1`; eventual target: `main`.

## Immutable authority and provenance

Controlling document: [ARCH-ETL-001 V1.6](ARCH_ETL_001_V16.md), published in
`ce603a4d298f6871821818e1f0d4fa101bad46a4` with message
`docs: publish approved ARCH-ETL-001 V1.6 baseline`.
The owner supplied the specification through R1 `README.md` at
`cab0e63c8869c0c8830c4cb0e503ac45c6e38892`. The original README link pinned
`2bb41a0`, which did not contain it; the updated branch resolved that intake blocker.

The canonical document is an exact **23,653-byte** copy of that supplied source:
SHA-256 `ed8af0f9c3fce3375d0375e2431bdf43567133943551b2c0bc9f0b9882ab5446`.
Its description as an owner-approved consolidated reconstruction, rather than a
verbatim archival transcript, is preserved. No goal, decision, requirement,
acceptance criterion, formatting or line ending was changed during publication.
The originally requested approved-source filename was not present; provenance
therefore identifies the actual owner-supplied README instead of inventing a file.

Pentaho-specific behavior follows this document even where older ARCH-001 text
says all V1.5 behavior is retained. This does not authorize unrelated changes to
the eight other adapters. Shared changes require explicit compatibility tests.

Sections 14–15 approve the reconstructed RT-001–RT-020 index for R1 planning;
missing historical wording is **not** a blocker. Section 8 and REC-09 explicitly
resolve employee cardinality: exactly one department for newly created employees,
with existing legacy multi-department memberships and valid inheritance retained.
The earlier intake ambiguity is closed without changing the approved document.

## Canonical ownership and reuse

| Logical concern | Existing canonical owner | R1 reconciliation |
| --- | --- | --- |
| Customer/environment | `Organization`, `MonitoringResource`, `PipelineIntegration` | Preserve UUID ownership and VM inheritance. Departments remain internal service-provider entities. |
| Platform authority/configuration | `PipelineConnection`, `PipelineCapability`, `PipelineMethod` | Reuse versioned connections and independent methods; describe CLI, Server and Carte separately. |
| Native pipeline definition | `PipelineJob.native_id`, `PipelineAssociation`, `create_job_resource` | Confirm stable, scoped native identity before mapping to a resource; do not use display names as keys. |
| Monitored workload | `MonitoringResource` and `JobOrder` | Keep resource/JobOrder IDs and HOSTED_ON relationships. No second workload or reconstruction engine. |
| Logical execution | `JobOrderHistory` plus the existing reducer | Logical run, schedule occurrence, attempt and recovery relationship are different concepts. The current single provider-execution key needs an explicit extension design. |
| Attempts/retries | `JobStepExecution.attempt` and future job-attempt extension of existing history | Step attempts do not establish whole-job attempts. Scheduler/native identity proves retries; manual reruns remain separate logical executions. |
| Evidence and claims | `PipelineEvidence`, `NormalizedEvent`, existing quarantine and mapping issues | Preserve raw records; append evidence/state revisions and separate claim disposition from current execution outcome. |
| Collection/replay ownership | `PipelineSource`, `PipelineOperation`, fenced `accept` | Preserve atomic evidence/idempotency/projection/checkpoint acceptance, generations, lease fences, separate cursors and composed holds. |
| Incidents/recovery | `OperationalIncident`, native incident details/associations/service | Extend existing native lifecycle. Observed recovery links never authorize ETL execution or prove restoration. |
| Notifications | `AlertNotificationDelivery`, `InAppNotification`, delivery worker | Reuse the outbox/leases; add historical-failure semantic idempotency in a later tested slice. |
| Access | `User`, `DepartmentMembership`, paired role/customer grants, `resolve_access` | Preserve explicit denies and platform delegation restrictions; separate selection from authorization. |
| Retention | `PipelineHold`, source cleanup and existing telemetry retention | Extend protection across revisions, evidence, incident/notification links; do not erase held history on detach. |

## REC-01–REC-12 implementation mapping

All twelve **architecture contracts are reconciled** below. Runtime completion is
tracked independently: only REC-03's declaration foundation is implemented here.

| ID / governing clauses | Existing locations | Reconciled shared-component contract and remaining work |
| --- | --- | --- |
| REC-01 — §§2.8, 9, 13.01; C1–C3 | `frontend/src/pages/DataPipelineIntegrations.jsx`; `backend/app/data_pipelines/api.py` | Reuse exactly eight stages, drafts and explicit selection/association. Embed Pentaho surface attributes here; no competing onboarding module. Runtime forms and operator review remain later work. |
| REC-02 — §§3.1–3.3, 5; A3, B1 | `backend/app/models/entities.py`; `backend/app/unified/models.py`; `backend/app/unified/reconstruction.py`; `backend/app/data_pipelines/bridge.py` | Extend the current resource/history/reducer path. Verified scheduler identity groups job attempts; WAITING_FOR_RETRY is nonterminal, verified retry success is SUCCESS_AFTER_RETRY. Manual reruns are distinct linked logical runs; failed originals remain failed. No new canonical engine. |
| REC-03 — §§4.1–4.4, 11; A1–A2 | `backend/app/pipeline_adapters/pentaho_contracts.py`; `backend/app/pipeline_adapters/__init__.py`; `backend/app/pipeline_adapters/native.py`; `backend/app/worker/pentaho_status.py` | Implemented static version-1 surface declaration consumed by existing metadata APIs. CLI and Server are PROPOSED; legacy Carte job reads are PARTIAL; all are runtime-unverified. Transformation status/restart-epoch support remains proposed. 10.2.x/11.0.x are candidates, not installed-build proof. |
| REC-04 — §§5, 13.04; B1 | `backend/app/unified/reconstruction.py`; `backend/app/models/entities.py` | Add claim-specific reconciliation and append-only state revisions, separate CONFLICTED_EVIDENCE verdict/quarantine from outcome, retain last defensible verified projection. Current UNKNOWN/configured-source conflict handling is an implementation gap; do not alter other adapters globally or just rename the enum. |
| REC-05 — §§5, 7, 10; B2 | `backend/app/worker/notifications.py`; `backend/app/models/entities.py`; `backend/app/telemetry/models.py`; `backend/app/telemetry/inbox.py` | Reuse notification infrastructure with logical failure/revision/recipient idempotency. Occurrence and discovery times remain distinct. Historical replay must not duplicate delivery or silently reopen closed incidents. Existing delivery/user uniqueness alone is insufficient for this end-to-end rule. |
| REC-06 — §7; B2, B4 | `backend/app/native_incidents/models.py`; `backend/app/native_incidents/service.py`; `backend/app/native_incidents/api.py` | Keep one native lifecycle and distinct execution failure records. Correlate only eligible active incidents with supporting relationships; restoration needs fresh verified evidence, observable dependencies, stable window and audit. Closed history produces reassessment, not implicit reopen. |
| REC-07 — §8; D1, D3–D4 | `backend/app/security/access_control.py`; `backend/app/security/scope.py`; `backend/app/api/access.py` | Extend backend-enforced delegated IT permissions, preserving explicit denies, last-admin protection and platform-only break-glass delegation. Future identity resolution and replay approval are separately authorized/audited; no new unenforced permission labels in this sprint. |
| REC-08 — §8; D2 | `backend/app/security/scope.py`; `backend/app/security/access_control.py`; `frontend/src/pages/DataPipelineIntegrations.jsx` | One/several selections require per-customer authorization. ALL requires elevated explicit grant plus defined future-customer coverage; it is never inferred from a filter. Empty selection denies access. Persisted ALL policy/granular scope implementation remains pending. |
| REC-09 — §§8, 13.09, 14.2, 15; D3 | `backend/app/security/access_models.py`; `backend/app/security/access_control.py`; `backend/app/api/access.py`; `frontend/src/pages/AccessManagement.jsx` | New employees get exactly one department. Preserve legacy multiple memberships, their inheritance and direct roles; no normalization/backfill deletes them. Existing resolver already reads multiple memberships. Explicit transfer must remain distinguishable from automatic destructive normalization. No cardinality migration here. |
| REC-10 — §§2.7, 5–6, 10; B3 | `backend/app/data_pipelines/models.py`; `backend/app/data_pipelines/service.py`; `backend/app/services/retention.py` | Keep raw 30-day/audit-at-least-365-day defaults and approved configurability; holds protect revisions, associations and incident/notification links. Source detach may preserve protected records. Cross-path retention protection needs implementation tests before any deletion-policy changes. |
| REC-11 — §§4.4, 11, 14; A1–A2, D5 | `backend/app/data_pipelines/api.py`; `backend/app/data_pipelines/runtime.py`; `backend/app/data_pipelines/service.py` | Preserve fail-closed method eligibility and independent review. Existing installed-version/reader-hash/generation proofs are reuse points, not a finding of full R1 exact-build compliance. Do not certify a version family, connectivity, fixture, static descriptor or screenshot. |
| REC-12 — §7; B4 | `backend/app/services/correlation.py`; `backend/app/unified/engines.py`; `backend/app/native_incidents/service.py` | Retain confidence/evidence and explicit relationships; proximity alone is not causality. A recovery association alone proves neither root cause nor restored service. Extend supporting native evidence without promoting correlation labels into proven cause. |

## Sprint 01 executable foundation

`describe_pentaho_monitoring_contract` supplies fresh JSON metadata through the
existing authorized Data Pipeline catalogue and unified platform description.
It declares implemented versus proposed observations, native-identity requirements,
limitations and independent exact-build/genuine-evidence approval gates. It makes
no network requests and registers no executable adapter.

The legacy `Pentaho` adapter and its accepted configuration fields remain unchanged.
The metadata cannot select a Kitchen/Pan or Server runtime. Existing Carte job
status support does not imply transformation status or restart-epoch support.
Other eight platform descriptions are unchanged. Existing catalogue candidates
8.3/9.3/9.4 remain; 10.2.x/11.0.x are additional unverified candidate families from
§4.4. Actual reader equivalence, capability proof, activation and egress checks
are not changed. No frontend flow is implemented by returning metadata.

## Proven schema gaps and migration deferral

`JobOrderHistory` is currently a mutable projection unique by job/provider ID;
`JobStepExecution.attempt` describes a step. Neither establishes a separate
whole-job attempt, append-only state revision or last-verified projection record.
`NormalizedEvent`/`PipelineEvidence` retain evidence but do not alone encode that
revision/attempt distinction. Delivery/user inbox uniqueness does not encode a
historical verified logical-failure identity. These are concrete extension needs,
not permission to create a second canonical execution/outbox engine.

Sprint 02 should first map those gaps to the existing owners, prove concurrency,
retention and historical-backfill semantics, then justify additive schema changes.
No speculative table, enum or migration is created in Sprint 01. Alembic remains
`0032_pipeline_ownership`; no historical migration is edited. Existing customer
UUIDs, execution evidence, checkpoints, memberships and legal holds are untouched.

## Acceptance and next sprint

The baseline's RT-001–RT-020 working index is accepted for planning (§§14–15), not
claimed as verbatim historical wording. All twenty **genuine native runtime cases
remain NOT RUN**. Static contract tests support foundation design only; they do
not count as executed Pentaho P0 runtime acceptance.

Next sprint: implement identity/attempt/revision contracts in the existing engine,
including conflicted-evidence preservation and historical-failure idempotency,
with customer/fencing/hold regression coverage. Then implement read-only surfaces
and operational review UI in small vertical slices, preserving independent method
eligibility and the eight other platforms. Obtain installed builds, native sources
and authorized read-only credentials for actual certification; unsupported
endpoints and build-specific claims remain unverified until observed.

Sprint 01 verification evidence: [verification report](../verification/arch-etl-001-v16-r1/sprint01/REPORT.md).
No PR, merge, deployment, ETL execution/control or production-data change is part
of this sprint. Stop after the focused foundation commit.
