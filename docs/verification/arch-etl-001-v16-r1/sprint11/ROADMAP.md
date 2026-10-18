# Corrected conditional Sprint 12–42 roadmap

**Planning status: NOT APPROVED FOR IMPLEMENTATION.** Sprint 11 ended DELIVERED_WITH_SOURCE_BLOCKERS. The detailed original roadmap and all 62 original improvement definitions remain unavailable. This revision preserves the owner's 42-sprint planning framework and [Sprint 10's five phases](../sprint10/ROADMAP.md), then adds exact register references, decision blockers and real-infrastructure gates to remaining sprints. It does not rewrite historical sprints or promise certification by Sprint 42. The eight named IMP references below are title-only, and their original requirements remain SOURCE_NOT_RECOVERED.

Every estimate is **2–3.5 hours of active Codex work, under the five-hour checkpoint ceiling**. Infrastructure provisioning, human decisions, independent witnessing and corrective follow-up are additional unknown effort. Do not compress acceptance or treat a calendar slot as authorization. Global exclusions: workload launch/restart/repair/cancel/rerun, implicit grants, identity duplication, legal-hold bypass, undocumented architecture changes, unapproved production actions and broad refactoring. Later sprints require explicit owner authorization.

Priority dependency order: deployment ownership and customer sharing (S12) → preservation/trust (S13–S16) → telemetry continuity (S17–S20) → native lifecycle/compatibility (S21–S26) → source-gated graph/SLO/intelligence (S27–S33) → recovery/scale/adoption (S34–S42). A blocked prerequisite postpones its sprint; numbering never waives an evidence gate.

## Sprint 12

- Phase: Foundation and architecture validation.
- Objective: Validate one deployment trust model and shared-customer threat cases.
- In-scope modules: Security/scope/shared attribution.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: Sprint 11 source blockers; controlling architecture remains available; named deployment owner.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: HIGH; Security and tenancy architecture.
- Deliverables: Trust-zone and attribution matrix.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Explicit unauthorized routes/IDs denied; sharing alternatives approved.
- Open decisions: Single provider versus independent provider tenants.
- Risk level: HIGH — Security and tenancy architecture.
- Exact references: P0-03, P0-06; AUD-06; NEW-03; GOV-03/GOV-04/GOV-06.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: NO for disposable fixture; YES for target deployment approval.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 13

- Phase: Foundation and architecture validation.
- Objective: Specify preservation and recovery baseline with one restore fixture.
- In-scope modules: Backup/migrations/legal holds.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: Sprint 11 source blockers; controlling architecture remains available; disposable database.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: HIGH; Data preservation and recovery.
- Deliverables: Populated backup/restore fingerprint evidence and proposed RTO/RPO.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Protected records, grants and memberships survive restore; no unsafe downgrade.
- Open decisions: Backup location, encryption and RTO/RPO owner.
- Risk level: HIGH — Data preservation and recovery.
- Exact references: P0-04; NEW-11; AUD-08; GOV-07.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: NO for disposable preservation fixture; YES for target DR.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 14

- Phase: Foundation and architecture validation.
- Objective: Prepare exact-build Pentaho acceptance and execute one approved case slice.
- In-scope modules: Pentaho read-only adapters/evidence.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: S12–S13 plus Sprint 11 source blockers; separately approved real installation and witness.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: HIGH; Native proof/identity; blocked without environment.
- Deliverables: Build/method matrix and bounded RT evidence slice.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Only witnessed cases marked passed; all others remain NOT RUN; no ETL workload invocation by OpsControl.
- Open decisions: Credentials, witness, build and which existing execution evidence can be observed.
- Risk level: HIGH — Native proof/identity; blocked without environment.
- Exact references: P0-01; AUD-08; GOV-05.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: YES — approved real Pentaho installation and witness.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: For actual RT slice, capture exact build, method, native evidence, witness and pass/fail for each case; untouched RT cases stay NOT RUN.

## Sprint 15

- Phase: Secure telemetry collection.
- Objective: Exercise one agent identity/certificate lifecycle slice.
- In-scope modules: Enrollment/rotation/TLS.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: S12 trust; test issuer.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: HIGH; Identity/trust boundary.
- Deliverables: Credential/expiry/revocation evidence and issuer decision.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Expired/revoked identities denied; audited recovery preserves identity.
- Open decisions: Issuer/CA owner and certificate versus token responsibilities.
- Risk level: HIGH — Identity/trust boundary.
- Exact references: P0-05; NEW-02; GOV-06.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: NO for test CA; YES for target issuer acceptance.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 16

