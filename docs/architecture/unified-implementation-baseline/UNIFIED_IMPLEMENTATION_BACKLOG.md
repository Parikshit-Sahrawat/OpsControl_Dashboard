# Unified Implementation Backlog

Baseline: PR #80 source `e69528ad2b826398474382f34126feeca740f6a6`; main/merge-base `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`. Working branch `dev/post-pr78-architecture-closure-20261105`. Assessment date: 2026-11-05. Source presence, controlled verification, genuine-provider certification and owner acceptance are separate dimensions. No product code or migration is changed by OC-ARCH-001.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.** Journey 20 Service Catalog excluded; Journey 32 Kubernetes/container observability skipped. No provider execution, scheduler writes, job retry/termination controls, merge or deployment.

## Dependency-ordered work

Backlog IDs below are execution task identifiers, not new product requirements. Preserve PR80 completed milestones; begin by repairing their request-path integration, not by recreating migration 0039 or the models. B00 blocks missing decisions only; it does not stop approved ETL scope/security/data-preservation work.

| Task | Priority | Prerequisites | Bounded work | Accountable role (not signoff) | Required tests / exit |
|---|---|---|---|---|---|
| B00 | P0 authority | None | Recover 30 exact numbered journey definitions and detailed LIC/event/channel decisions; versioned many-to-many crosswalk, no fabricated mapping. | Owner/architect | Evidence artifact and explicit authority per row; exclusions immutable. Missing source remains BLOCKED. |
| B01 | P0 security/functionality | Existing PR80 foundation | Fix CF-01 scope paths, audited request persistence, parent immutability and resource/env boundaries. Address CF-03 with deterministic transaction proof. | Backend + security | Real HTTP authorized create/edit/list/job/dependency; A/B/none/ALL grants, deny overrides, role revoke; audit commit/rollback; parallel cycle attempts. No global bypass. |
| B02 | P0 data safety | B01 | Preserve optional legacy JobOrder linkage; guard populated rollback/recovery; define explicit non-destructive workflow assignment and timing compatibility. | DB + backend | Fresh upgrade, historical populated upgrade, old/new consumers, hashes, dump/restore, populated downgrade refusal before drops. No automatic grouping, no live DB. |
| B03 | P1 native observation | B01/B02; sanitized provider schema | Implement source-specific read-only mutable-row observation contract for Oracle/MSSQL/logs; retain independent methods and canonical IDs. | Provider + runtime | Same-row RUNNING→SUCCESS/FAILED, late terminal updates, overlap, pagination, timestamp units, duplicates, retention, schema drift, permission denial; no scheduler DML/control. |
| B04 | P1 UI | B01/B02 | Add workflow/job editor in existing configuration owner; reuse read-only operational projection; expose blocked/readiness state and credential refs. | Frontend + backend | Browser create/edit/reload/source/customer switching, DAG validation, stale fetch protection, failed save, role negatives; only job duration, workflow timing; no Run/Retry buttons. |
| B05 | P1 lifecycle | B02/B03 | Connect workflow occurrences and child native attempts to existing reducer; derive outcomes/completeness/health separately. | Monitoring engineer | Timezone/DST, no-run vs no-telemetry, missing child, attempt retry grouping, late evidence, conflict quarantine, no duplicate canonical execution; persisted receipt reconciliation. |
| B06 | P1 policy/events | B05; specific catalog/override decisions from B00 | Implement versioned template→workflow→job event policy, event/alert separation, four-state conditions and evidence-backed recovery. | Monitoring + product | Policy snapshot reproducibility, explicit override/clear, actual elapsed threshold, debounce/recovery, stale orthogonal, restart/replay dedup, no inferred success from stale source. |
| B07 | P1 notification/UI | B06; channel disposition CF-04 | Wire approved existing channels/outbox and incident projections; preserve immutable distinct failures, historical notification and review. | Integrations + operations | Delivery retries/dedup, recipient scope, historical occurrence/discovery, no closed-incident silent reopen, restoration evidence window, tenant-negative browser/API. |
| B08 | P0 release evidence / parallel | B01–B07 where relevant; separate runtime approvals | Certify genuine provider capabilities, bounded source continuity, security and rollback; retain independent CHK gates. | Independent verification/security/provider owners | RT-001–020 native exact-build evidence and owner approval; source inventory/receipts, known loss FAIL, unsupported NOT TESTED; no synthetic-to-genuine promotion. |
| B09 | P1 licensing | B00 exact licensing contract; B01 security primitives | Design/implement LIC-001–008 incrementally after missing cryptographic/grace/deployment decisions; reuse deployment machinery where applicable. | Product/license/security owners | Signed tamper/replay/expiry, offline trust, non-destructive grace, isolation/audit, governed compatibility and rollback. No legal clearance inferred. |

