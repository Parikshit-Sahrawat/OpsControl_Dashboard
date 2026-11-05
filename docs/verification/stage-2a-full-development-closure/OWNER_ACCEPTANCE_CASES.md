# Nine original individual owner acceptance cases

No new owner signoff is inferred. Execute only in an authorized disposable environment; do not use live UAT credentials. Existing owner-approved Kubernetes removal is separate from these active features.

## RM-01 — Customer Organizations are monitored customers, distinct from provider Departments

Owner decision: PENDING. Expected: Customer Organizations are monitored customers, distinct from provider Departments. Reject unauthorized/cross-customer requests, preserve stored configuration on reload, and retain immutable evidence.

Source: `backend/app/api/organizations.py`, `backend/app/security/scope.py`, `frontend/src/pages/ResourceManagementV2.jsx`.

Test definitions: `backend/tests/test_sprint08_rbac.py`.

Reproduce: run the task-owned PostgreSQL `scripts/scope-removal-regressions.py` with `SCOPE_EVIDENCE_DIR` set to a new path; select the named test modules from the complete backend log. For UI/API acceptance use the corresponding architecture/release commands in TEST_RESULTS.md. Compare the named tests and applicable browser assertions with the expected requirement; record exact SHA, role, organization, expected/actual, screenshots and owner name/date.

Evidence authority: original controlled results and exact named tests remain in requirements.json; new regression output is raw/resumed/regressions/backend-full.log. No provider or independent UAT acceptance inferred.

Remaining action: Retain negative cross-entity tests; independent UAT.


Individual acceptance procedure: Create/select a synthetic customer in Resource Management; create/select an internal Department in Access Management. Confirm neither appears as the other entity and unauthorized tenant IDs are denied.

Specific controlled evidence: `scripts/arch001-acceptance.py with ARCH001_BROWSER_ACCEPTANCE=1; backend/tests/test_sprint08_rbac.py`. Record owner decision and any disagreement; do not treat this checklist as execution evidence.

## RM-04 — Collector configuration supports multiple independently added methods

Owner decision: PENDING. Expected: Collector configuration supports multiple independently added methods. Reject unauthorized/cross-customer requests, preserve stored configuration on reload, and retain immutable evidence.

Source: `backend/app/telemetry/api.py`, `frontend/src/pages/CollectorControl.jsx`.

Test definitions: `backend/tests/test_managed_telemetry.py`.

Reproduce: run the task-owned PostgreSQL `scripts/scope-removal-regressions.py` with `SCOPE_EVIDENCE_DIR` set to a new path; select the named test modules from the complete backend log. For UI/API acceptance use the corresponding architecture/release commands in TEST_RESULTS.md. Compare the named tests and applicable browser assertions with the expected requirement; record exact SHA, role, organization, expected/actual, screenshots and owner name/date.

Evidence authority: original controlled results and exact named tests remain in requirements.json; new regression output is raw/resumed/regressions/backend-full.log. No provider or independent UAT acceptance inferred.

Remaining action: Verify method attribution and real agent separately.


Individual acceptance procedure: Register a VM fixture and configure independent methods. Save/reload each method; changing one must not overwrite another. Unverified method activation must fail.

Specific controlled evidence: `arch2/browser.json; backend/tests; scripts/arch001-acceptance.py`. Record owner decision and any disagreement; do not treat this checklist as execution evidence.

## RM-05 — Method-specific canonical collection identity and one fenced active owner

Owner decision: PENDING. Expected: Method-specific canonical collection identity and one fenced active owner. Reject unauthorized/cross-customer requests, preserve stored configuration on reload, and retain immutable evidence.

Source: `backend/app/telemetry/api.py`, `backend/app/telemetry/models.py`.

Test definitions: `backend/tests/test_managed_telemetry.py`.

Reproduce: run the task-owned PostgreSQL `scripts/scope-removal-regressions.py` with `SCOPE_EVIDENCE_DIR` set to a new path; select the named test modules from the complete backend log. For UI/API acceptance use the corresponding architecture/release commands in TEST_RESULTS.md. Compare the named tests and applicable browser assertions with the expected requirement; record exact SHA, role, organization, expected/actual, screenshots and owner name/date.

Evidence authority: original controlled results and exact named tests remain in requirements.json; new regression output is raw/resumed/regressions/backend-full.log. No provider or independent UAT acceptance inferred.

Remaining action: Retain generation/fencing regression under concurrency.


Individual acceptance procedure: Execute lease/identity negatives with two synthetic agents: canonical method identity survives retries, second active owner is fenced, wrong token/customer and replay are rejected.