- Phase: Secure telemetry collection.
- Objective: Validate one private route and rotation overlap.
- In-scope modules: Agent TLS/network controls.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: S12, S15; isolated network.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: HIGH; Network and certificate security.
- Deliverables: Allowed/denied route and CA overlap evidence.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: No unauthorized network path; continuity accounted during rotation.
- Open decisions: Outbound-only versus private route topology.
- Risk level: HIGH — Network and certificate security.
- Exact references: P0-05, P0-06; NEW-02, NEW-03; GOV-06.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: YES for representative private/hybrid network acceptance.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 17

- Phase: Secure telemetry collection.
- Objective: Measure one bounded ingest/backpressure workload.
- In-scope modules: OTLP/API/agent buffer/diagnostics.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: S15–S16; controlled TLS lab.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: MEDIUM; Bounded ingest experiment.
- Deliverables: Dataset, queue/disk measurements and loss accounting.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Accepted/rejected/dropped IDs reconciled; memory/disk bounds and failures reported.
- Open decisions: Buffer limit and backpressure policy.
- Risk level: MEDIUM — Bounded ingest experiment.
- Exact references: P0-02; NEW-04, NEW-10; AUD-05; GOV-06.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: NO for bounded TLS lab; YES for target continuity.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 18

- Phase: Secure telemetry collection.
- Objective: Specify service completeness, blind spots and clock-skew semantics.
- In-scope modules: Coverage/schedules/telemetry timestamps.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: S11 recovered definitions; S17 signals.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: HIGH; Evidence consistency and clocks.
- Deliverables: Completeness/skew contract and deterministic fixture.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Missing/stale/skew cases stay UNKNOWN/INCOMPLETE; no fabricated NO_RUN/health.
- Open decisions: Service ownership, skew tolerances and expected signals.
- Risk level: HIGH — Evidence consistency and clocks.
- Exact references: P0-02; NEW-01, NEW-06, NEW-07; AUD-06; GOV-04/GOV-08.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: NO for deterministic fixture; YES for target clock/coverage policy.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 19

- Phase: Secure telemetry collection.
- Objective: Test one disconnect/restart durable-delivery and replay slice.
- In-scope modules: Agent export/source fences/replay.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: S17–S18; approved replay boundaries.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: HIGH; Concurrency, fences and recovery.
- Deliverables: Numbered-signal restart and idempotency evidence.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: No double projection; held evidence remains held; receipts account for continuity.
- Open decisions: Queue retention and independent replay approval.
- Risk level: HIGH — Concurrency, fences and recovery.
- Exact references: P0-02; NEW-04; GOV-06.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: NO for controlled restart; YES for target resilience.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 20

- Phase: Secure telemetry collection.
- Objective: Validate one synthetic path and notification delivery failure window.
- In-scope modules: API probes/outbox/provider sandbox.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: S12 routing authority; S17 diagnostics.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: MEDIUM; Bounded controlled transport; security review required.
- Deliverables: Synthetic failure/recovery and delivery crash-window evidence.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Synthetic health labeled; wrong-customer routing denied; duplicate limits explicit.
- Open decisions: Provider idempotency and escalation owner.
- Risk level: MEDIUM — Bounded controlled transport; security review required.
- Exact references: P0-02, P1-07; NEW-05; GOV-04.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: NO for synthetic lab; YES for provider routing acceptance.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 21

- Phase: Secure telemetry collection.
- Objective: Verify one native agent package canary and rollback.
- In-scope modules: Agent packaging/config revision.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: S15 identity; exact OS/runtime version.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: MEDIUM; Single platform canary only.
- Deliverables: Native host install/upgrade/failure/rollback evidence.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Identity/checkpoints preserved; invalid configuration not applied.
- Open decisions: Windows or Linux first; maintenance owner.
- Risk level: MEDIUM — Single platform canary only.
- Exact references: P1-06; NEW-08; GOV-06.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: YES for native agent/OS package acceptance.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 22

