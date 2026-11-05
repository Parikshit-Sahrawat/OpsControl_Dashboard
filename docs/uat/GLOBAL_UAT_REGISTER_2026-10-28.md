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

## RM-DEF-036 — P0 provisional: dashboard unresponsive during active metrics ingestion

- **Architecture clarification (2026-10-29): GLOBAL performance gate.** RM-DEF-036 applies to **all OpsControl modules and shared data-access paths**, not only Compute Health: Overview, Organizations, Resource Management, Compute Instances, ETL Jobs, VM Health, APIs, Active Incidents, Correlation, Collectors, and telemetry/history views. Every growing-data list and summary endpoint must avoid N+1 queries, unnecessary full-table scans, unbounded responses, and excessive per-metric queries. Use indexed filters, batched relationships, bounded pagination, purpose-built aggregates, and response-time instrumentation where appropriate. Frontend pages must avoid overlapping polling, cancel stale requests, minimize re-renders, and paginate/virtualize large collections. Validate P50/P95/max API latency, query counts/plans, response size, UI responsiveness, and functional correctness **during sustained metrics ingestion** for representative modules. The infrastructure snapshot batching commit `dff03df4` is a partial fix only; the global audit, implementation, and cross-module acceptance remain OPEN. Preserve multi-tenant scope, authorization, data retention, and telemetry integrity.


- **Observed 2026-10-28 (Ubuntu local UAT):** After the registered agent started sending native host metrics, the OpsControl Dashboard became severely slow/unresponsive. The operator manually stopped the agent and browser responsiveness returned. This is an operator observation, not yet a measured causal attribution.
- **Severity:** P0 provisional; **status:** OPEN, release-blocking pending controlled reproduction and root-cause evidence.
- **Affected path to investigate:** Agent 1.5.0 / OTel Contrib 0.123.0 → TLS OTLP HTTP ingestion → FastAPI workers → PostgreSQL writes/queries → polling/API responses → React rendering. Shared local CPU, memory, disk I/O, connection-pool pressure and telemetry cardinality are hypotheses, not findings.
- **Preservation:** Do not reset enrollment, delete queued telemetry, alter the verified revision 2, wipe volumes, or weaken existing CI/release security gates. Stop/restart agent only as an explicitly controlled test with recorded timestamps; preserve evidence before any changes.
- **Minimum evidence:** Clock-aligned agent and API logs; host CPU/RAM/swap/disk I/O; container CPU/memory; PostgreSQL active sessions/locks/query latency; OTLP ingest rate and queue depth; browser network request timing, 5-second refresh behavior, React render/profiler or performance trace. Compare agent OFF versus ON with same dashboard route and customer scope.
- **Acceptance:** With agent continuously ingesting, dashboard remains responsive; ingestion is bounded/backpressured; queries are paginated/aggregated and appropriately indexed; UI does not render unbounded raw metrics or overlap refresh requests. Quantitative thresholds and test load to be approved after baseline measurements. Validate sustained operation and restart/recovery without data loss claims; CHK-001 and CHK-002 remain independent blockers.

## RM-DEF-037 — P1 provisional: duplicate records in ingested metrics

- **Observed 2026-10-28 (Ubuntu local UAT):** Operator verified multiple duplicate entries in actual ingested metrics while agent telemetry was active. The duplicate samples, timestamps, labels and storage identifiers have not yet been provided, so this is an observed symptom rather than a confirmed collector or ingestion root cause.
- **Status:** OPEN, release-blocking for telemetry correctness; **severity:** P1 provisional (escalate if duplicate volume contributes to RM-DEF-036 availability impact).
- **Investigation:** Determine whether duplicates are identical samples in persisted storage, multiple legitimate points sharing display timestamp, duplicate API responses, or duplicate frontend rows. Compare resource/organization/agent identity, metric name, attributes, source timestamp, observed timestamp, value, ingestion ID and database row ID. Check simultaneous pipelines/scrapers, collector retry/replay after acknowledgment, queue checkpoint behavior, backend insert idempotency, join fan-out, polling and React list keys. Do not deduplicate by metric name alone or discard valid high-frequency samples.
- **Acceptance:** For a controlled sample set, verify expected collection cadence and uniqueness of the correct logical sample identity end-to-end (agent export → OTLP receipt → database → API → UI); preserve valid distinct points, enforce retry-safe idempotency at the correct boundary, and test restart/replay and tenant isolation. Capture raw before/after counts and explain every duplicate class. Do not assume CHK-001 persistent queue loss is resolved.
- **Relationship:** Investigate alongside RM-DEF-036 (dashboard hang during ingestion), but do not infer that duplication caused the hang without performance evidence.

## RM-DEF-038 — P1 provisional: journald collection permission denied

- **Observed (Ubuntu local UAT):** Adding a journald collection method results in a collector **permission denied** error. The exact journal path, errno, service account, collector receiver config, and failure stage (validation/startup/ingestion) are not yet established.
- **Status:** OPEN; **severity:** P1 provisional. Blocks acceptance of journald method on Linux until a supported least-privilege installation and runtime contract is demonstrated.
- **Investigation:** Capture sanitized collector and agent logs, systemd service identity and sandbox settings (User, Group, SupplementaryGroups, DynamicUser, ProtectSystem, ReadOnlyPaths, InaccessiblePaths), journal ACLs and permissions, and whether the runtime can read journalctl as its effective service account. Confirm receiver supports journald on pinned Contrib 0.123.0 and whether journald is read directly or via journalctl; distinguish permissions from missing executable/path or unsupported config.
- **Remediation criteria:** Use least-privilege journal access (e.g. appropriate systemd-journal/adm group when applicable and service sandbox compatibility); do not chmod journal world-readable, run entire agent as root by default, or bypass existing collector security checks. Installation/upgrade must apply and verify the supported permission model with clear user-facing diagnostics and restart requirements.
- **Acceptance:** With a configured journald method, verified journal events arrive exactly as expected with correct customer/resource attribution, no duplicates or hidden access failures; unauthorized journal access remains denied; agent and dashboard remain stable under simultaneous metrics and logs. Preserve existing UAT state and evidence.

## RM-DEF-039 — Collector onboarding versus centralized administration (architecture approved)

- **Decision (approved by product owner):** Keep **Resource Management → Collectors** as the authoritative centralized collector inventory and ongoing administration workspace. **Compute Instances → Collector Configuration** is a **one-time initial onboarding process**, not a second permanent collector management UI.
- **Initial onboarding:** install/enroll agent → connect → configure initial collection methods → validate → deploy → verify real telemetry → complete. After completion, show verified monitoring state and a link to **Manage Collector**; do not keep prompting installation or replay onboarding during ordinary operations.
- **Ongoing administration:** centrally manage collection methods (including journald), configuration revisions, validation/deployment, health, diagnostics, upgrades, maintenance, and enabled/disabled state. Preserve a clear resource association and return link.
- **Data integrity:** Both entry points reference the same collector ID, resource ID, backend configuration, revision and deployment history; no duplicated independent collector records or competing activation paths. Existing connected agents must be recognized and never require re-enrollment simply to enter management.
- **Status:** APPROVED architecture; implementation OPEN; acceptance requires a one-time successful onboarding followed by ongoing edits through central Collectors, consistent statuses, authorization, and no regressions in telemetry or agent state.
