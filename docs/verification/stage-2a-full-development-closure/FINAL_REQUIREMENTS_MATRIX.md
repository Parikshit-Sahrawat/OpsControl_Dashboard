# Final requirement matrix

Source, authority, approved ownership, historical named tests and before/after classifications are retained in [requirements.json](requirements.json). Historical tests are not new executions. See BASELINE_DELTA.md for current-main effects.

| ID | Requirement | Prior | Current | Owner acceptance |
|---|---|---|---|---|
| RM-01 | Customer Organizations are monitored customers, distinct from provider Departments | VERIFIED_PENDING_OWNER | VERIFIED_PENDING_OWNER | Pending |
| RM-02 | Resource Management is sole onboarding/inventory/configuration plane | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Pending |
| RM-03 | Compact lists, collapsible sidebar and responsive UX | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Pending |
| RM-04 | Collector configuration supports multiple independently added methods | VERIFIED_PENDING_OWNER | VERIFIED_PENDING_OWNER | Pending |
| RM-05 | Method-specific canonical collection identity and one fenced active owner | VERIFIED_PENDING_OWNER | VERIFIED_PENDING_OWNER | Pending |
| AM-01 | Internal employees, departments, direct/inherited roles and customer-scoped RBAC | VERIFIED_PENDING_OWNER | VERIFIED_PENDING_OWNER | Pending |
| AM-02 | Employee table Name/Username/Email and header actions | IMPLEMENTED_UNVERIFIED | IMPLEMENTED_UNVERIFIED | Pending |
| AM-03 | Departments Members & access navigation and assignment | IMPLEMENTED_UNVERIFIED | IMPLEMENTED_UNVERIFIED | Pending |
| SET-01 | Profile/account security, display and notification preferences | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Pending |
| SET-02 | Admin-authorized platform settings with safe persistence/audit | NOT_IMPLEMENTED | NOT_IMPLEMENTED | Pending |
| HELP-01 | Manual, technical docs, provider SOP/runbooks, FAQ | PARTIALLY_IMPLEMENTED | VERIFIED_PENDING_OWNER | Pending |
| TEL-01 | Windows/Linux agent install/enrollment and authenticated bridge | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Pending |
| TEL-02 | Logs, metrics, traces with explicit method identity | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Pending |
| TEL-03 | Durable ingestion, backpressure, replay and loss accounting | BLOCKED_RELIABILITY | BLOCKED_RELIABILITY | Pending |
| TEL-04 | Certificate lifecycle/private trust/clock uncertainty | BLOCKED_ARCHITECTURE | BLOCKED_ARCHITECTURE | Pending |
| CMP-01 | Windows/Linux VM/EC2 native operational health | VERIFIED_PENDING_OWNER | VERIFIED_PENDING_OWNER | Pending |
| CMP-02 | One owning customer for each VM/EC2 | VERIFIED_PENDING_OWNER | VERIFIED_PENDING_OWNER | Pending |
| DP-01 | Read-only Pentaho outcome, health, identity and evidence | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Pending |
| DP-02 | Nine platform-native classifications and version-aware profiles | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Pending |
| API-01 | HTTP/TLS/synthetic endpoint operational monitoring | VERIFIED_PENDING_OWNER | VERIFIED_PENDING_OWNER | Pending |
| K8S-01 | Authorized multi-customer canonical Kubernetes clusters | REMOVED_FROM_SCOPE | REMOVED_FROM_SCOPE | Accepted removal — current owner instruction; PR73 merged |
| K8S-02 | EKS discovery and node/pod/cluster health | REMOVED_FROM_SCOPE | REMOVED_FROM_SCOPE | Accepted removal — current owner instruction; PR73 merged |
| TOP-01 | Customer-safe topology relationships, freshness/history | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Pending |
| OPS-01 | Alerting, incident/service ownership and notifications | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Pending |
| OPS-02 | Versioned SLO policy, denominator and reproducible evidence | BLOCKED_ARCHITECTURE | BLOCKED_ARCHITECTURE | Pending |
| OPS-03 | Recovery validation with health, workload, dependencies and observation | VERIFIED_PENDING_OWNER | VERIFIED_PENDING_OWNER | Pending |
| OPS-04 | Coverage/blind spots, self-monitoring and scoped reporting | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Pending |
| PLT-01 | Populated migrations, backup, restore, legal holds and DR | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Pending |
| PLT-02 | Stage B branch-aware Feature UAT and controlled deployment | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Pending |
| PLT-03 | Security, residency, legal holds and retention | BLOCKED_SECURITY | BLOCKED_SECURITY | Pending |
| PLT-04 | Performance, fleet lifecycle, bounded inventory and storage cost | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Pending |
| UI-001 | Expandable/collapsible sidebar navigation groups, active routes, keyboard/mobile support, and preference persistence | IMPLEMENTED_UNVERIFIED | IMPLEMENTED_UNVERIFIED | Pending |
| UI-002 | Replace Resource Management horizontal tabs with a clearly grouped component selector/dropdown | IMPLEMENTED_UNVERIFIED | IMPLEMENTED_UNVERIFIED | Pending |
| UI-003 | Replace Compute Instance onboarding modal with a full-page configuration workspace | IMPLEMENTED_UNVERIFIED | IMPLEMENTED_UNVERIFIED | Pending |
| UI-004 | Provide a vertical desktop stepper for the 10-step Compute onboarding journey and compact mobile navigation | IMPLEMENTED_UNVERIFIED | SUPERSEDED | Pending |
| UI-005 | Eliminate overlaps, clipping, inconsistent spacing, and misaligned form controls | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Pending |
| UI-006 | Standardize Previous, Continue, Save Draft, validation, and primary actions; remove duplicate Next buttons | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Pending |
| UI-007 | Investigate and resolve `Data source not found` / `Not Found` onboarding errors without masking backend failures | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Pending |
| UI-008 | Support independently configured collection methods for one VM-associated OpsControl Agent | IMPLEMENTED_UNVERIFIED | IMPLEMENTED_UNVERIFIED | Pending |
| UI-009 | Implement meaningful backend-confirmed readiness validation before monitoring activation | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Pending |
| UI-010 | Preserve distinction between monitored customer organizations and internal employee departments | VERIFIED_PENDING_OWNER | VERIFIED_PENDING_OWNER | Pending |
| UI-011 | Preserve Resource Management as configuration/inventory and Operations as monitoring/investigation | IMPLEMENTED_UNVERIFIED | IMPLEMENTED_UNVERIFIED | Pending |
| UI-012 | Verify desktop, tablet, mobile, light theme, and dark theme | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Pending |
| UI-013 | Correct Data Pipeline/Pentaho configuration layout, labels, credential references, responsive fields, and stepper | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Pending |
| UI-014 | Correct Access Management explicit access-boundary form layout and scope/permission grouping | IMPLEMENTED_UNVERIFIED | IMPLEMENTED_UNVERIFIED | Pending |
| UI-015 | Improve Department → Employee → Permissions workflow and effective-permission readability without changing RBAC | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Pending |
| UI-016 | Improve Dashboard information hierarchy and empty states; do not treat valid zero-data states as defects | IMPLEMENTED_UNVERIFIED | IMPLEMENTED_UNVERIFIED | Pending |
| UI-017 | Distinguish Compute Health operational adapter evidence from resource inventory | IMPLEMENTED_UNVERIFIED | IMPLEMENTED_UNVERIFIED | Pending |
| UI-018 | Improve Data Pipeline inventory tables, column readability, typography, and responsiveness | IMPLEMENTED_UNVERIFIED | IMPLEMENTED_UNVERIFIED | Pending |
| UI-019 | Distinguish registered API Endpoints from operational service-probe evidence | IMPLEMENTED_UNVERIFIED | IMPLEMENTED_UNVERIFIED | Pending |
| UI-020 | Improve Alerts filter labels and toolbar consistency, without expanding deferred Alerts redesign | PARTIALLY_IMPLEMENTED | VERIFIED_PENDING_OWNER | Pending |
| UI-021 | Correct Incidents pagination and record-count alignment | PARTIALLY_IMPLEMENTED | VERIFIED_PENDING_OWNER | Pending |
| UI-022 | Improve Resource Management nested navigation for Event Parameters and Alert Rules | IMPLEMENTED_UNVERIFIED | IMPLEMENTED_UNVERIFIED | Pending |
| UI-023 | Standardize stepper interaction and presentation across Compute and ETL configuration journeys | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Pending |
| OC-IMP-001 | Original proposal wording retained; no individual approval inferred | BLOCKED_ARCHITECTURE | BLOCKED_ARCHITECTURE | Pending |
| OC-IMP-002 | Original proposal wording retained; no individual approval inferred | BLOCKED_ARCHITECTURE | BLOCKED_ARCHITECTURE | Pending |
| OC-IMP-003 | Original proposal wording retained; no individual approval inferred | BLOCKED_ARCHITECTURE | BLOCKED_ARCHITECTURE | Pending |
| OC-IMP-004 | Original proposal wording retained; no individual approval inferred | BLOCKED_ARCHITECTURE | BLOCKED_ARCHITECTURE | Pending |
| OC-IMP-005 | Original proposal wording retained; no individual approval inferred | BLOCKED_ARCHITECTURE | BLOCKED_ARCHITECTURE | Pending |
| OC-IMP-006 | Original proposal wording retained; no individual approval inferred | BLOCKED_ARCHITECTURE | BLOCKED_ARCHITECTURE | Pending |
| OC-IMP-007 | Original proposal wording retained; no individual approval inferred | BLOCKED_ARCHITECTURE | BLOCKED_ARCHITECTURE | Pending |
| OC-IMP-008 | Original proposal wording retained; no individual approval inferred | BLOCKED_ARCHITECTURE | BLOCKED_ARCHITECTURE | Pending |
| OC-IMP-009 | Original proposal wording retained; no individual approval inferred | BLOCKED_ARCHITECTURE | BLOCKED_ARCHITECTURE | Pending |
| OC-IMP-010 | Original proposal wording retained; no individual approval inferred | BLOCKED_ARCHITECTURE | BLOCKED_ARCHITECTURE | Pending |
| OC-IMP-011 | Original proposal wording retained; no individual approval inferred | BLOCKED_ARCHITECTURE | BLOCKED_ARCHITECTURE | Pending |
| OC-IMP-012 | Original proposal wording retained; no individual approval inferred | BLOCKED_ARCHITECTURE | BLOCKED_ARCHITECTURE | Pending |
| OC-IMP-013 | Original proposal wording retained; no individual approval inferred | BLOCKED_ARCHITECTURE | BLOCKED_ARCHITECTURE | Pending |
| OC-IMP-014 | Original proposal wording retained; no individual approval inferred | BLOCKED_ARCHITECTURE | BLOCKED_ARCHITECTURE | Pending |
| OC-IMP-015 | Original proposal wording retained; no individual approval inferred | BLOCKED_ARCHITECTURE | BLOCKED_ARCHITECTURE | Pending |
| OC-IMP-016 | Original proposal wording retained; no individual approval inferred | BLOCKED_ARCHITECTURE | BLOCKED_ARCHITECTURE | Pending |
| OC-IMP-017 | Original proposal wording retained; no individual approval inferred | SUPERSEDED | SUPERSEDED | Pending |
| OC-IMP-018 | Original proposal wording retained; no individual approval inferred | BLOCKED_ARCHITECTURE | BLOCKED_ARCHITECTURE | Pending |
| IMP-001 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-002 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-003 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-004 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-005 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-006 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-007 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-008 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-009 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-010 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-011 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-012 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-013 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-014 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-015 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-016 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-017 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-018 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-019 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-020 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-021 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-022 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-023 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-024 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-025 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-026 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-027 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-028 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-029 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-030 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-031 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-032 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-033 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-034 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-035 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-036 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-037 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-038 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-039 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-040 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-041 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-042 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-043 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-044 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-045 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-046 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-047 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-048 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-049 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-050 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-051 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-052 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-053 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-054 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-055 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-056 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-057 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-058 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-059 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-060 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-061 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
| IMP-062 | Original authoritative definition unavailable | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Pending |