- Phase: Multi-platform observability.
- Objective: Establish one non-Pentaho platform/build compatibility entry.
- In-scope modules: Adapter/capability registry.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: Approved sandbox and build; S11 scope.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: MEDIUM; One platform/build/method.
- Deliverables: Exact build/method native evidence entry.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Documented versus runtime-verified support distinct; existing adapters retained.
- Open decisions: Platform choice and read-only account.
- Risk level: MEDIUM — One platform/build/method.
- Exact references: P1-08; NEW-13; GOV-05.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: YES for selected provider/build acceptance.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 23

- Phase: Multi-platform observability.
- Objective: Validate one private-cloud or VMware compute integration slice.
- In-scope modules: Canonical resources/collectors.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: S12 private model; approved installation.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: MEDIUM; No invented integration contract.
- Deliverables: Native identity/collection/outage evidence.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: No name-derived identity; native resource subtype and customer ownership preserved.
- Open decisions: Verified provider contract and target OS.
- Risk level: MEDIUM — No invented integration contract.
- Exact references: P1-08; NEW-03, NEW-13; GOV-03/GOV-05.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: YES for VMware/private-cloud native acceptance.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 24

- Phase: Multi-platform observability.
- Objective: Continue one approved Pentaho installed-build acceptance slice.
- In-scope modules: Pentaho CLI/Server/Carte contract selected.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: S14 environment; independent witness.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: HIGH; Canonical native identity and proof.
- Deliverables: Case-by-case native evidence and unresolved compatibility ledger.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Only actually witnessed cases leave NOT RUN; incomplete twenty-case set blocks certification.
- Open decisions: Exact method/build and remaining cases.
- Risk level: HIGH — Canonical native identity and proof.
- Exact references: P0-01, P1-08; NEW-13; GOV-05.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: YES — exact Pentaho installed build and witness.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: For actual RT slice, capture exact build, method, native evidence, witness and pass/fail; do not infer remaining cases.

## Sprint 25

- Phase: Multi-platform observability.
- Objective: Validate one AWS/Azure/cloud-native platform slice.
- In-scope modules: Existing Glue/ADF/cloud scopes.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: Approved sandbox account/region and S16 routes.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: MEDIUM; One sandbox; no blanket cloud certification.
- Deliverables: Native identities/permissions/failure evidence.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Cross-account/subscription denial and native result evidence.
- Open decisions: AWS versus Azure and tested regional capability.
- Risk level: MEDIUM — One sandbox; no blanket cloud certification.
- Exact references: P1-08; NEW-13; GOV-05.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: YES for chosen AWS/Azure sandbox account.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 26

- Phase: Multi-platform observability.
- Objective: Validate one container/API/hybrid service slice and remaining compatibility plan.
- In-scope modules: Kubernetes/API/OTLP contracts.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: S12 attribution; approved cluster/service.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: HIGH; Ephemeral identity and tenancy.
- Deliverables: Namespace/service identity and outage evidence; remaining platform backlog.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: No inventory-to-runtime capability inference; record eight non-Pentaho platforms individually.
- Open decisions: In-cluster least privilege and remaining acceptance environments.
- Risk level: HIGH — Ephemeral identity and tenancy.
- Exact references: P1-08; NEW-13; GOV-03/GOV-05.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: YES for chosen Kubernetes/API target platform.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 27

- Phase: Topology, incidents and service intelligence.
- Objective: Reconcile graph authorization and one shared-node policy increment.
- In-scope modules: ResourceDependency/scope.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: Recovered graph definitions; S12 shared model.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: HIGH; Graph authorization.
- Deliverables: Policy mapping and negative graph fixture.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: No cross-customer edge or derived exposure; existing composite FKs preserved.
- Open decisions: Original graph policy requirements.
- Risk level: HIGH — Graph authorization.
- Exact references: P0-03, P1-04; IMP-055 (title-only/source blocked); AUD-02; GOV-04/GOV-08.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: NO for negative scoped graph fixtures; YES for deployed sharing policy.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 28

- Phase: Topology, incidents and service intelligence.
- Objective: Define and verify one historical topology snapshot contract.
- In-scope modules: Dependency temporal history.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: S27; recovered snapshot definition.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: HIGH; Temporal consistency.
- Deliverables: As-of reproducibility fixture and implementation proposal if needed.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Retired edges reconstruct correctly; immutable references and scope preserved.
- Open decisions: Snapshot versus interval projection and retention.
- Risk level: HIGH — Temporal consistency.
- Exact references: P1-04; IMP-056 (title-only/source blocked); GOV-08.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: NO for controlled historical graph fixture.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 29