Specific controlled evidence: `release/remote_protocol_probe.log; release/remote-telemetry.json`. Record owner decision and any disagreement; do not treat this checklist as execution evidence.

## AM-01 — Internal employees, departments, direct/inherited roles and customer-scoped RBAC

Owner decision: PENDING. Expected: Internal employees, departments, direct/inherited roles and customer-scoped RBAC. Reject unauthorized/cross-customer requests, preserve stored configuration on reload, and retain immutable evidence.

Source: `backend/app/api/access.py`, `backend/app/security/access_models.py`.

Test definitions: `backend/tests/test_sprint08_rbac.py`.

Reproduce: run the task-owned PostgreSQL `scripts/scope-removal-regressions.py` with `SCOPE_EVIDENCE_DIR` set to a new path; select the named test modules from the complete backend log. For UI/API acceptance use the corresponding architecture/release commands in TEST_RESULTS.md. Compare the named tests and applicable browser assertions with the expected requirement; record exact SHA, role, organization, expected/actual, screenshots and owner name/date.

Evidence authority: original controlled results and exact named tests remain in requirements.json; new regression output is raw/resumed/regressions/backend-full.log. No provider or independent UAT acceptance inferred.

Remaining action: Independent UAT of all authorized actions.


Individual acceptance procedure: Create employee in one provider Department, inspect inherited/direct effective permissions, then revoke access and attempt direct API navigation. Expect no implicit customer grant and 403 for unauthorized API.

Specific controlled evidence: `arch2/access-v15-browser.json; resumed/v16-final/sprint08-http.json`. Record owner decision and any disagreement; do not treat this checklist as execution evidence.

## CMP-01 — Windows/Linux VM/EC2 native operational health

Owner decision: PENDING. Expected: Windows/Linux VM/EC2 native operational health. Reject unauthorized/cross-customer requests, preserve stored configuration on reload, and retain immutable evidence.

Source: `backend/app/models/entities.py`, `backend/app/worker/collector_runtime.py`.

Test definitions: `backend/tests/test_infrastructure_health_projection.py`.

Reproduce: run the task-owned PostgreSQL `scripts/scope-removal-regressions.py` with `SCOPE_EVIDENCE_DIR` set to a new path; select the named test modules from the complete backend log. For UI/API acceptance use the corresponding architecture/release commands in TEST_RESULTS.md. Compare the named tests and applicable browser assertions with the expected requirement; record exact SHA, role, organization, expected/actual, screenshots and owner name/date.

Evidence authority: original controlled results and exact named tests remain in requirements.json; new regression output is raw/resumed/regressions/backend-full.log. No provider or independent UAT acceptance inferred.

Remaining action: Preserve source/health distinction; real-provider acceptance later.


Individual acceptance procedure: With controlled compute signal fixture, open VM Health and inspect evidence provenance; change to stale/missing evidence and require explicit unknown/stale, never healthy from registration alone. Genuine Windows/Linux/EC2 certification remains separate.

Specific controlled evidence: `backend/tests/test_infrastructure_health_projection.py; requirements.json exact test_paths; release/scope-browser.json`. Record owner decision and any disagreement; do not treat this checklist as execution evidence.

## CMP-02 — One owning customer for each VM/EC2

Owner decision: PENDING. Expected: One owning customer for each VM/EC2. Reject unauthorized/cross-customer requests, preserve stored configuration on reload, and retain immutable evidence.

Source: `backend/app/unified/api.py`, `backend/app/models/entities.py`.

Test definitions: `backend/tests/test_unified_v15_contracts.py`.

Reproduce: run the task-owned PostgreSQL `scripts/scope-removal-regressions.py` with `SCOPE_EVIDENCE_DIR` set to a new path; select the named test modules from the complete backend log. For UI/API acceptance use the corresponding architecture/release commands in TEST_RESULTS.md. Compare the named tests and applicable browser assertions with the expected requirement; record exact SHA, role, organization, expected/actual, screenshots and owner name/date.

Evidence authority: original controlled results and exact named tests remain in requirements.json; new regression output is raw/resumed/regressions/backend-full.log. No provider or independent UAT acceptance inferred.

Remaining action: Retain FK and forged-ID negatives.


Individual acceptance procedure: Create a VM under customer A, attempt a second customer owner and forged cross-customer modification. Expect exclusive owner and denial, while history and tenant relationships persist.

Specific controlled evidence: `resumed/regressions/preservation.json; requirements.json exact tenant/ownership test definitions`. Record owner decision and any disagreement; do not treat this checklist as execution evidence.