ETL-01/04/16 → B01/B02; ETL-02/03/15 → B02/B04/B05; ETL-05/06/07/14 → B03/B05/B08; ETL-08–12 → B05/B06; ETL-13 → B07. LIC-001–008 → B09. Other canonical requirements retain the PR78 register and owner cases; do not assign them to missing journey numbers. SET-02 editable settings and SET-01 account-security decisions remain unresolved; neither authorizes a generic editor.

Historical IMP-001–062 stay SOURCE_NOT_RECOVERED and OC-IMP proposals are not silently approved. Newly merged RM-DEF observations require their own reproduction and acceptance; they are not additional numbered journey definitions.



## Follow-on disposition: OC-ETL-003 (2026-11-05)

Source `f57153836615fb07d748ede6b49af6a11dba96fe` closes the bounded CF-02 populated-foundation rollback and CF-03 supported HTTP concurrent graph risks with controlled PostgreSQL evidence: [report](../../verification/oc-etl-003/REPORT.md), [rollback contract](../../verification/oc-etl-003/ROLLBACK_COMPATIBILITY.md), [concurrency acceptance](../../verification/oc-etl-003/CONCURRENCY.md). ETL-01 workflow/job foundation and dependency integrity, inherited §10 evidence preservation, and backlog B01/B02 now have 84 passing regression tests plus six migration/recovery groups. Per-workflow serialization and shared authorization-reader locking preserve exclusive revocation protection. Applied migrations are unchanged. Prior rows remain historical baseline observations. This does not complete the remaining workflow UI, policy evaluation or provider work, certify every historical downgrade, or recover missing numbered journey authority. Owner acceptance remains pending; all release gates remain unchanged.


## OC-ETL-003A.1 CI compatibility and owner-decision alignment (2026-11-06)

[CI matrix](../../verification/ci-roadmap-alignment/CI_REQUIREMENTS_MATRIX.md) and [remediation evidence](../../verification/oc-etl-003a/REPORT.md) reconcile the four migration-contract CI regressions. Local controlled tests preserve populated state, explicit empty rollback paths, authorization and per-workflow transaction safeguards. Nine owner decisions supplied in OC-ETL-003A.1 use OWNER_APPROVED_CONTROLLED_SCOPE — INDEPENDENT_UAT_PENDING; historical pending-acceptance records are retained as snapshots. These decisions are not CI, independent UAT or genuine-provider certification. B00 still requires 30 numbered journey definitions; Journey20 excluded and Journey32 skipped. B04 / OC-ETL-004 remains the subsequent implementation task after hosted CI closure. CHK-001 FAIL, CHK-002 BLOCKED, SECURITY BLOCKED, RELEASE NO-GO.


## OC-ETL-004 — supported Workflow/Job UI verification (2026-11-06)

Implementation `1d3004d`, exact accepted technical source `6a9c7a2cc2eafbac76b6e7b48a54d35c9d115f19`: [evidence](../../verification/oc-etl-004/2026-11-06/REPORT.md), [open contracts](../../verification/oc-etl-004/2026-11-06/OPEN_GAPS.md). This is controlled verification, not owner acceptance. Historical baseline observations above remain unchanged.