- Phase: Topology, incidents and service intelligence.
- Objective: Bound graph traversal and define one freshness/expiry increment.
- In-scope modules: Dependency APIs/queries.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: S27–S28; original integrity/freshness definitions.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: HIGH; Concurrency and graph integrity.
- Deliverables: Query-count experiment and cycle/freshness tests.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Concurrent cycle attempts fail; traversal bound explicit; stale edges never trusted silently.
- Open decisions: Expiry authority and safe query/pagination contract.
- Risk level: HIGH — Concurrency and graph integrity.
- Exact references: P1-04; IMP-057, IMP-058 (title-only/source blocked); AUD-02; GOV-08.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: NO for bounded/concurrent graph fixture.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 30

- Phase: Topology, incidents and service intelligence.
- Objective: Recover and specify one SLO measurement/provenance increment.
- In-scope modules: Telemetry/reporting/SLO contract.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: Recovered SLO definition; S18 completeness.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: HIGH; Measurement correctness.
- Deliverables: Formula/denominator/window fixture and provenance design.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Reproduce one approved metric from evidence; missing data treatment explicit.
- Open decisions: SLO policy owner and formula approval.
- Risk level: HIGH — Measurement correctness.
- Exact references: P1-05; IMP-059 (title-only/source blocked); AUD-07; NEW-01; GOV-08.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: NO for deterministic math fixture; YES for production SLO claims.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 31

- Phase: Topology, incidents and service intelligence.
- Objective: Define one versioned SLO policy and evidence review linkage.
- In-scope modules: Policy/evidence review.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: S30; original policy definition.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: HIGH; Evidence and version consistency.
- Deliverables: Policy revision/recompute and stale-decision fixture.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Historical result references exact evidence/policy; no free-form native outcome override.
- Open decisions: Prospective versus historical recalculation.
- Risk level: HIGH — Evidence and version consistency.
- Exact references: P1-05; IMP-060 (title-only/source blocked); AUD-07; GOV-08.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: NO for policy-revision fixture; YES for production SLO claims.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 32

- Phase: Topology, incidents and service intelligence.
- Objective: Validate customer-safe incident ownership, escalation and recovery slice.
- In-scope modules: Native incidents/notifications.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: S27; original correlation definition; S20 delivery.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: HIGH; Incident recovery and disclosure.
- Deliverables: Customer-safe root/recovery/routing scenario.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Original failed execution stays failed; dependencies/window required; no automatic historical reopen.
- Open decisions: Service owner and common-root authority.
- Risk level: HIGH — Incident recovery and disclosure.
- Exact references: P1-07; IMP-061 (title-only/source blocked); NEW-12; GOV-04/GOV-08.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: NO for customer-safe fixture; YES for provider routing/recovery claim.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 33

- Phase: Topology, incidents and service intelligence.
- Objective: Evaluate one permission-safe derived/change analytics increment.
- In-scope modules: Reports/audit/correlation.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: S27–S32; recovered analytics definition.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: HIGH; Derived data security.
- Deliverables: Authorized-input/aggregate inference tests and change attribution proposal.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: No unauthorized aggregate/history disclosure; correlation labeled; no new identity model.
- Open decisions: Aggregation leakage threshold and change-event authority.
- Risk level: HIGH — Derived data security.
- Exact references: P0-03; IMP-062 (title-only/source blocked); NEW-14; GOV-04/GOV-08.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: NO for derived-disclosure fixture; YES for target disclosure review.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 34

- Phase: Enterprise resilience, scalability and controlled adoption.
- Objective: Run one populated disaster-recovery drill.
- In-scope modules: Database/evidence/agent checkpoints.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: S13 approved recovery policy; isolated restore target.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: HIGH; Recovery and migration integrity.
- Deliverables: Timed recovery/fingerprint report.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Compare achieved RTO/RPO; holds/grants/hashes/evidence preserved.
- Open decisions: Recovery-site availability and failover owner.
- Risk level: HIGH — Recovery and migration integrity.
- Exact references: P0-04; NEW-11; AUD-08; GOV-07.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: YES for representative isolated recovery site.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Time populated restoration into an isolated site; fingerprint preserved grants, identities, holds, evidence and checkpoints.

