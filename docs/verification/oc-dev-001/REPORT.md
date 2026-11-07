# OC-DEV-001 — full-product development gap reconciliation

2026-11-07. **Audit/backlog delivered for review; no implementation sprint, formal UAT, merge or deployment started.** Main **`ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`**; draft PR80 **`958193f266c89302b2f1919e3703faece591e0af`**. Audit-only branch audit/oc-dev-001-full-product-reconciliation from main. Final documentation commit and review PR are reported after commit. PR80 is not modified by this work.

## Navigation and authority

[Baselines/branch delta](BASELINE_AND_BRANCH_RECONCILIATION.md) · [full feature inventory](FULL_FEATURE_INVENTORY.md) · [requirements CSV](REQUIREMENTS_GAP_MATRIX.csv) / [JSON](REQUIREMENTS_GAP_MATRIX.json) · [coverage CSV](AUTOMATED_TEST_COVERAGE_MATRIX.csv) · [master backlog CSV](MASTER_DEVELOPMENT_BACKLOG.csv) / [JSON](MASTER_DEVELOPMENT_BACKLOG.json) · [dependency graph](DEVELOPMENT_DEPENDENCY_GRAPH.md) · [five sprints](NEXT_FIVE_SPRINTS.md) · [risks/decisions](RISKS_AND_EXTERNAL_BLOCKERS.md).

Audit view of existing canonical authorities, **not a competing canonical register**.134 prior registered IDs +24 newer unique ETL/licensing IDs = **158**. This includes proposals and62 unrecovered historical IDs; it is not158 approved features or a completion percentage. Each ID counted once under one primary module; overlapping feature references do not add counts.31 included journeys/30 unrecovered numbered definitions are a separate dimension;20 excluded,32 skipped. Kubernetes and Service Catalog remain excluded. PagerDuty/ServiceNow remain retired pending authority resolution.

## Candidate requirement classifications

| Status | Count |
|---|---:|
| IMPLEMENTED_AUTOMATED_VERIFIED | 14 |
| PARTIALLY_IMPLEMENTED | 27 |
| IMPLEMENTED_TEST_GAP | 13 |
| REQUIREMENT_AUTHORITY_PENDING | 31 |
| BLOCKED_EXTERNAL_DEPENDENCY | 5 |
| SUPERSEDED_OR_EXCLUDED | 4 |
| SOURCE_NOT_RECOVERED | 62 |
| NOT_IMPLEMENTED | 2 |

IMPLEMENTED_AUTOMATED_VERIFIED means the bounded named capability has controlled automated evidence; it does not imply every broader end-to-end edge, independent UAT, provider or release acceptance. Main-specific classification/source presence is recorded separately.13 test-gap rows are not silently called complete. Two NOT_IMPLEMENTED rows identify ETL event-rule separation and ETL-specific inherited policy, whose detailed policy prerequisites remain explicit.31 authority-pending rows are not coding permissions. Four excluded/superseded rows are not failures.

| Primary module / authority bucket | Requirement IDs |
|---|---:|
| Resources | 12 |
| Access | 6 |
| Settings | 6 |
| Telemetry | 4 |
| VM | 3 |
| NativeBinding | 2 |
| API | 2 |
| Excluded | 2 |
| Topology | 1 |
| Operations | 6 |
| Deployment | 4 |
| Templates | 2 |
| ETL | 19 |
| Incidents | 1 |
| Authority | 18 |
| HistoricalAuthority | 62 |
| Licensing | 8 |

Requirement triage priorities: {'P1': 60, 'P2': 88, 'P0': 10}; priorities are proposed review urgency, not recovered historical severity. Source-not-recovered rows do not receive invented functional severity.

## Master backlog

**55 items:**33 coding,8 decisions,6 external qualification,2 formal UAT,6 verification. These are prospective slices, not newly approved requirements. All requested columns, exact references, dependencies, observable acceptance and S/M/L/XL relative complexity are in the CSV. External availability UNESTIMATED.

| Backlog priority | Items |
|---|---:|
| P0 | 16 |
| P1 | 36 |
| P2 | 3 |

Backlog module counts: {'Telemetry': 3, 'Runtime': 5, 'Access': 2, 'Settings': 5, 'Resources': 3, 'Templates': 1, 'Signals': 1, 'Operations': 4, 'API': 1, 'VM': 1, 'Notifications': 2, 'Topology': 2, 'Retention': 2, 'Deployment': 4, 'Security': 2, 'Licensing': 2, 'ETL': 7, 'NativeBinding': 4, 'Authority': 1, 'Acceptance': 2, 'Performance': 1}.

Top10 coding priorities (ordered for this review; prerequisites still apply):