| Requirement | Implemented and verified | Unimplemented/blocked | Acceptance |
|---|---|---|---|
| ETL-02 | Workflow list/create/edit/details, timezone/weekdays/windows/duration/SLA, persisted reload | Frequency/recurrence, detailed calendar and authoritative activation/occurrence semantics G1/G4/G5 | PARTIALLY_IMPLEMENTED; verified supported scope; owner pending |
| ETL-03 | Child name/host/runtime create/edit/reload; immutable parent/customer/environment; legacy unassigned rows preserved | Distinct long-running threshold and native PipelineJob binding G2/G3 | PARTIALLY_IMPLEMENTED; verified supported scope; owner pending |
| ETL-15 | Configuration workspace under Resource Management, directed dependencies, read-only receipt/freshness/readiness projection, tenant guards and failed-save preservation | Full operational Workflow readiness/outcomes and provider connectivity G4/G5/G6 | PARTIALLY_IMPLEMENTED; 19 authenticated browser groups; owner pending |
| ETL-16 | Actual secured APIs and UI role/tenant negatives; retained request hooks/audit/DAG locks; seven concurrency/security regressions | Broader security/release/provider gates remain independent | IMPLEMENTED_VERIFIED for this bounded configuration path; not full ETL acceptance |

85 PostgreSQL/HTTP regression cases pass, 45 frontend cases pass, six migration preservation/recovery groups pass. Exact raw outcomes and cleanup are in the evidence package. Backend configuration validity is explicitly supported-child-runtime-only; BLOCKED activation and UNVERIFIED provider states are not inferred healthy from persistence. All 31 included journeys, 30 SOURCE_NOT_RECOVERED numbered definitions, excluded Journey20 and skipped Journey32 are preserved. Nine prior owner decisions remain OWNER_APPROVED_CONTROLLED_SCOPE — INDEPENDENT_UAT_PENDING; no new ETL approval. CHK-001 FAIL, CHK-002 BLOCKED, SECURITY BLOCKED, RELEASE NO-GO.


## OC-ETL-005 — current native staging and proposed binding/readiness contracts (2026-11-06)

[Native contract](../etl/OC_ETL_005_NATIVE_BINDING_CONTRACT.md), [readiness authority](../etl/OC_ETL_005_READINESS_CONTRACT.md), [decision register](../etl/OC_ETL_005_DECISION_REGISTER.md); [execution evidence](../../verification/oc-etl-005/REPORT.md). Product baseline `9c021bbb94de3017bdc9f41b6a774d7b378ae9a7`; test-only source `3852c8d81f6fad4628c30f3cd0f8adaea6dc52f7`. ETL-03/05/14/15/16 and ETL-02 readiness authority reuse the existing resource→Job→Workflow chain and generation-fenced sources. One new current-contract test has 36 real HTTP assertions; full owned lab86 PASS including prior UI19 groups and migration6 groups. No product handlers, permissions, schemas or collector code changed.

Existing indirect native-candidate registration can stage a Workflow child under quarantine; this refines G3 without claiming a complete confirmed/temporal binding. Existing association removal deletes its tuple row while keeping tested history/evidence, so full binding provenance/replacement remains a D06 design blocker. D01–D10 new choices are PROPOSED / PENDING accountable approval. G1/G2 owner-source semantics, G3 temporal design, G4 aggregate activation, G5 lifecycle and G6 independent acceptance/provider evidence remain explicit. Next bounded slice: review D01–D06 then implement only the approved additive contract. No new ETL acceptance; nine prior controlled owner decisions, all31 included journeys,30 unrecovered definitions, Journey20 excluded and32 skipped remain. CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.


## OC-ETL-006 — owner-approved temporal claim registry and six-dimension readiness (2026-11-06)

Owner approval D01–D06 is recorded in `docs/verification/oc-etl-006/APPROVAL_AND_SCOPE.md`; it supersedes prior owner-pending design requests, not independent signoffs. Exact tested source `8e7cdf91d70f19a19c1cdf8d763818446b1c179f`. Additive0040, immutable scoped claim versions/method snapshots and terminal retirement, transactional ownership/authorization, receipt constraints, fail-closed opted-in routing, six backend dimensions and existing Resource Management UI are implemented. 104 PostgreSQL/API regression cases PASS, 9 new +19 retained browser groups, 46 frontend tests, six retained migration groups and actual104-table temporal restore comparison. Counts overlap.