## Sprint 35

- Phase: Enterprise resilience, scalability and controlled adoption.
- Objective: Measure bounded fleet RBAC/read/revocation contention.
- In-scope modules: Resolver/transaction_authority/inventory.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: S12 trust; approved dataset sizes.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: HIGH; Authorization and concurrency.
- Deliverables: Latency/query/lock report with concurrent negatives.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Record p50/p95/p99/errors and lock waits; revocation denies authoritative decisions.
- Open decisions: Measured target capacity and allowed contention.
- Risk level: HIGH — Authorization and concurrency.
- Exact references: P1-01; AUD-03, AUD-04; GOV-09.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: NO for bounded load; YES for target capacity certification.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Report dataset, concurrency, duration, p50/p95/p99, failures, query/lock counts and denied revocation races.

## Sprint 36

- Phase: Enterprise resilience, scalability and controlled adoption.
- Objective: Migrate one external-client family to explicit scope.
- In-scope modules: Owned API clients/docs.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: Client inventory and owners; S35.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: MEDIUM; Bounded client compatibility.
- Deliverables: Versioned compatibility matrix and owned-client tests.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Omitted/wildcard denied; authorized IDs/ALL explicit; partner state not overstated.
- Open decisions: Third-party owner availability.
- Risk level: MEDIUM — Bounded client compatibility.
- Exact references: P1-02; GOV-09.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: NO for owned-client harness; YES for third-party adoption.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 37

- Phase: Enterprise resilience, scalability and controlled adoption.
- Objective: Fix verified pagination bottleneck in one API contract.
- In-scope modules: Resource dependency details or measured archive query.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: S29/S35; approved backward-compatible contract.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: MEDIUM; One contract only; security review.
- Deliverables: Bounded scoped endpoint and relevant frontend increment.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Complete static traversal; no IDOR; stable order and mutation semantics documented.
- Open decisions: Offset versus cursor after query-plan evidence.
- Risk level: MEDIUM — One contract only; security review.
- Exact references: P1-03; AUD-01, AUD-03; GOV-09.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: NO for disposable large inventory.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Traverse static scoped pages without omissions or cross-customer IDs; measure deep page query plan and mutated-view semantics.

## Sprint 38

- Phase: Enterprise resilience, scalability and controlled adoption.
- Objective: Extend canary orchestration to one additional agent/platform version.
- In-scope modules: Agent lifecycle/compatibility registry.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: S21 native canary; S22 compatibility.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: MEDIUM; No unrestricted remote workload execution.
- Deliverables: One-version staged rollout/rollback evidence.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Checkpoint/identity preserved; unsupported combinations disabled.
- Open decisions: Rollout authority and compatibility set.
- Risk level: MEDIUM — No unrestricted remote workload execution.
- Exact references: P1-06; NEW-08; GOV-06.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: YES for native package/OS canary.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 39

- Phase: Enterprise resilience, scalability and controlled adoption.
- Objective: Measure and govern one cardinality/residency/retention slice.
- In-scope modules: Telemetry storage/holds/redaction.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: S11 policy recovery; privacy/retention owners.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: HIGH; Data protection and preservation.
- Deliverables: Cost/growth report and bounded policy proposal.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: Held evidence survives; sensitive fields/regions governed; approved limits measured.
- Open decisions: Data residency, deletion and archive attestation.
- Risk level: HIGH — Data protection and preservation.
- Exact references: P2-02; NEW-09, NEW-16; GOV-07/GOV-09.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: NO for measured fixture; YES for production residency/economics.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 40

- Phase: Enterprise resilience, scalability and controlled adoption.
- Objective: Run one operator shift/UAT/accessibility drill.
- In-scope modules: Six pages/Access/Resource navigation.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: Verified scoped contracts; representative operators.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: MEDIUM; One controlled workflow set.
- Deliverables: Keyboard/mobile/shift evidence and bounded defect list.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: No stale customer data; decisions and handover understood; legacy navigation preserved.
- Open decisions: Human operators and operational acceptance owner.
- Risk level: MEDIUM — One controlled workflow set.
- Exact references: P2-01; GOV-10.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: YES for representative human operator UAT.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 41

