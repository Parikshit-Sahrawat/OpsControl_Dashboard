# OpsControl — Unified Journey 1–33 + ETL Implementation Register

Status: **scope approved; implementation and evidence reconciliation in progress**.
Authority: approved OpsControl Dashboard Journey 1–33 roadmap **plus** the approved ETL monitoring architecture. This register is a tracking instrument, not a declaration that any journey is implemented or accepted.

## Scope rules

- Include approved Dashboard Journeys **1–19, 21–31, and 33** (31 journeys).
- **Journey 20: Service Catalog — excluded**. **Journey 32: Kubernetes / Container Observability — skipped/not approved**. Do not implement either without a separate architecture decision.
- Journey 33: Product Lifecycle & Licensing — track LIC-001 through LIC-008, including unresolved evidence and acceptance gates.
- ETL v1.6/v1.7 is monitoring-only: observe externally scheduled work; never dispatch, schedule, retry, or terminate external jobs.
- Link duplicate requirements between roadmaps rather than duplicating implementation or counting them as independently accepted.
- A journey is **verified** only after code mapping, focused tests, integration/UAT evidence, owner acceptance, and required security/reliability gates. No unsupported PASS claims.

## Reconciliation ledger

| Journey | Architecture authority | Implementation evidence | Verification | Owner acceptance |
|---|---|---|---|---|
| 01 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 02 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 03 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 04 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 05 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 06 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 07 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 08 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 09 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 10 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 11 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 12 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 13 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 14 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 15 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 16 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 17 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 18 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 19 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 20 | EXCLUDED — Service Catalog | Out of scope | N/A | N/A |
| 21 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 22 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 23 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 24 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 25 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 26 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 27 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 28 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 29 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 30 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 31 | APPROVED — confirm exact journey requirements from signed-off architecture | Pending code-to-requirement mapping | Not yet verified | Pending |
| 32 | SKIPPED — Kubernetes / Container Observability | Out of scope | N/A | N/A |
| 33 | APPROVED — Product Lifecycle & Licensing (LIC-001–008) | Pending code-to-requirement mapping | Not yet verified | Pending |

## ETL architecture delivery matrix

| Capability | Evidence to inspect | Status |
|---|---|---|
| Workflow → Job ownership, configuration, activation | ETL API, schemas, migration 0039, frontend | Partial; tests not yet certified |
| Read-only native execution evidence | persisted execution histories, provider collectors | Partial |
| Source polling / overlapping scans / checkpoint safety | collector/runtime and PostgreSQL acceptance | Not certified |
| Job events and workflow lifecycle | native monitoring engine | Pending reconciliation |
| Workflow SLA, expected windows, missing/late/incomplete runs | evaluation service and tests | Pending |
| Dependency DAG and violation detection | dependency APIs and event evaluator | Partial |
| Evidence correlation and alert separation | correlation and incident services | Partial |
| Operational React UI | workflow/job screens and monitoring integration | Pending |
| Authenticated UAT and genuine Pentaho certification | UAT evidence | Pending / blocked |
| Settings and remaining approved journeys | requirement register, backend and frontend | Pending reconciliation |

## Execution policy

- Implementation-first development with logical commits and focused tests. Full 13-workflow CI reconciliation at implementation milestones.
- Preserve tenant isolation, RBAC, migration compatibility, idempotency, and durable PostgreSQL acceptance semantics.
- Preserve all existing security and release controls; no merging, deployment, waivers, or branch-protection changes without separate authorization.
- Current release posture: **CHK-001 FAIL; CHK-002 BLOCKED; SECURITY BLOCKED; RELEASE NO-GO**.

## Next evidence tasks

1. Locate the exact signed-off Journey 1–33 requirements and ETL decision register; replace placeholder authority text with precise requirement IDs and source links.
2. Trace each requirement to implementation files, tests, UAT evidence, and responsible owner.
3. Identify shared ETL/journey requirements, dependencies, gaps, and safe implementation sequencing.
4. Implement and test missing scope in reviewable commits; record failures rather than converting unverified work into PASS.
5. Complete milestone-level CI, migration, authenticated UAT, reliability and security acceptance before requesting merge.