ETL-02 remains PARTIAL (frequency/calendar authority D07). ETL-03 native claim/version/configuration is VERIFIED; qualified authority, positive confirmation and live cutover remain BLOCKED D09. ETL-05/14 receipt constraints/negative attribution verified; new qualified positive receipt routing NOT TESTED. ETL-15/16 supported configuration, saved/reloaded claims/history and six blocked/unverified readiness dimensions VERIFIED; full aggregate ACTIVE/HEALTHY and complete occurrence semantics remain BLOCKED. No acceptance or provider certification inferred.

Next implementation prerequisites: exact D09 authority attestation and qualification; active source handoff/receipt reconciliation; old-writer version fencing/rollback before container deployment. No repeat D01–D06 owner approval is required. D07/D08 and independent UAT remain open. All31 included journeys/30 SOURCE_NOT_RECOVERED numbered definitions, Journey20 excluded and32 skipped, nine previous owner controlled-scope approvals remain unchanged. [Execution, failures, cleanup and limits](../../verification/oc-etl-006/REPORT.md) (repository-relative path; see PR80 for exact links). CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.


## OC-ETL-007 — authority verification and database writer fence (2026-11-06)

Exact tested source `2b8eada577d0a56358d599c2f3a5e02d687b30a1`; [report](../../verification/oc-etl-007/REPORT.md). Implemented provider-independent signed/native-source envelopes, conditional genuine-attestation confirmation/receipt ownership and a PostgreSQL protocol1 fence. Actual117-case suite PASS, including104 retained +13 new, 23 table-specific refusal branches, two exact older source versions, 107-table restore comparison, four new browser contract/denial groups. Counts overlap. No genuine provider attestation/qualified receipt is seeded; test issuers cannot qualify. Old writers are fenced, not operationally rollback-certified.

ETL-03/05/14 native authority and provenance remain PARTIAL: structural/negative gates verified; qualified positive admission, canonical alias owner conflicts and live/stale-generation handoff BLOCKED. ETL-15/16 current UI/readiness support remains VERIFIED_BOUNDED_SUBSET, activation BLOCKED/health UNVERIFIED without evidence. D01–D06 approval is preserved; user OC-ETL-007 authorizes generic attestation design only, not an exact provider target. No new functional owner acceptance inferred. D07/D08 and independent UAT pending.

Next executable prerequisites: explicit exact-build read-only target + accountable verifier/issuer evidence; qualify confirmation/receipt/expiry/cutover; authority-aware rollback image or tested safe degraded mode before isolated candidate/deployment. 31 included journeys/30 SOURCE_NOT_RECOVERED numbered definitions retained; Journey20 excluded/32 skipped, nine controlled owner decisions unchanged. CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.


## OC-ETL-008A — Pentaho offline qualification preparation (2026-11-07)

[Preparation package](../../verification/oc-etl-008/REPORT.md) inventories existing Server scheduler/export versus Carte execution/status contracts and proposes UNVERIFIED exact-build endpoint candidates. ETL-03/05/14/15/16 remain bounded/partial as recorded; no positive provider authority, receipt admission, active cutover, operational old-image rollback or new acceptance is certified. Offline parser/signature fixtures never create qualified proof. D07/D08 policy dependencies remain pending; no calendar/threshold semantics added.

Next: explicitly authorized exact-build read-only target, accountable issuer/reviewer, native object/schedule/execution identity chain and scoped TLS/network/credential approval before any live reads. Current nine acceptance selections Pending; historical OWNER_APPROVED_CONTROLLED_SCOPE — INDEPENDENT_UAT_PENDING dispositions preserved.31 journeys/30 unrecovered numbered definitions and Journey20 excluded/Journey32 skipped unchanged. CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.
