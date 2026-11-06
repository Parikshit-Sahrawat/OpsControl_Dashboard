# OC-ETL-005 — Authoritative monitoring activation and readiness

> OC-ETL-006 follow-on: D01–D06 product-owner authorization is recorded in the [decision register](OC_ETL_005_DECISION_REGISTER.md). The original current/proposed inventory below describes the immutable OC-ETL-005 baseline. [Current implemented subset and blockers](../../verification/oc-etl-006/APPROVAL_AND_SCOPE.md), [migration contract](../../verification/oc-etl-006/MIGRATION_AND_RECOVERY.md), and [served readiness transitions](../../verification/oc-etl-006/READINESS_TRANSITIONS.md) supersede implementation availability only. No provider or release certification is inferred.

Status: **CURRENT AUTHORITY INVENTORY + PROPOSED WORKFLOW CONTRACT / PENDING D03–D10**. Inspected product source `9c021bbb94de3017bdc9f41b6a774d7b378ae9a7`; 2026-11-06 UTC. No new readiness API, activation action, provider behavior or state migration is implemented by this document. See [native binding](OC_ETL_005_NATIVE_BINDING_CONTRACT.md), [decisions](OC_ETL_005_DECISION_REGISTER.md), and [executed verification](../../verification/oc-etl-005/REPORT.md).

A saved configuration, selected Job, recent HTTP response, enabled flag, confirmed association or successful prior execution is insufficient on its own to establish active, healthy, complete or certified monitoring. Each dimension below has a separate backend authority and provenance.

## 1. Current backend authorities — implemented, not interchangeable

| Current authority | Actual meaning / blocking checks | Must not be interpreted as |
|---|---|---|
| `api/etl.py:get_workflow_monitoring` | Persisted observations; `configuration_scope=SUPPORTED_CHILD_RUNTIME_FIELDS_ONLY`; VALID/INCOMPLETE only reflects presence of child Jobs with bounded runtime fields; activation always BLOCKED, provider UNVERIFIED | Full Workflow configuration completeness, approved recurrence, native binding, active collection or healthy execution |
| `models/entities.py:ETLWorkflow.active`, `JobOrder.active/monitoring_enabled` | Persisted configuration settings | Authoritative monitoring readiness or a workload running state |
| `data_pipelines/api.py:associate/register_job/select_job` | Explicit scoped native candidate and current-generation method association; staged legacy candidate stays quarantined/unselected | Runtime verification, successful provider connectivity or permission to activate |
| `service.eligible` | Current capability/connection/method/reader-definition/source-generation proof: accepted AUTHENTICATED_RUNTIME evidence, compatible profile RUNTIME_VERIFIED, enabled method, active connection and live integration; Pentaho context adds exact-build/surface matching when supplied | Independent genuine-provider certification simply because a field contains a trusted-looking label |
| `service.reader_equivalence`, `check_ticket`, `acquire` | Physical reader contract, source lock, generation/fence/owner/mode/lease validity, holds/continuity and current eligible enabled readers | A business Workflow scheduler lease or exactly-once execution guarantee |
| `service.blockers` / integration `/validate` | Configuration/selection/resource/association/runtime-proof/continuity/hold checks and existence of durable telemetry | Final activation or universally fresh evidence; last_received_at being non-null is not an age check |
| integration `/activate` | Existing confirmed monitoring activation additionally requires selected canonical resources, PIPELINE_V16_PROXY handoff and `unified.engines.source_readiness` for each; audits and enables existing monitoring | An API to run, schedule, retry or terminate provider jobs; a Workflow-level activation implementation |
| `unified/api.py:verification/activate_resource` | Customer/collector/source enablement and actual recent provider observations; mapped V1.6 resources must use eligible active integration; no bypass via legacy resource activate | A replacement for native capability proof, per-Job bindings or Workflow completion |
| `api/activation.py`, `services/activation_engine.py`, `MonitoringActivation.status` | Data Source monitoring plan preview/apply/disable with its own permissions/rules/worker prerequisites | Workflow ACTIVE inferred from an unrelated Data Source activation |
| `_item`, source health, native reducer, incident recovery | Collector freshness, receipt/reader status, immutable execution/attempt outcomes and evidence-backed incident/recovery projections respectively | One combined green Boolean proving every other dimension or release certification |

Current freshness calculations differ intentionally in existing contexts: `_item` uses last_success_at and `max(120, interval_seconds*2+30)`; resource source_readiness uses actual ended_at and `max(120, interval_seconds*3)` plus ETL complete-inventory/SUCCESS requirements. Do not silently unify these into a new Workflow policy or use a producer timestamp to spoof a recent server receipt. D05 must approve a versioned basis, thresholds and clock uncertainty policy. Existing thresholds are preserved, not changed by this task.

