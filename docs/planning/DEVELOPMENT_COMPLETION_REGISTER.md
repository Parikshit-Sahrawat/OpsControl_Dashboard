# OpsControl Development Completion Register v1.0

Status: OWNER-APPROVED SCOPE; PRELIMINARY SOURCE-TRACEABILITY INVENTORY; NOT A FULL SOURCE/EXECUTION AUDIT.
Baseline: main 4ebd8d8a64dff75ef7577c169c76e651e435dcc7 (2026-10-22 check). PR #41 is unmerged at c98809e7de630ed9fbb04178acc7e58dd76ba434 and must be reconciled separately. PR #33 protected.
Governance: Issue #42. Do not infer completion from sprint number, fixture success or PR description. Status codes: IMPLEMENTED_REPORTED, PARTIAL, NOT_IMPLEMENTED_REPORTED, SOURCE_AUDIT_REQUIRED, EXTERNAL_ACCEPTANCE_PENDING. The 'evidence' column is a lead for source audit, not proof of all individual feature files.

| ID | Approved requirement / feature | Workstream | Current status | Evidence/source inspection starting points | Missing work / verification | Dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| RM-01 | Customer Organizations are monitored customers, separate from provider departments | DEV-01 | IMPLEMENTED_REPORTED | docs/architecture/PRODUCT_ALIGNMENT_ADDENDUM.md; docs/verification/sprint14r/REPORT.md | Audit full frontend/API/DB mapping and UAT | RBAC |
| RM-02 | Resource Management sole onboarding, inventory and configuration control plane | DEV-01 | PARTIAL | docs/architecture/PRODUCT_ALIGNMENT_ADDENDUM.md; ARCH_001_V16.md | Audit canonical resource workflows and persistence | RM-01 |
| RM-03 | Compact resource lists, collapsible sidebar, responsive UX | DEV-01 | PARTIAL | docs/verification/sprint14r/REPORT.md; PR #41 | Integrate PR #41 when all gates pass; verify current exact UI | UI-001–023 |
| RM-04 | Collector multi-method add-one-at-a-time configuration | DEV-02 | PARTIAL | docs/verification/sprint14r/REPORT.md; docs/verification/sprint14r/PRODUCTION_READINESS.md | Real collector methods, lifecycle, end-to-end evidence | Identity and agent |
| RM-05 | Method-specific canonical collection identity; one fenced active owner | DEV-02 | IMPLEMENTED_REPORTED | ARCH_001_V16.md; docs/verification/sprint14r/REPORT.md | Exact source audit and adversarial regression | RM-04 |
| AM-01 | Provider employee departments, teams, roles and customer-scoped RBAC | DEV-01 | PARTIAL | docs/architecture/PRODUCT_ALIGNMENT_ADDENDUM.md; docs/verification/sprint14r/REPORT.md | Complete UI functional actions, negative scopes, user UAT findings | RM-01 |
| AM-02 | Access Management employee table separate Name/Username/Email and header actions | DEV-01 | SOURCE_AUDIT_REQUIRED | Approved UAT Cycle 2 findings #3, #6, #7 | Inspect actual components; implement remaining fixes | AM-01 |
| AM-03 | Departments Members & access functional navigation/assignment | DEV-01 | SOURCE_AUDIT_REQUIRED | Approved UAT Cycle 2 finding #8 | Backend data, roles, scopes, read-only guard and UI | AM-01 |
| UI-001–023 | All approved UI alignment findings | DEV-01 | SOURCE_AUDIT_REQUIRED | PR #41; docs/verification/sprint14r/REPORT.md | Reconstruct item-by-item trace and verify all tests | PR #41 |
| SET-01 | User profile, account security, preferences and notification settings | DEV-01 | SOURCE_AUDIT_REQUIRED | Owner approval in Issue #42 | Audit existing profile routes, implement missing full UI/API | AM-01 |
| SET-02 | Authorized global application settings with safe persistence and audit trail | DEV-06 | SOURCE_AUDIT_REQUIRED | Owner approval in Issue #42 | Define safe editable keys, RBAC, audit, validation, secret references | AM-01 |
| HELP-01 | User manual, technical documentation, provider SOPs/runbooks, FAQ | DEV-01 | SOURCE_AUDIT_REQUIRED | Owner approval in Issue #42 | Content structure, routes, search/navigation and SOP permissions | AM-01 |
| TEL-01 | Windows/Linux OpsControl Agent install/enrollment, authenticated collector bridge | DEV-02 | PARTIAL | docs/verification/sprint14r/PRODUCTION_READINESS.md | Real OS package/install, certificates, canary and rollback | OPS_DEPLOY_001.md |
| TEL-02 | Logs, Metrics, Traces with explicit collection method identity | DEV-02 | PARTIAL | ARCH_001_V16.md; docs/verification/sprint14r/IMPROVEMENT_REGISTER.md | Verify each data path, expected signals and freshness | TEL-01 |
| TEL-03 | Telemetry durability, backpressure, replay, drop/loss accounting | DEV-02 | PARTIAL | OC-IMP-004; P0-02 | Complete end-to-end failure/restart and sustained load | TEL-01 |
| TEL-04 | Certificate rotation/revocation, private network trust, clock uncertainty | DEV-06 | PARTIAL | OC-IMP-002/003/007; P0-05/06 | Provider CA and real network evidence | Approved topology |
| CMP-01 | Windows/Linux VM/EC2 native health and operational views | DEV-03 | PARTIAL | P1-06; sprint22 roadmap | Real host validation and lifecycle | TEL-01 |
| CMP-02 | Each VM/EC2 exclusively owned by one customer | DEV-03 | SOURCE_AUDIT_REQUIRED | Latest owner architecture decision | Correct older shared-VM spec; validate FK, API and scope | RM-01 |
| DP-01 | Read-only Pentaho ETL, execution outcome vs monitoring health | DEV-03 | PARTIAL | docs/verification/sprint14r/REPORT.md; P0-01 | Genuine RT-001–020 and native child identity | Installed build |
| DP-02 | Nine native platform classifications and immutable version-aware profiles | DEV-03 | PARTIAL | ARCH_001_V16.md; OC-IMP-013 | Version/method-specific capability evidence per adapter | Provider access |
| API-01 | API/TLS/synthetic endpoint monitoring and operational history | DEV-03 | PARTIAL | sprint25 roadmap; OC-IMP-005 | Real target journeys and scoped evidence | TEL-02 |
| K8S-01 | Canonical cluster may be associated with multiple authorized customers | DEV-04 | SOURCE_AUDIT_REQUIRED | Latest owner architecture decision; historical P0-03 superseded for VM | Versioned cluster associations, namespace/workload attribution and negative tests | AM-01 |
| K8S-02 | EKS discovery, nodes, pods, cluster health, private API connectivity | DEV-04 | PARTIAL | sprint23 roadmap; OPS_DEPLOY_001.md | Real authorized EKS and runtime compatibility | K8S-01 |
| TOP-01 | Customer-safe topology, relationships, freshness and history | DEV-04 | PARTIAL | sprint27–29 roadmap; P1-04 | Graph identity, provenance and scale | K8S-01 |
| OPS-01 | Alerting, incident/service ownership, notifications and escalation | DEV-05 | PARTIAL | OC-IMP-012/014; P1-07 | Real provider sandbox and customer-negative delivery | TEL-02 |
| OPS-02 | Versioned SLO policy, denominator and reproducible evidence | DEV-05 | NOT_IMPLEMENTED_REPORTED | P1-05; OC-IMP-018 | Policy design, implementation and tests | Original source governance |
| OPS-03 | Recovery validation: health, workload success, dependencies, observation and evidence | DEV-05 | PARTIAL | OC-IMP-018 | Explicit recovery criteria and negative/unknown paths | OPS-01 |
| OPS-04 | Coverage/blind spots, self-monitoring and customer-safe reporting | DEV-05 | PARTIAL | OC-IMP-001/006/010 | Whole data path and stale-state verification | TEL-03 |
| PLT-01 | Populated migrations, backup, encrypted restore, WAL/PITR, DR | DEV-06 | PARTIAL | P0-04; OC-IMP-011 | Measured restore and key custody | Approved topology |
| PLT-02 | Stage B branch-aware Feature UAT and controlled deployment | DEV-06 | PARTIAL | PR #40; docs/verification/stage-b-uat/ACCEPTANCE.md | Real runner/environment/backup/restore acceptance | Infrastructure |
| PLT-03 | Security, residency, legal holds and retention | DEV-06 | PARTIAL | OC-IMP-016; ARCH_001_V16.md | Policy and negative export checks | Legal/data policy |
| PLT-04 | Performance, fleet lifecycle, bounded inventories, storage/cost | DEV-06 | PARTIAL | P1-01/03; P2-02; sprint35–39 | Representative measured workloads | TEL-03 |
| REL-01 | Seven release gates and independent evidence-backed sign-off | PHASE-02/04 | EXTERNAL_ACCEPTANCE_PENDING | docs/verification/sprint14r/PRODUCTION_READINESS.md; OC-IMP-015 | Independent acceptance and deployment approval | Development Complete |

## Approved improvement mapping
OC-IMP-001 DEV-05; 002 DEV-06; 003 DEV-06; 004 DEV-02; 005 DEV-03; 006 DEV-05; 007 DEV-02/06; 008 DEV-02; 009 DEV-06; 010 DEV-05; 011 DEV-06; 012 DEV-05; 013 DEV-03; 014 DEV-05; 015 Phase 2/4; 016 DEV-06; 017 DEV-04 (reinterpret as approved shared Kubernetes, not shared VM); 018 DEV-04/05.
Original IMP-001–062 exact definitions remain SOURCE_NOT_RECOVERED and must not be fabricated. AUD01–08 remain tracked in docs/verification/arch-etl-001-v16-r1/sprint10/CODE_AUDIT_FINDINGS.md.

## Required audit enrichment
For each row, Codex must replace source starting points with exact implementation file paths, API endpoints, models/migrations, tests, execution evidence and SHA. Record explicit absence if none. Expand grouped UI-001–023 and platform adapters into one row each after recovering original approved wording. Keep a changelog when superseding a historical requirement.
