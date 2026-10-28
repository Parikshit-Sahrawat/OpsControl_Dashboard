# OpsControl — Global UAT Register (cumulative)
Last reconciled: 2026-10-28. Governing principle: **no UAT finding closes on merge alone**.

This is the cumulative baseline for all future Resource Management and global dashboard UAT. Retain the original observations/screenshots and historical failure evidence; future implementation and acceptance updates must be append-only or explicitly audited. A component-level PASS does not automatically close end-to-end UX, security, or deployment findings.

## Resource Management — RM-DEF-001 through RM-DEF-035

| ID | Description / required outcome | Priority | Acceptance status |
|---|---|---|---|
| RM-DEF-001 | Redundant Resource Management navigation | P2 | OPEN / reassess after independent UAT |
| RM-DEF-002 | Organization description UX | P2 | OPEN / reassess after independent UAT |
| RM-DEF-003 | Inactive organization filtering | P1 | OPEN / reassess after independent UAT |
| RM-DEF-004 | Slow organization listing | P1 | OPEN / reassess after independent UAT |
| RM-DEF-005 | Browser-history crash | P1 | OPEN / reassess after independent UAT |
| RM-DEF-006 | Typography consistency A | P2 | OPEN / reassess after independent UAT |
| RM-DEF-007 | Typography consistency B | P2 | OPEN / reassess after independent UAT |
| RM-DEF-008 | Resource Name and Hostname identity separation | P1 | OPEN / reassess after independent UAT |
| RM-DEF-009 | Move service names to collector/monitoring context | P2 | OPEN / reassess after independent UAT |
| RM-DEF-010 | Move native host metrics to collector context | P2 | OPEN / reassess after independent UAT |
| RM-DEF-011 | Form validation and field constraints | P1 | OPEN / reassess after independent UAT |
| RM-DEF-012 | Dedicated Collector Setup workspace | P1 | OPEN / reassess after independent UAT |
| RM-DEF-013 | Automatic collector name | P2 | OPEN / reassess after independent UAT |
| RM-DEF-014 | Bottom Save Collector action | P2 | OPEN / reassess after independent UAT |
| RM-DEF-015 | Move Agent Health to Agent workspace | P2 | OPEN / reassess after independent UAT |
| RM-DEF-016 | Telemetry Health and NO_DATA semantics | P2 | OPEN / reassess after independent UAT |
| RM-DEF-017 | Simplify collection methods | P1 | OPEN / reassess after independent UAT |
| RM-DEF-018 | Simplify Host Monitoring | P1 | OPEN / reassess after independent UAT |
| RM-DEF-019 | Add Method UX | P1 | OPEN / reassess after independent UAT |
| RM-DEF-020 | Revision YAML validation/download | P1 | OPEN / reassess after independent UAT |
| RM-DEF-021 | Deployment history and rollback | P1 | OPEN / reassess after independent UAT |
| RM-DEF-022 | Actual Linux ZIP/Windows EXE delivery and installer UX | P1 | OPEN / reassess after independent UAT |
| RM-DEF-023 | Enrollment issuance and secure operator flow | P1 | OPEN / reassess after independent UAT |
| RM-DEF-024 | Agent connection + runtime proof | P1 | OPEN / reassess after independent UAT |
| RM-DEF-025 | Readiness vs CONFIGURED vs CONNECTED distinctions | P1 | OPEN / reassess after independent UAT |
| RM-DEF-026 | Compute Health generic error | P1 | OPEN / reassess after independent UAT |
| RM-DEF-027 | Version inheritance clarity | P2 | OPEN / reassess after independent UAT |
| RM-DEF-028 | Organization created but missing in inventory | P1 | OPEN / reassess after independent UAT |
| RM-DEF-029 | Remove false 10-step identity wizard; distinct 8-step onboarding | P1 | OPEN / reassess after independent UAT |
| RM-DEF-030 | Remove Compute Identity sidebar and expand form | P2 | OPEN / reassess after independent UAT |
| RM-DEF-031 | Move sequential, dependent onboarding actions into Collector Configuration; hide installation action after connected/configured | P1 | OPEN / reassess after independent UAT |
| RM-DEF-032 | Verify telemetry view closes after ~2 seconds | P1 | OPEN / reassess after independent UAT |
| RM-DEF-033 | Remove redundant Compute Activate monitoring action; preserve backend gates | P1 | OPEN / reassess after independent UAT |
| RM-DEF-034 | Remove standalone Event Parameters navigation; preserve data/API/history | P2 | OPEN / reassess after independent UAT |
| RM-DEF-035 | Compute Health Parameters shows Resource unavailable despite telemetry | P1 | OPEN / reassess after independent UAT |

