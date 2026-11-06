# Test And Owner Acceptance Matrix

Baseline: PR #80 source `e69528ad2b826398474382f34126feeca740f6a6`; main/merge-base `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`. Working branch `dev/post-pr78-architecture-closure-20261105`. Assessment date: 2026-11-05. Source presence, controlled verification, genuine-provider certification and owner acceptance are separate dimensions. No product code or migration is changed by OC-ARCH-001.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.** Journey 20 Service Catalog excluded; Journey 32 Kubernetes/container observability skipped. No provider execution, scheduler writes, job retry/termination controls, merge or deployment.

## New execution at the baseline SHA

| Check | Command | Result | What it proves / does not prove |
|---|---|---|---|
| ETL foundation | `cd backend && .venv/bin/python -m unittest discover -s tests -p test_etl_workflow_foundation.py -v` | 16 PASS, 0 FAIL, 0 SKIP; exit 0 | Schema validation, models, mocked route permission/update safeguards. No real request scope, database, migration or browser coverage. evidence/etl-foundation.log |
| ETL Clear filters | `cd frontend && node --test scripts/etl_filters.test.mjs` | 2 PASS, 0 FAIL, 0 SKIP; exit 0 | Source-pattern assertions for four defaults / All environments; not browser execution. evidence/etl-filters.log |
| Actual shared write hook | `evidence/reproduce_scope_gap.py` from backend | FAIL integration behavior: both new models denied 403 | In-memory SQLAlchemy Session calls actual before_flush handler with synthetic admin; no DB/HTTP. Output evidence/workflow-scope-probe.json. Probe exits 0 to report observations, not product PASS. |
| Documentation | `python docs/architecture/unified-implementation-baseline/validate.py` | See VALIDATION.json | File/link/ID/coverage/checksum checks; no runtime acceptance inferred. |

Initial setup had a mistaken relative Python version-check path (exit 127); correct backend .venv command above ran successfully. Initial GitHub search lacked a required type qualifier (422), then was repeated with is:issue/is:pull-request; raw scoped search results retained. No repository code was changed for those tooling errors.

## Required next acceptance boundaries

| Requirements | Controlled execution still required | Owner/provider acceptance |
|---|---|---|
| ETL-01–04/16 | B01/B02 authenticated HTTP + PostgreSQL + 0039 preservation, authorization, audit, DAG race | Product/backend/security owner reviews exact evidence, not just mocked guard calls |
| ETL-05–08/14 | Stable native source IDs, mutable row terminal transition, late updates, independently persisted receipts, restart/retention/fencing | Provider owner authorizes exact build/schema; independent reviewer certifies only executed methods |
| ETL-09–13 | Effective policy version snapshots, event/alert lifecycle, missing data, dedup/outbox/recovery and channel negatives | Product approves unresolved catalog/channel/override details first |
| ETL-15 | Actual browser Workflow→Job editor, persistence, errors, narrow roles and tenant switches | Owner UAT after integration; filter source test is insufficient |
| V1.6 A1–D5 / RT-001–020 | Use approved reconstructed index from ARCH_ETL_001_V16.md; retain exact source/method/build/customer/generation/hash/expected/actual evidence | Genuine installed CLI/Server/Carte runtime plus independent approval; no mocked certification |
| LIC-001–008 | Cryptography/offline/grace/identity and licensing-specific authorization tests after contract decisions | Accountable product/security/license owner; no invented signoff |
| 30 missing journey definitions | No executable acceptance criteria invented | Recover signed-off numbered source before allocating behavior |

Each acceptance record requires immutable source SHA, schema revision, method/build, environment, sanitized fixture hash, command, exit, passed/failed/skipped count, log/screenshot, persisted evidence, cleanup and reviewer decision. Distinguish BLOCKED approval/provider access from FAIL behavior and NOT TESTED. No owner signoffs supplied for this task.

PR78 historical tests at fa3a9a24107f465dac6692b2a9ea69b910ff06ee: 552 backend, 38 frontend, controlled HTTP/browser and restoration results are retained in docs/verification/stage-2a-full-development-closure. They predate PR80 migration 0039 and do not certify it. No full backend, browser, PostgreSQL migration, provider, load or collector reliability suite was executed in this documentation-only baseline task. Existing nine owner cases remain linked there, not replaced by CI.



## Follow-on disposition: OC-ETL-003 (2026-11-05)

Source `f57153836615fb07d748ede6b49af6a11dba96fe` closes the bounded CF-02 populated-foundation rollback and CF-03 supported HTTP concurrent graph risks with controlled PostgreSQL evidence: [report](../../verification/oc-etl-003/REPORT.md), [rollback contract](../../verification/oc-etl-003/ROLLBACK_COMPATIBILITY.md), [concurrency acceptance](../../verification/oc-etl-003/CONCURRENCY.md). ETL-01 workflow/job foundation and dependency integrity, inherited §10 evidence preservation, and backlog B01/B02 now have 84 passing regression tests plus six migration/recovery groups. Per-workflow serialization and shared authorization-reader locking preserve exclusive revocation protection. Applied migrations are unchanged. Prior rows remain historical baseline observations. This does not complete the remaining workflow UI, policy evaluation or provider work, certify every historical downgrade, or recover missing numbered journey authority. Owner acceptance remains pending; all release gates remain unchanged.


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
