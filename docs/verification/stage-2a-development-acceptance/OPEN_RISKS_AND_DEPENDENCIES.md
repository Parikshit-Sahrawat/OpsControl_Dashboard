# Ordered risks, accountable roles and bounded next work

| Priority | Requirement(s) | Blocker / dependency | Accountable role / bounded closure |
|---|---|---|---|
| P0 | TEL-03, TEL-01/02 | CHK-001 loss; CHK-002 rollback | Runtime engineer + independent verifier: supported upstream candidate, approved N1–N4 cuts and receipt reconciliation; no version transition here |
| P0 | PLT-03 | Image vulnerabilities, final identities, licensing/NOTICE, independent review | Security + release + legal/data owner: scoped exact-image closure and explicit signoffs, no waiver |
| P0 development | SET-02 | Approved settings behavior not implemented | Product/security owner approves safe fields and audit contract before bounded API/UI implementation |
| P0 governance | IMP-001–062, OC-IMP-001–018, TEL-04, OPS-02 | Original definitions/individual approvals/CA/SLO policies missing | Project owner recovers source or explicitly disposes scope; no inferred task authorization |
| P1 | RM-02/03, UI-005–009/012/013/015/020/021/023 | Incomplete workflows and item-level visual evidence | UX/engineering + owner: reproduce each scoped case, attach precise evidence, then fix only confirmed defects |
| P1 | DP-01/02, CMP-01, API-01, TEL-01 | Genuine-provider evidence | Provider owner + independent verifier: approved installed-build fixture and read-only target authorization |
| P1 | OPS-01, TOP-01, OPS-02/04 | Retired integrations versus requested capability; correlation/SLO/coverage completeness | Product/operations owner resolves scope and evidence semantics before implementation |
| P1 | PLT-01/02/04 | DR, persistent Stage B pilot and representative capacity | Platform owner: approved isolated rehearsal/benchmark; no live UAT action in this review |

Tenant isolation and historical migration preservation have current passing controlled evidence; they are mandatory regression gates, not newly asserted open defects. Historical red CI or fixed hydration is not reopened. Physical in-flight worker draining, large-fleet scheduling performance and older unidentifiable exploratory Docker volumes remain limitations of the reused removal evidence. The pre-existing EKS auxiliary raw ledger has a serialization defect; canonical HTTP/acceptance JSON is valid. No generic telemetry label is removed as if it were an operational Kubernetes adapter.

Historical 42-sprint authority remains incomplete: exact original detailed Sprint11–42 approvals and IMP definitions are not recovered. The conditional roadmap is not approved scope; fixed-percentage development coverage and shared-VM/Kubernetes suggestions are superseded. Measure coverage, preserve historical measurements, retain mandatory behavioral/security/migration/tenant/CI checks. Full ENG-001 authority remains an owner recovery item.

Terminology/authority conflict: the Issue42/canonical four-phase baseline and `docs/sdlc/05-ROADMAP.md` multi-phase engineering outline use different phase granularity. This review does not silently redefine either or equate Stage3 authorization with a roadmap phase number. Owner must identify the approved Stage3 entry scope. Only the explicitly removed cluster workstream was corrected.