- **OC-DEV-101** — Central PostgreSQL durable-spool admission and recovery (P0; prerequisites: OC-DEV-201).
- **OC-DEV-103** — Cross-resource write authorization and revocation regression closure (P0; prerequisites: none beyond authorization).
- **OC-DEV-135** — Global responsiveness under sustained ingestion RM-DEF-036 (P0; prerequisites: OC-DEV-103).
- **OC-DEV-121** — Cross-module migration/backup/restore preservation (P0; prerequisites: none beyond authorization).
- **OC-DEV-107** — Source attribution and independently reconciled telemetry receipts (P0; prerequisites: OC-DEV-101, OC-DEV-103).
- **OC-DEV-106** — Template attachment → effective config → activation vertical slice (P1; prerequisites: OC-DEV-105).
- **OC-DEV-105** — Resource onboarding/draft/edit and lifecycle closure (P1; prerequisites: OC-DEV-103).
- **OC-DEV-108** — Signal-to-alert-to-incident recovery vertical slice (P1; prerequisites: OC-DEV-107).
- **OC-DEV-123** — Runtime image and tooling security remediation backlog (P0; prerequisites: none beyond authorization).
- **OC-DEV-132** — Authority-aware older-writer rollback candidate (P0; prerequisites: OC-DEV-501, OC-DEV-121).

## Dependency / sprint recommendation

Critical delivery path **201 detailed PG spool contract →101 durable admission →107 attributed/reconciled receipts →108 alerts/incidents →118 delivery/109 projections**. Preserve centralized PostgreSQL design; no unapproved queue/fork/replay-primary replacement. Separate native path301→130→131/129, policy204/207→125/127/128 and compatibility121/501→132→122. DAG cycle checks pass; no unnecessary requirement to finish formal UAT, merge PR80 or recover all numbered journeys before unrelated safe development.

**Recommend Sprint1:** resource ownership/configuration vertical slice (103/105/106), preservation121 and global performance135, with201/501/503 and security123 in parallel. Exact scope/capacity needs owner authorization; no coding begins here. Native positive qualification and new settings/licensing behavior remain gated, not fabricated into the sprint.

## Actual audit executions and coverage gaps

| New bounded check | Result | Source / raw evidence |
|---|---|---|
| Backend contract subset main | **61 PASS,0 fail/error/skip**, forbidden IO0 | main pinned above; logs/main-contract-tests.log |
| Same backend subset PR80 | **61 PASS,0 fail/error/skip**, forbidden IO0 | PR80 pinned above; logs/pr80-contract-tests.log |
| Node helper/source suite main | **38 PASS,0 fail/skip** | logs/main-frontend-tests.log |
| Node helper/source suite PR80 | **46 PASS,0 fail/skip** | logs/pr80-frontend-tests.log |
| PR80 Pentaho/authority offline subset | **60 PASS,0 fail/error/skip**, forbidden IO0 | logs/pr80-authority-offline.log |
| PR80 existing traceability validator |PASS56 IDs,31 journeys,nine historical decisions | logs/pr80-traceability.log |
| This package CSV/JSON/provenance/unique-ID/DAG/link/hash validation |Recorded in VALIDATION.json; no acceptance inferred | validate_reconciliation.py; logs/validation.log |

Counts overlap heavily: the same61 cases run on two baselines and Pentaho subsets overlap. Do not total these as unique coverage. Main/PR80 Node helpers are not mounted React component tests; no mounted framework located. Newly executed contract suite uses guarded DB/network/subprocess boundaries and mocks where existing tests do, not real HTTP/PostgreSQL authorization integration. No fresh PG migrations, browser/runtime integration, genuine provider, formal UAT, throughput benchmark or security certification was executed by this audit; prior controlled evidence remains identified by its original SHA.

Coverage rows: {'HISTORICAL_BOUNDED_PASS; no complete-current-case crosswalk': 13, 'CURRENT_BOUNDED_FILE_SUITE_PASS': 4, 'DEFINITION_OR_ADJACENT_MODULE_ONLY': 54, 'NO_SPECIFIC_AUTOMATION_MAPPING': 87}.87 rows have no specific automation mapping (mostly unavailable authority/proposals/licensing); definition/adjacent-test presence is not complete execution. SOURCE_SYMBOL_INDEX distinguishes static markers/routes/tables from tested runtime. Missing automation includes mounted components, full source-to-UI receipt reconciliation, safe positive authority/cutover, approved event/policy matrices, global ingestion load, installer/provider and independent acceptance.

Current main hosted snapshot: **8 success /3 skipped /1 failed publish preflight**. PR80: **18/18 success**. No unrelated CI rerun. Main failed assertion detail was unavailable in downloaded logs; retained failure stage/annotations and proposed503 investigate without publication or bypass. Source review/matrix generation initially caught one mistyped remote-worker path; failed audit-generation log preserved, corrected to actual scheduler/agent paths, no product change.

## Remaining decisions and stop point

D07/D08, settings/account contract, exact event/override policy, native target/issuer/read-only proof, licensing detail, freshness/SLO/PKI/escalation, source/namespace recovery and independent security/DR/provider/UAT remain as risks. All nine current owner selections **Pending**; historical controlled approvals unchanged. Production collector0.123.0 unchanged. No shared environment or owner's separate UAT accessed. No task containers/services/volumes/credentials created; nothing required Docker cleanup. Work stops after publication for review; **OC-DEV-002 not authorized or started**.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**