## API-01 — HTTP/TLS/synthetic endpoint operational monitoring

Owner decision: PENDING. Expected: HTTP/TLS/synthetic endpoint operational monitoring. Reject unauthorized/cross-customer requests, preserve stored configuration on reload, and retain immutable evidence.

Source: `frontend/src/pages/MonitoringSetup.jsx`, `backend/app/services/activation_engine.py`, `backend/app/api/remote_protocol.py`.

Test definitions: `backend/tests/test_activation_hydration.py`.

Reproduce: run the task-owned PostgreSQL `scripts/scope-removal-regressions.py` with `SCOPE_EVIDENCE_DIR` set to a new path; select the named test modules from the complete backend log. For UI/API acceptance use the corresponding architecture/release commands in TEST_RESULTS.md. Compare the named tests and applicable browser assertions with the expected requirement; record exact SHA, role, organization, expected/actual, screenshots and owner name/date.

Evidence authority: original controlled results and exact named tests remain in requirements.json; new regression output is raw/resumed/regressions/backend-full.log. No provider or independent UAT acceptance inferred.

Remaining action: Confirm actual target freshness/authorization; real-network acceptance later.


Individual acceptance procedure: Use controlled HTTPS fixture with GET/HEAD, expected status, latency threshold and approved header. Save/reload settings, trigger failure then recovery and inspect persisted evidence; reject forbidden methods, untrusted TLS and wrong tenant.

Specific controlled evidence: `release/remote-telemetry.json; release/security_release_probe.log; requirements.json saved-settings test definitions`. Record owner decision and any disagreement; do not treat this checklist as execution evidence.

## OPS-03 — Recovery validation with health, workload, dependencies and observation

Owner decision: PENDING. Expected: Recovery validation with health, workload, dependencies and observation. Reject unauthorized/cross-customer requests, preserve stored configuration on reload, and retain immutable evidence.

Source: `backend/app/worker/alert_engine.py`, `backend/app/native_incidents/service.py`.

Test definitions: `backend/tests/test_native_incidents_v15.py`.

Reproduce: run the task-owned PostgreSQL `scripts/scope-removal-regressions.py` with `SCOPE_EVIDENCE_DIR` set to a new path; select the named test modules from the complete backend log. For UI/API acceptance use the corresponding architecture/release commands in TEST_RESULTS.md. Compare the named tests and applicable browser assertions with the expected requirement; record exact SHA, role, organization, expected/actual, screenshots and owner name/date.

Evidence authority: original controlled results and exact named tests remain in requirements.json; new regression output is raw/resumed/regressions/backend-full.log. No provider or independent UAT acceptance inferred.

Remaining action: Independent downstream/recovery UAT; no automatic certification.


Individual acceptance procedure: Trigger a synthetic incident, attempt recovery without required health/workload/dependency observations (must deny), then supply controlled observations and verify authorized transition plus audit history.

Specific controlled evidence: `arch2/browser.json; resumed/v16-final/pentaho-incident-http.json; requirements.json exact recovery tests`. Record owner decision and any disagreement; do not treat this checklist as execution evidence.

## UI-010 — Preserve distinction between monitored customer organizations and internal employee departments

Owner decision: PENDING. Expected: Preserve distinction between monitored customer organizations and internal employee departments. Reject unauthorized/cross-customer requests, preserve stored configuration on reload, and retain immutable evidence.

Source: `backend/app/models/entities.py`, `backend/app/security/access_models.py`, `scripts/access-acceptance.py`.

Test definitions: .

Reproduce: run the task-owned PostgreSQL `scripts/scope-removal-regressions.py` with `SCOPE_EVIDENCE_DIR` set to a new path; select the named test modules from the complete backend log. For UI/API acceptance use the corresponding architecture/release commands in TEST_RESULTS.md. Compare the named tests and applicable browser assertions with the expected requirement; record exact SHA, role, organization, expected/actual, screenshots and owner name/date.

Evidence authority: original controlled results and exact named tests remain in requirements.json; new regression output is raw/resumed/regressions/backend-full.log. No provider or independent UAT acceptance inferred.

Remaining action: Preserve cross-entity negative UAT.


Individual acceptance procedure: Navigate customer Organizations then internal Departments, create an employee requiring an existing Department and inspect the two distinct UUID/entity sets. No accidental customer grant from Department membership.

Specific controlled evidence: `arch2/access-v15-browser.json; resumed/v16-final/sprint08-http.json`. Record owner decision and any disagreement; do not treat this checklist as execution evidence.