`service.accept` atomically persists evidence/receipt/projection and checkpoint under its current ticket. Its current `accepted` counter increments for newly stored raw records, including records with outcome QUARANTINED_IDENTITY; it is not a count of verified canonical native projections. Quarantined batches can update received timestamps and set source.health=DEGRADED. A raw receipt/count or recent timestamp therefore cannot establish valid native binding or healthy execution. The function distinguishes source-observed evidence timestamps from its server clock used for receipts/source scheduling. This does not fix collector CHK-001 or prove zero-loss delivery. Native outcome, monitoring freshness, schedule compliance and evidence completeness remain independent (ARCH-ETL-001 §3).

## 2. Proposed six-dimensional Workflow evaluation — not served yet

A future backend evaluator must return a versioned snapshot with evaluated_at, evidence/proof IDs, current model revisions, source/method generations, policy version, explanatory reason codes and scope. No stored UI flag may override it. Authorization filters must apply before evaluation; an invisible dependency must not be reported as a confirmed absence or leak another customer's data. Use UNKNOWN/UNAVAILABLE where visibility or evidence is insufficient.

| Dimension | Proposed states | Authority / transitions | Blocking conditions / required evidence |
|---|---|---|---|
| Configuration completeness | DRAFT, INCOMPLETE, VALID, INVALID, UNRESOLVED_CONTRACT | Versioned approved Workflow/Job schema and effective monitoring-expectation policy; edits invalidate the previous evaluation; revalidate after persisted changes | Missing required approved fields → INCOMPLETE; incompatible data → INVALID; missing approved recurrence/catalog/threshold semantics → UNRESOLVED_CONTRACT. Current supported runtime validity alone cannot yield full VALID |
| Binding validity | UNBOUND, STAGED, VALID, CONFLICTED, STALE, RETIRED | Native binding versions and scoped source/method proof references; stage does not confirm; current-gen confirmation required after handoff; retirement never erases past tuples | Parent/customer/environment/native authority/cardinality/proof/version mismatch; quarantined or ambiguous native candidate; unresolved source namespace; stale generation or changed reader hash. A display name is never proof |
| Monitoring activation | DISABLED, BLOCKED, APPROVAL_REQUIRED, ACTIVE, SUSPENDED, REVOKED | Separate desired and effective monitoring activation, explicit approval and auditable backend apply; derive from existing integration/resource authorities once D03 is approved | No eligible native binding, unverified required reader, missing current proof, holds/continuity gap, revoked authority, changed revision, invalid policy or absent prerequisites. No implicit activation on save; no new authority from Workflow.active |
| Collector/source connectivity | UNKNOWN, UNVERIFIED, REACHABLE, UNREACHABLE, DEGRADED, UNSUPPORTED | Authenticated, authorized, read-only observation for exact source/reader/build/capability, with real server-side acceptance; changes invalidate old proof | HTTP200/schema metadata/fixtures alone cannot yield verified provider connectivity; wrong auth/TLS/egress/namespace or unsupported method remains blocked. Distinguish known unavailable capability from transient connection failure |
| Evidence freshness | NO_DATA, FRESH, STALE, GAP, UNKNOWN | Accepted receipt and observed-time provenance under approved, versioned per-source policy; evaluate on backend, expose basis/age/evaluated_at | Missing receipts → NO_DATA; age outside approved bounds → STALE; continuity/coverage loss → GAP; missing or untrusted clock/policy → UNKNOWN. Fresh receipt does not imply successful execution or complete inventory |
| Runtime operational health | UNKNOWN, HEALTHY, DEGRADED, UNHEALTHY (proposed summary), with separate outcome/completeness/schedule fields | Existing canonical histories/attempt revisions, approved event catalog/policy, Workflow required-child completeness and evidence-backed recovery; no second run engine | HEALTHY needs fresh verified applicable evidence, approved expected Workflow completeness/outcome and downstream/recovery observation where required. Unknown schedule/source, conflicting claims or partial evidence cannot be silently counted as healthy. Detailed aggregation remains D03/G5 blocked |

These state names are a proposed public contract, not a migration of current enums. Do not map the proposed operational summary directly to the v1.7 Normal/Pending/Firing/Recovered event lifecycle or legacy OPEN/RESOLVED alerts: those represent different dimensions and require recovered catalog/override authority.

### Proposed snapshot envelope (illustrative schema, not an existing endpoint)

```json
{
  "contract_version": "oc-etl-readiness/v1-proposed",
  "workflow_id": "typed-uuid-reference",
  "configuration": {"status": "UNRESOLVED_CONTRACT", "policy_version": null},
  "binding": {"status": "STAGED", "binding_version": null},
  "activation": {"desired": "DISABLED", "effective": "BLOCKED"},
  "connectivity": {"status": "UNVERIFIED", "proof_id": null},
  "freshness": {"status": "NO_DATA", "basis": null},
  "operational": {"health": "UNKNOWN", "outcome": "UNKNOWN", "completeness": "UNKNOWN"},
  "reasons": ["WORKFLOW_CONTRACT_NOT_APPROVED", "NATIVE_BINDING_UNCONFIRMED"],
  "release_readiness": "NO_GO"
}
```

Actual implementation must use UUIDs and server-produced evaluation/proof timestamps, not these placeholders. The envelope is blocked pending contract, permission, schema and provider acceptance; it is not permission to implement guessed defaults.