**Observed acceptance evidence (not a blanket closure):** Linux ZIP staged and installed; Ubuntu agent v1.5.0 securely enrolled and CONNECTED; after host-method configuration revision 2, runtime RUNNING, deployment history revision 2 VERIFIED, metrics RECEIVING (13,607 at screenshot capture); logs/traces NO_DATA because revision 2 includes metrics only. Prior revision-1 deployment failures retained. RM-DEF-024 agent *connection* pass; full readiness/telemetry user journey remains under verification. RM-DEF-022 Windows native EXE artifact not yet provisioned. RM-DEF-028 organization inventory still empty even though organization was created and selectable. RM-DEF-032 transient telemetry verification, RM-DEF-033 redundant activation network error, RM-DEF-035 resource unavailable all reproduced in local UAT.

### Approved 8-step Compute/Collector journey

1. Create Compute Instance identity.
2. Download and install native agent (Linux verified ZIP; Windows actual EXE required).
3. Register agent securely with a simplified, operator-safe enrollment.
4. Verify authenticated connection and actionable runtime diagnostics.
5. Configure host monitoring and ETL collection methods/templates.
6. Validate and approve the revision.
7. Apply revision to agent and expose deployment history/rollback.
8. Verify actual telemetry, then expose readiness/activation only through appropriate authorized gates.

Distinguish identity saved, agent installed, registered, connected, runtime RUNNING, revision applied, telemetry received, and monitoring active. Never infer later states from earlier ones. Preserve rejected/missing method evidence. Preserve tenant isolation, credential secrecy, CHK-001/CHK-002 security blocks, and all UAT retention data.

## Global UI modernization — UI-001 through UI-010

| ID | Requirement | Priority | Acceptance status |
|---|---|---|---|
| UI-001 | Dark/light accessible themes | P1 | OPEN / design and UAT pending |
| UI-002 | KPI metrics layouts and health matrix | P1 | OPEN / design and UAT pending |
| UI-003 | Live Streaming / Historical Analysis switchable workspace | P1 | OPEN / design and UAT pending |
| UI-004 | Date picker, frequency chart, sortable dense audit table | P1 | OPEN / design and UAT pending |
| UI-005 | Collapsible, hover-expandable sidebar | P1 | OPEN / design and UAT pending |
| UI-006 | Hierarchical navigation and progressive disclosure | P1 | OPEN / design and UAT pending |
| UI-007 | Severity/release/version status badges | P2 | OPEN / design and UAT pending |
| UI-008 | High data density and responsive layouts | P1 | OPEN / design and UAT pending |
| UI-009 | Shared design system across monitoring domains | P1 | OPEN / design and UAT pending |
| UI-010 | Incremental pinned Tailwind CSS migration | P2 | OPEN / design and UAT pending |

Design direction: dark-first high-density NOC interface, accessible high-contrast light theme; time-series, bar/donut, gauge and availability matrix; sidebar collapsed icons with pinned/hover expansion; clear live vs historical investigations; progressive disclosure; avoid unnecessary redirects or navigation resets. Existing frontend is React 19 + Vite 7 with project CSS, **not** currently Tailwind; evaluate incremental Tailwind integration with existing regression gates.

## Cross-cutting retained registers

- **RM-SEC-001:** HAR/secret-token handling; no real bearer tokens or enrollment material in screenshots, logs or CI artifacts. OPEN acceptance.
- **RM-SCOPE-001:** Kubernetes removal boundary and unrelated workflows/UX scope. OPEN verification.
- **UAT-ENV-001..004:** persistent Ubuntu UAT Compose override, PostgreSQL durable volume, TLS trust/CA, agent host state, local checkout/permission drift, backups and clean refresh requirements. NEVER use `down -v`, wipe persistent volumes, reset agent identity or silently rewrite local user files.
- **Release safety:** existing PR #69 DEV-05.2A CHK-001 FAIL, CHK-002 BLOCKED, SECURITY BLOCKED, RELEASE NO-GO; no implicit waiver, binary swap, forced merge or qualification-by-green-CI.

## New UAT cycle after implementation PR merge

**First: Resource Management → Organizations.** Create/edit, inactive filters, inventory pagination and search, tenant boundaries, authorized-customer selector consistency, reload/history navigation, data persistence, and exact error states.

**Second: Resource Management → Compute Instances.** Create/edit identity, full-width form, validation, customer binding, agent enroll/diagnostics, collector sequential workflow, deployed revision 2 preservation, telemetry verification persistence, health-page routing, permissions and regression.

### Update protocol

For each item, record: reproduction steps, screenshot/evidence reference, affected revision, actual outcome, expected outcome, implementation PR/commit, test case, independent UAT decision and date. Statuses: OPEN, IN PROGRESS, BLOCKED, READY FOR UAT, PASS, FAIL. No statuses are implied by a checkmark on a different substep.