- Phase: Enterprise resilience, scalability and controlled adoption.
- Objective: Assemble evidence-based platform readiness review.
- In-scope modules: Self-observability/compatibility/gap ledger.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: Prior slices; independent reviewers.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: HIGH; Production-readiness governance.
- Deliverables: Gate matrix and one alert/health blind-spot experiment.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: No unverified platform enabled; queue/worker/data-path health distinct; all P0 evidence reviewed.
- Open decisions: Independent approval and unresolved blockers.
- Risk level: HIGH — Production-readiness governance.
- Exact references: P0-01–P0-06, P1-01–P1-08; NEW-10, NEW-15; AUD-05, AUD-08; GOV-10.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: YES for independent target evidence.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Sprint 42

- Phase: Enterprise resilience, scalability and controlled adoption.
- Objective: Make controlled-adoption go/no-go recommendation.
- In-scope modules: Readiness/release governance.
- Out-of-scope work: global exclusions; other platform/build/module increments and broad refactoring.
- Prerequisites: All mandatory gates and owner decisions.
- Estimated Codex effort: 2–3.5 hours; below-five-hour checkpoint rule applies.
- Model recommendation: HIGH; Recommendation only; deployment separately authorized.
- Deliverables: Signed evidence index or explicit NO-GO checkpoint.
- Test requirements: requirement-specific allowed/denied, preservation and failure cases on owned fixtures; real infrastructure/witness where the readiness register requires it; documentation/link checks for governance-only increments.
- Exit criteria: No production claim with open P0; independent Pentaho and security evidence required.
- Open decisions: Release authority, rollout envelope and rollback ownership.
- Risk level: HIGH — Recommendation only; deployment separately authorized.

- Exact references: P0-01–P0-06, P1-01–P1-08, P2-01–P2-02; NEW-15; GOV-10.
- Blocking decisions: the GOV IDs in exact references; [governance register](ARCHITECTURE_GOVERNANCE.md) remains pending where marked.
- Real infrastructure needed: YES for independent production go/no-go.
- Independent evidence required: documented code/test outputs alone do not certify target operation; have an independent witness for installed-build, network, DR, security and production claims when applicable.
- Remaining risk and follow-up: source-gated approved requirements cannot be closed here; retain unsatisfied cases as [post-42 extensions](#conditional-post-42-extensions) or separately authorized bounded increments.
- Slice-specific tests: Verify the listed exit criteria with focused owned fixtures; retain negative authorization, preservation and failure-path evidence relevant to this slice.

## Coverage and sequencing

Phase 1 spans S11–S14; secure telemetry S15–S21; multi-platform S22–S26; topology/service intelligence S27–S33; enterprise resilience/adoption S34–S42. Dependencies may block later slots; chronological placement never waives a gate. P0 trust/identity/recovery planning begins before scale or derived analytics. S14/S24 are bounded runtime slices, not a substitute for completing all twenty independent cases. S22–S26 record all nine platform families in a compatibility ledger and accept one exact build/method per slice; any remaining platforms require follow-up increments before claiming certification.

Compared with historical release roadmaps, this adds explicit source-recovery, customer-sharing, independent runtime, preservation and no-go checkpoints. No exact original Sprint 11–42 change comparison is possible without its source. See [governance decisions](ARCHITECTURE_GOVERNANCE.md) for blocking decisions and [readiness](PRODUCTION_READINESS.md) for complete gap assignments.
## Conditional post-42 extensions

**Unapproved proposal.** The twenty installed-build Pentaho cases, nine platform families, Windows/Linux native agent/service lifecycle, real target DR/network/PKI and human adoption may require additional short increments after Sprint 42. There is no supported estimate that they will all fit before then. Any original approved IMP definition recovered later that cannot fit gets a separately reviewed bounded extension, preserving its exact ID and acceptance wording; no renumbering or silent dropping. A NO-GO at S42 is an acceptable evidence-based result.

Cross-reference all sixteen [readiness gaps](PRODUCTION_READINESS.md), sixteen [NEW candidates](NEW_IMPROVEMENT_RECONCILIATION.md), eight [audit findings](AUDIT_FINDINGS.md) and the 62-entry [source register](IMPROVEMENT_REGISTER.md). Source recovery and owner approval precede definitive duplicate judgments or architecture changes. Pentaho RT-001–RT-020 remain NOT RUN until separately authorized real-runtime acceptance is independently witnessed.