## 3. Activation preview/apply contract — proposed D03/D04

1. A read/preview evaluates current authorized Workflow, children, native bindings, source/method/connection/capability versions, configured expectations and applicable holds without contacting a provider as a side effect of saving. Return blockers with references visible to the caller; preserve authoritative UNKNOWN states.
2. Preview is advisory, not a reusable authorization token. Explicit apply includes expected revisions and the approved binding/source set. Re-read and lock affected objects in deterministic order, use the existing request transaction-authority/revocation protection, and reject changes since preview. An expired/revoked role or source token must fail at the server even if the browser cached permission.
3. Apply uses the established collection/integration/resource activation machinery only after all required selected methods have their current independently verified capability proofs, eligible bindings, recent scoped receipts, safe source continuity and approved configuration. Do not set runtime_verified or compatibility from client input, a successful HTTP response or a controlled fixture.
4. Commit activation transition, exact approved snapshot and audit atomically. No partial active child set may be presented as a fully active Workflow. If only a subset is explicitly approved, report its scope/limitations and unknown required-child completeness; subset semantics require D03 approval.
5. A source-generation/method/credential-reader change invalidates the corresponding proof and binding evaluation. Holds/revocation produce effective SUSPENDED/REVOKED/BLOCKED as appropriate; do not silently substitute another reader or copy an old certification to the new generation. Preserve accepted historical state and require reviewed continuity/reverification.
6. Desired ACTIVE may coexist with a transient connectivity error or failed workload. Report those dimensions independently; do not hide failures by silently disabling monitoring or call configured-but-unreachable monitoring healthy. Existing collection retries are not ETL workload retries.
7. Retiring monitoring stops future eligible observation/routing through approved lifecycle controls only. It never stops, cancels, retries, deletes or schedules a provider workload.

Existing integration behavior blocks on any enabled unverified method. The architecture allows explicit limited eligible-method coverage, but this is not permission to auto-disable unsupported methods or claim full parity. Operators must explicitly select the approved coverage and respect current gates; any future Workflow subset policy is a D03 decision.

## 4. Readiness and release are independent

A release gate failure does not falsify an independently observed Job outcome. Conversely, a genuinely healthy observed workload cannot waive security, collector durability, checkpoint/rollback, provider or release gates. A future evaluation must retain release/durability warnings separately from the six technical dimensions. No automatic production activation or deployment is authorized here.

Current CHK-001 FAIL and CHK-002 BLOCKED prevent durable/rollback release certification; SECURITY BLOCKED and RELEASE NO-GO remain. Synthetic fixtures may test gate behavior but cannot be provider qualification. Genuine proof must identify exact installed build/surface, authenticated source/generation/reader, native IDs/epochs, original evidence hashes, server receipts and accountable reviewer/approval. TLS, egress allowlists, read-only credentials, secret references and redaction remain existing mandatory prerequisites.

## 5. Security review and acceptance cases

Technical review is a source/contract review by Codex with controlled PostgreSQL negative tests, not accountable human security approval. D04/D06/D09 signoffs remain pending. Neither the old collector-study role approval nor the nine controlled functional owner decisions grants this new activation authority.

| Case | Required assertion | Current result / future requirement |
|---|---|---|
| RD-01 | Saved/valid supported fields + unbound/unverified native source never become ACTIVE/HEALTHY | Current Workflow BLOCKED/UNVERIFIED and integration/resource denials tested |
| RD-02 | Valid binding, exact proof and complete current prerequisites allow explicit monitored activation without workload control | New Workflow-positive ACTIVE path NOT RUN / BLOCKED D03/D09; do not synthesize proof |
| RD-03 | Missing source, expired generation, retired method, changed reader/proof, holds and revoked roles block before commit | Current missing/generation/role negatives tested; full proposed aggregate matrix pending |
| RD-04 | A source can be fresh while execution FAILED; old SUCCESS can be STALE; no source is not NO_RUN | Existing 004 stale/missing browser evidence retained; new aggregate/clock/coverage policy D05/G5 pending |
| RD-05 | Conflicting identity/late evidence quarantined; historical failures and attempts remain immutable | Existing reducer/receipt guards reused; genuine-provider epoch/attempt certification NOT TESTED |
| RD-06 | Preview/apply race, in-flight reader, crash and failed persistence leave no partially active Workflow or checkpoint loss | New aggregate implementation, forward migration and protocol tests BLOCKED D03/D06; CHK-001 not waived |
| RD-07 | Revocation after preview, forged ALL/customer/resource selection and worker-as-human denied | Existing scoped security baseline retained; new approval keys not introduced |
| RD-08 | Limited capability coverage is explicit and cannot be reported as full Workflow health or release GO | Product subset/completeness policy pending; unsupported providers stay BLOCKED/NOT TESTED |

No wall-clock freshness threshold, recurrence, retry grouping, calendar or event precedence is invented. The acceptance plan must be executed against actual implementation and independently persisted receipts when approved; documentation and a synthetic negative test are not certification.
