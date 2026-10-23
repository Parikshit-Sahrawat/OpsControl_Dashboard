# Issue #47 — canonical Development Completion Register reconciliation

Status: **DELIVERED FOR REVIEW** (documentation only). This report does not certify Phase 1 Development Complete, independent UAT or production readiness, and does not authorize implementation of proposed OC-IMPs. Source snapshot and draft-PR context are fixed below; later implementation needs a new exact-SHA test gate.

## Source and approval reconciliation

| Authority/evidence | Exact revision and result |
| --- | --- |
| `origin/main` | `ae4df971d07fa65bbe9e50fbdacba2c68ceae7be`, verified on 2026-10-22 before branch creation. Issue #44/#45 integration is in main. |
| [Issue #42](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/42) | Approved four phases, Settings/Help scope and one-customer VM versus explicitly shared Kubernetes model. It also contains a now-superseded 80% development coverage rule. |
| [Issue #47](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/47) | Requests one canonical register, 26 families and individual UI/OC-IMP/AUD mapping; reiterates no fixed percentage gate. |
| Planning branch `docs/development-completion-register-v1` | `955917474672df8c964e63f384513a2f373661d0`; preliminary `docs/planning/DEVELOPMENT_COMPLETION_REGISTER.md`, older baseline. Reconciled into [canonical register](../../planning/DEVELOPMENT_COMPLETION_REGISTER.md), planning branch untouched. |
| Draft [PR #43](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/43) | Open/draft, head `2b1ade567dd4c0ad4967f3d603e3fdd84cffb782`; 26 audit families, **14 bounded-source COMPLETE / 12 PARTIAL** at `65aa131`. Source audit is evidence, not a parallel requirement catalog. No PR #43 files were changed. |
| [Issue #46 verification report](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/365a1202314c8a744f3cb0cef60cec45976dac54/docs/verification/issue-46/REPORT.md) | Branch commit `365a1202314c8a744f3cb0cef60cec45976dac54` is **not merged**; documentation-only tests at main `ae4df971` confirm controlled onboarding, RBAC, customer isolation and disposable PostgreSQL preservation. Independent UAT is not established. |
| [UI register](../ui-alignment-fix/source/UI_001_023_REGISTER.md) | UI-001–023 individually approved in owner discussion; original UAT Test 1 [source](../ui-alignment-fix/source/UAT_TEST_1_UI_ALIGNMENT_FIX.txt) is present. |
| [Sprint 12 OC-IMP proposal baseline](../arch-etl-001-v16-r1/sprint12/OC_IMP_V20_BASELINE.md) | Explicitly states all 18 entries `PROPOSED_OWNER_REVIEW` and none individually approved. Later shorthand “approved OC-IMP proposals” is not evidence of individual requirement approval. |
| [Sprint 11 source recovery](../arch-etl-001-v16-r1/sprint11/SOURCE_RECOVERY.md) | Original IMP-001–062 definitions and approval revision remain unavailable; eight known titles do not establish detailed scope. |
| [ARCH-001](../../ARCH_001_V16.md), [ARCH-ETL-001](../../architecture/ARCH_ETL_001_V16.md), [Product Alignment](../../architecture/PRODUCT_ALIGNMENT_ADDENDUM.md) | Controlling architecture and owner decision summaries; no architecture file was edited. Full original ENG-001 wording remains unavailable; see `docs/engineering/ENG_001.md`. |

## Completed work incorporated

- **Issue #44 / PR #48:** fix head `52d825c60b354019026652297e431f7bd80d3a6e`; merged via PR #48 (`05ed1200471b729d3af4778d517cea1209ea9eb6`). Sprint 07 Global environments/sidebar and NOC customer/Reports assertions are present in main. The Reports fixture contract is four executions during failure and five after recovery; no backlog entry reopens the already-fixed selectors.
- **Issue #45 / PR #49:** fix head `5f611ce9ca50b953a991f8d2a769ea2246a4f054`; merged through the integration result, with PR #49 merge commit `a5592d1d8d8c39d6d1d167afdd3b4cbf29d9d524` and PR #50/main merge `ae4df971d07fa65bbe9e50fbdacba2c68ceae7be`. `scripts/test-quality.sh` still writes `coverage.json`, `coverage.xml` and text but no fixed `--fail-under`; test failures remain gated. Historical 65% and 80% rules remain historical evidence. This does **not** claim #49's original standalone CI head passed.
- **Issue #46:** developer verification report at `365a120` (unmerged) exercised exact-main `ae4df971`: 25 access security groups plus 7 browser groups, 11 release/restore groups, V1.6 HTTP/browser, 43 focused backend units and 5 frontend tests, plus additional controlled acceptance harnesses. PostgreSQL 17 disposable containers, Alembic `0037_access_boundaries`; no product defect confirmed. Exact commands/outcomes are in its report, not rerun in this documentation task.
- Exact-main workflow evidence in Issue #46: [OpsControl Validation 39827607825](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/39827607825), [continuous quality 39827607578](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/39827607578), [pipeline ownership 39827607355](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/39827607355) passed. Coverage was **82.66% informational** over 7,455 statements in the quality run; ordinary unit stage recorded 503 tests, 208 skipped. [Stage B manual UAT 39827607428](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/39827607428) was skipped by design. These are inherited exact-main results, **not** tests rerun for this docs commit.

## Conflicts and decisions still open

1. **OC-IMP approval:** Sprint 12 register explicitly says all 18 are individually proposed; planning branch/Issue #47 prose calls them approved or approved proposals. Until the owner supplies an item-level approval record or explicitly approves exact amended text, implementation of new OC-IMP requirements is conditional. Existing approved architecture remains binding.
2. **Shared resource wording:** OC-IMP-017 and historical Sprint 12 example describe one VM visible to A/B; latest owner policy in Issue #42 makes each VM/EC2 single-customer. A canonical Kubernetes cluster may be explicitly associated with multiple customers, but its identity, assignment, derived-data and revocation contract needs owner-approved design before schema/runtime work.
3. **Original source authority:** IMP-001–062 original text/revision and full original ENG-001 wording are unrecovered. No assumed approvals or implementation tasks are assigned from titles. An owner-supplied authoritative record would permit later reconciliation.
4. **SLO and legacy method policy:** AUD-07 lacks exact approved versioned SLO semantics; AUD-06's legacy missing method ID is a compatibility/security choice. Both require explicit owner/architecture decision before changing behavior.
5. **Independent UAT provenance:** Owner-reported UI PASS has no exact deployed SHA, image digests, schema, environment and dated case evidence for current main. No acceptance is transferred between revisions.

The active coverage policy is resolved by the later explicit owner decision and actual merged main behavior; no owner approval is sought to reinstate a percentage gate. No broad RBAC or VM-sharing change is proposed. The 18 OC-IMP proposals and original 62 IMP source gaps are **source/approval blockers**, not 80 separate confirmed application defects.

## Phase 1 gap register and next actions

| Workstream | Highest-value confirmed/verification gap | Dependency and source-backed action |
| --- | --- | --- |
| DEV-01 | Per-step onboarding/action consistency, historical Not Found reproduction, Access/Resource UAT layout; Settings/Help scope needs inventory | UI-006/007/009/015/023; use exact-main draft/activation fixtures, fix only reproduced defect; preserve current RBAC and single RM control plane. |
| DEV-02 | Legacy collection-method attribution and end-to-end signal/delivery accounting | AUD-06 and TEL-02 first; approve compatibility policy before changing legacy acceptance. OC-IMP-004 is proposed. |
| DEV-03 | Installed Pentaho/native child identity and eight other build profiles; compute/API real-source freshness | DP-01/02 and CMP/API paths; controlled regression now, RT-001–020 remain NOT RUN, provider acceptance later. |
| DEV-04 | Canonical shared-cluster authorization model; graph query scale/freshness | K8S-01 needs approved contract; AUD-01 source correction must be measured, AUD-02 graph traversal benchmark. No VM-sharing migration. |
| DEV-05 | Incident count/recovery UI, notification delivery, SLO authority | UI-021 regression; AUD-07 and OC-IMP-012/018 require source/approval before new policy code. |
| DEV-06 | Reproducible populated preservation, Stage B runner parity, data-path/performance evidence | Issue #46 local preservation exists; real UAT runner/production DR remain separate; no fixed coverage floor. |

The [backlog](BACKLOG.md) provides **three bounded slices per DEV workstream** with IDs, reuse, missing behavior, frontend/backend/database boundaries, positive/negative tests, acceptance, dependencies and effort estimates. Its top five recommended increments begin with current onboarding verification and now-green pipeline regression. Phase 1 coding is not started here.

## Reconciliation result and limits

[Canonical register](../../planning/DEVELOPMENT_COMPLETION_REGISTER.md): 31 canonical product rows plus 23 approved UI refinements; the 26 audit families are mapped once and not counted as requirements. Eighteen individually proposed OC-IMP entries and eight tracked AUD findings are mapped separately. The 62 original IMP identifiers are individually marked `SOURCE_NOT_RECOVERED`. These counts do not imply product-completion percentages. Source implementation, controlled automated verification, independent UAT and production certification remain separate.

No runtime, migration, test, workflow, security policy, UAT database, Docker volume, deployment or architecture file was changed. PR #33 and PR #43 were read-only. This documentation change did not rerun backend/frontend/browser/CI suites; the exact-main execution evidence above comes from Issue #46 and GitHub workflow reports. Only documentation validation is required for this branch. Production remains **NOT READY**.
