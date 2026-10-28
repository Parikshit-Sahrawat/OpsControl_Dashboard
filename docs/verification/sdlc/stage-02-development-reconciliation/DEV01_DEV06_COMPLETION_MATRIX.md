# Requirement-level reconciliation

Current source baseline `09a578f70282c7889a515c332c948f1940ae6719`. Historical verified labels are preserved separately. Current IMPLEMENTED_UNVERIFIED means exact-current per-requirement execution has not been established by this documentation audit; it does not erase historic passes. Proposed requirements and missing originals are counted separately. No completion percentages. SET-02 requires renewed source assessment; historical absence is not assumed current. K8S-01 now has source/models and migration0038, contradicting the historical “not located” finding; qualification/approval chain still needs review.

Canonical ownership is retained: K8S/TOP DEV04, OPS DEV05 despite audit category names. API/model/migration/test dependencies and historical evidence are retained verbatim per requirement in [requirements.json](requirements.json), traced to [main traceability](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/09a578f70282c7889a515c332c948f1940ae6719/docs/verification/issue-47/TRACEABILITY.md).

| ID | Owner | Historical | Current assessment | Remaining acceptance prerequisite |
|---|---|---|---|---|
| RM-01 | DEV-01 | IMPLEMENTED_VERIFIED | IMPLEMENTED_UNVERIFIED | Retain negative cross-entity tests; independent UAT |
| RM-02 | DEV-01 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Recheck end-to-end draft/activation and avoid duplicate controls |
| RM-03 | DEV-01 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Target reproduced 390/768/1366 issues |
| RM-04 | DEV-02 | IMPLEMENTED_VERIFIED | IMPLEMENTED_UNVERIFIED | Verify method attribution and real agent separately |
| RM-05 | DEV-02 | IMPLEMENTED_VERIFIED | IMPLEMENTED_UNVERIFIED | Retain generation/fencing regression under concurrency |
| AM-01 | DEV-01 | IMPLEMENTED_VERIFIED | IMPLEMENTED_UNVERIFIED | Independent UAT of all authorized actions |
| AM-02 | DEV-01 | IMPLEMENTED_UNVERIFIED | IMPLEMENTED_UNVERIFIED | Reproduce UAT Cycle 2 findings before UI correction |
| AM-03 | DEV-01 | IMPLEMENTED_UNVERIFIED | IMPLEMENTED_UNVERIFIED | Confirm actionable route and write permissions |
| SET-01 | DEV-01 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Map existing profile contracts; implement only missing approved UI/API |
| SET-02 | DEV-06 | NOT_IMPLEMENTED | NOT_ASSESSED | Define safe editable keys; keep resource-specific settings in RM |
| HELP-01 | DEV-01 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Inventory existing help content and scoped SOP presentation |
| TEL-01 | DEV-02 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Bound installed-build fixture/packaging checks; real OS acceptance later |
| TEL-02 | DEV-02 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Verify each signal path and attribution |
| TEL-03 | DEV-02 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Define approved delivery contract before additions |
| TEL-04 | DEV-06 | BLOCKED_ARCHITECTURE | BLOCKED_ARCHITECTURE | Provider CA, network and clock policies; controlled implementation later |
| CMP-01 | DEV-03 | IMPLEMENTED_VERIFIED | IMPLEMENTED_UNVERIFIED | Preserve source/health distinction; real-provider acceptance later |
| CMP-02 | DEV-03 | IMPLEMENTED_VERIFIED | IMPLEMENTED_UNVERIFIED | Retain FK and forged-ID negatives |
| DP-01 | DEV-03 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Native child evidence and RT-001–020 remain open |
| DP-02 | DEV-03 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Exact build/method capability evidence, no invented support |
| API-01 | DEV-03 | IMPLEMENTED_VERIFIED | IMPLEMENTED_UNVERIFIED | Confirm actual target freshness/authorization; real-network acceptance later |
| K8S-01 | DEV-04 | BLOCKED_ARCHITECTURE | IMPLEMENTED_UNVERIFIED | Approve additive identity/association/attribution design |
| K8S-02 | DEV-04 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Verify provider-native data and private API in approved lab |
| TOP-01 | DEV-04 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Benchmark graph and specify version/expiry policy |
| OPS-01 | DEV-05 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Delivery and escalation contract/negative tests |
| OPS-02 | DEV-05 | BLOCKED_ARCHITECTURE | BLOCKED_ARCHITECTURE | Recover source or approve precise SLO contract |
| OPS-03 | DEV-05 | IMPLEMENTED_VERIFIED | IMPLEMENTED_UNVERIFIED | Independent downstream/recovery UAT; no automatic certification |
| OPS-04 | DEV-05 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Inject outages; define completeness projections |
| PLT-01 | DEV-06 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Controlled preservation recheck; real WAL/PITR/DR later |
| PLT-02 | DEV-06 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Isolated runner rehearsal subject to approval; no auto-deploy |
| PLT-03 | DEV-06 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Decide data policy before residency implementation |
| PLT-04 | DEV-06 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Measure representative workload before optimization |
| UI-001 | RM-03 / 01 | IMPLEMENTED_VERIFIED | IMPLEMENTED_UNVERIFIED | Candidate-SHA keyboard/mobile/persistence UAT |
| UI-002 | RM-02 / 01 | IMPLEMENTED_VERIFIED | IMPLEMENTED_UNVERIFIED | Check refresh/deep-link |
| UI-003 | RM-02 / 01 | IMPLEMENTED_VERIFIED | IMPLEMENTED_UNVERIFIED | Full Compute UAT |
| UI-004 | RM-02 / 01 | IMPLEMENTED_VERIFIED | IMPLEMENTED_UNVERIFIED | Mobile/desktop focus checks |
| UI-005 | RM-03 / 01 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Reproduce clipping at 390/768/1366 |
| UI-006 | RM-02 / 01 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | One primary action, validation per state |
| UI-007 | RM-02 / 01 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Reproduce historical Not Found with persisted draft |
| UI-008 | RM-04 / 02 | IMPLEMENTED_VERIFIED | IMPLEMENTED_UNVERIFIED | Multi-method UAT, real agent separate |
| UI-009 | RM-02 / 01 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Prove backend-confirmed actual readiness per target |
| UI-010 | RM-01/AM-01 / 01 | IMPLEMENTED_VERIFIED | IMPLEMENTED_UNVERIFIED | Preserve cross-entity negative UAT |
| UI-011 | RM-02/CMP-01/DP-01/API-01 / 01 | IMPLEMENTED_VERIFIED | IMPLEMENTED_UNVERIFIED | Check no duplicate create in Operations |
| UI-012 | RM-03 / 01 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Responsive/theme/reduced-motion independent pass |
| UI-013 | DP-01 / 01 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Verify credentials remain references and layout |
| UI-014 | AM-01 / 01 | IMPLEMENTED_VERIFIED | IMPLEMENTED_UNVERIFIED | LIMIT/DENY form independent UAT |
| UI-015 | AM-01/03 / 01 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Employee→permission origin UX |
| UI-016 | OPS-04 / 01 | IMPLEMENTED_VERIFIED | IMPLEMENTED_UNVERIFIED | Actual outage vs valid zero state |
| UI-017 | CMP-01 / 03 | IMPLEMENTED_VERIFIED | IMPLEMENTED_UNVERIFIED | Real adapter acceptance separate |
| UI-018 | DP-01 / 03 | IMPLEMENTED_VERIFIED | IMPLEMENTED_UNVERIFIED | Readability/overflow independent UAT |
| UI-019 | API-01 / 03 | IMPLEMENTED_VERIFIED | IMPLEMENTED_UNVERIFIED | Real probe acceptance separate |
| UI-020 | OPS-01 / 05 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Labels only; no Alerts redesign |
| UI-021 | OPS-01 / 05 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Filtered totals/duplicates browser test |
| UI-022 | RM-02 / 01 | IMPLEMENTED_VERIFIED | IMPLEMENTED_UNVERIFIED | Deep-link/permissions UAT |
| UI-023 | RM-02/DP-01 / 01 | PARTIALLY_IMPLEMENTED | PARTIALLY_IMPLEMENTED | Step action/focus parity test |
| OC-IMP-001 | Preserve issue47 TRACEABILITY proposal mapping | PROPOSED_OWNER_REVIEW | BLOCKED_ARCHITECTURE | Obtain item-level approval; shared VM example superseded by exclusive VM ownership |
| OC-IMP-002 | Preserve issue47 TRACEABILITY proposal mapping | PROPOSED_OWNER_REVIEW | BLOCKED_ARCHITECTURE | Obtain item-level approval; shared VM example superseded by exclusive VM ownership |
| OC-IMP-003 | Preserve issue47 TRACEABILITY proposal mapping | PROPOSED_OWNER_REVIEW | BLOCKED_ARCHITECTURE | Obtain item-level approval; shared VM example superseded by exclusive VM ownership |
| OC-IMP-004 | Preserve issue47 TRACEABILITY proposal mapping | PROPOSED_OWNER_REVIEW | BLOCKED_ARCHITECTURE | Obtain item-level approval; shared VM example superseded by exclusive VM ownership |
| OC-IMP-005 | Preserve issue47 TRACEABILITY proposal mapping | PROPOSED_OWNER_REVIEW | BLOCKED_ARCHITECTURE | Obtain item-level approval; shared VM example superseded by exclusive VM ownership |
| OC-IMP-006 | Preserve issue47 TRACEABILITY proposal mapping | PROPOSED_OWNER_REVIEW | BLOCKED_ARCHITECTURE | Obtain item-level approval; shared VM example superseded by exclusive VM ownership |
| OC-IMP-007 | Preserve issue47 TRACEABILITY proposal mapping | PROPOSED_OWNER_REVIEW | BLOCKED_ARCHITECTURE | Obtain item-level approval; shared VM example superseded by exclusive VM ownership |
| OC-IMP-008 | Preserve issue47 TRACEABILITY proposal mapping | PROPOSED_OWNER_REVIEW | BLOCKED_ARCHITECTURE | Obtain item-level approval; shared VM example superseded by exclusive VM ownership |
| OC-IMP-009 | Preserve issue47 TRACEABILITY proposal mapping | PROPOSED_OWNER_REVIEW | BLOCKED_ARCHITECTURE | Obtain item-level approval; shared VM example superseded by exclusive VM ownership |
| OC-IMP-010 | Preserve issue47 TRACEABILITY proposal mapping | PROPOSED_OWNER_REVIEW | BLOCKED_ARCHITECTURE | Obtain item-level approval; shared VM example superseded by exclusive VM ownership |
| OC-IMP-011 | Preserve issue47 TRACEABILITY proposal mapping | PROPOSED_OWNER_REVIEW | BLOCKED_ARCHITECTURE | Obtain item-level approval; shared VM example superseded by exclusive VM ownership |
| OC-IMP-012 | Preserve issue47 TRACEABILITY proposal mapping | PROPOSED_OWNER_REVIEW | BLOCKED_ARCHITECTURE | Obtain item-level approval; shared VM example superseded by exclusive VM ownership |
| OC-IMP-013 | Preserve issue47 TRACEABILITY proposal mapping | PROPOSED_OWNER_REVIEW | BLOCKED_ARCHITECTURE | Obtain item-level approval; shared VM example superseded by exclusive VM ownership |
| OC-IMP-014 | Preserve issue47 TRACEABILITY proposal mapping | PROPOSED_OWNER_REVIEW | BLOCKED_ARCHITECTURE | Obtain item-level approval; shared VM example superseded by exclusive VM ownership |
| OC-IMP-015 | Preserve issue47 TRACEABILITY proposal mapping | PROPOSED_OWNER_REVIEW | BLOCKED_ARCHITECTURE | Obtain item-level approval; shared VM example superseded by exclusive VM ownership |
| OC-IMP-016 | Preserve issue47 TRACEABILITY proposal mapping | PROPOSED_OWNER_REVIEW | BLOCKED_ARCHITECTURE | Obtain item-level approval; shared VM example superseded by exclusive VM ownership |
| OC-IMP-017 | Preserve issue47 TRACEABILITY proposal mapping | PROPOSED_OWNER_REVIEW | BLOCKED_ARCHITECTURE | Obtain item-level approval; shared VM example superseded by exclusive VM ownership |
| OC-IMP-018 | Preserve issue47 TRACEABILITY proposal mapping | PROPOSED_OWNER_REVIEW | BLOCKED_ARCHITECTURE | Obtain item-level approval; shared VM example superseded by exclusive VM ownership |
| IMP-001 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-002 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-003 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-004 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-005 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-006 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-007 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-008 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-009 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-010 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-011 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-012 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-013 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-014 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-015 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-016 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-017 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-018 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-019 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-020 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-021 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-022 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-023 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-024 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-025 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-026 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-027 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-028 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-029 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-030 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-031 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-032 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-033 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-034 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-035 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-036 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-037 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-038 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-039 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-040 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-041 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-042 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-043 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-044 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-045 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-046 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-047 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-048 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-049 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-050 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-051 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-052 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-053 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-054 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-055 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-056 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-057 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-058 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-059 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-060 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-061 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
| IMP-062 | Unassigned: original source missing | SOURCE_NOT_RECOVERED | SOURCE_NOT_RECOVERED | Recover original wording/version/approval; do not infer scope from titles |
