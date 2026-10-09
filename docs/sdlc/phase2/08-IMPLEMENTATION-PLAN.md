# 08 — Architecture-to-Implementation Plan (Proposed)

## Dependency order
1. **P0 Identity and tenant scope:** implement authentication and common authorize-scoped query helpers for all existing routers; restrict all organization CRUD and nested evidence. Write negative tests first. Track #2, #9.
2. **P0 Template activation:** define desired/applied schema, preview API, idempotent reconciliation and state. Test attachment -> operational Collector + MetricDefinition -> API metric sample. Track #3.
3. **P1 Collector reliability:** correct HTTPS handling, add lease/idempotency/heartbeats, clearly identify unsupported OTEL, Windows/Linux/Pentaho. Track #4, #7, #8, #11.
4. **P1 Truthful UI:** use API-scoped KPI counts and filtered lists; clarify placeholders and current screenshots. Track #5, #10.
5. **P1 Quality and release safety:** pytest, ESLint, Alembic upgrades, real-UI snapshots, secret scanning, ownership/role and error contracts. Track #6, #14.
6. **P1 First source integration:** implement read-only Pentaho execution adapter using a representative, approved source contract; preserve NO_RUN vs NO_RESPONSE vs FAILED semantics.
7. **P2 Integrations:** VM metrics/log transport; SFTP/S3; notification providers and reports, each gated by adapter tests and admin approval.

## Architecture review deliverables
| Design item | Output | Acceptance |
|---|---|---|
| Component architecture | C4 context/container and worker interaction diagrams | Boundaries, failure modes and deployment topology approved |
| ERD and migrations | Tenant-safe physical schema, backfill and upgrade strategy | Constraint tests and migration plans reviewed |
| RBAC | Action-by-role matrix, token/session contract | All API surfaces covered, negative tests defined |
| Template activation | Desired/applied state and reconciliation state machine | Repeatability, rollback and demo vertical-slice proof |
| API contracts | OpenAPI route/change and error-policy docs | Frontend and backend consumers reviewed |
| Runtime and alerts | Collector concurrency, retries, event and alert semantics | Failure injection and idempotency tests |
| QA | Test strategy and CI status gates | Test ownership and release threshold agreed |

## Phase 2 exit gate
- [ ] Identity provider and membership policy confirmed
- [ ] Authorization requirements mapped to each endpoint/entity
- [ ] Template version and activation reconciliation contract accepted
- [ ] Supported collector types and OTEL semantics agreed
- [ ] Database ERD and migration approach reviewed
- [ ] API changes and backward compatibility reviewed
- [ ] Reliability and security threat model reviewed
- [ ] Acceptance test suite design and release gate approved
- [ ] Decision ownership and unresolved choices recorded

## Rules
No production deploy or merge to `main` by this design PR. Implement only after approval through focused feature branches and tests. This design phase must not close P0 security vulnerabilities without passing runtime negative tests.
