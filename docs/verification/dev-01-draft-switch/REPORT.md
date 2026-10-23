# DEV-01.1 Compute draft switch — developer verification

Baseline: `origin/main` at `ae4df971d07fa65bbe9e50fbdacba2c68ceae7be`. Work: `fix/dev-01-onboarding-draft-switch`. This is a bounded RM-02 / UI-003 / UI-006 correction; UI-007, UI-009 and UI-023 remain regression boundaries. Independent UAT is pending.

## Reproduction and correction

The authenticated ARCH-001 browser fixture created linked draft A for resource A and unlinked draft B. In the same open Compute workspace it selected A, then B, and saved B's resource identity. Before the correction, the request was `PUT /api/v1/unified/resources/bde084a4-9db7-460b-bc22-019d15b935d6`, returning HTTP 409. Disposable PostgreSQL showed draft B (`0d8e366c-a802-430a-8692-d3b1a36c04d0`) still unlinked, A at revision 1, and no resource under B's name. The browser was retaining A's `created` resource when B had no `resource_id`. This was a wrong-target request, even though backend revision protection rejected the write.

`ResourceForm.resumeDraft` now resolves the selected draft and any linked resource before replacing draft-specific form state. An unlinked draft clears the previous resource. A selection generation guard discards late detail responses from superseded selections. Backend ownership, revision, authorization and readiness behavior is unchanged.

The browser regression exercises A→B and B→A, a delayed A detail response after B is selected, visible validation errors, draft ID preservation, and direct database state. After the correction, B sent `POST /api/v1/unified/resources/vm` (201); A subsequently sent `PUT /api/v1/unified/resources/{A}` (200). Database assertions confirmed A retained its original ID/name, B was created exactly once, and B's draft remained under its original ID without acquiring A's resource ID. The pre-fix and post-fix synthetic evidence is stored locally at `/tmp/opscontrol-dev01-before/draft-switch.json` and `/tmp/opscontrol-dev01-final/draft-switch.json` for this execution. These paths are local evidence, not durable CI artifacts.

## Executed gates

| Command / gate | Result |
| --- | --- |
| `ARCH001_API_ACCEPTANCE=1 ARCH001_ENGINE_ACCEPTANCE=1 ARCH001_BROWSER_ACCEPTANCE=1 ARCH001_EVIDENCE_DIR=/tmp/opscontrol-dev01-before backend/.venv/bin/python scripts/arch001-acceptance.py` on unchanged runtime | Expected regression failure: browser observed `PUT` to A, HTTP 409; preceding migration/API/engine checks passed. |
| Same command with `ARCH001_EVIDENCE_DIR=/tmp/opscontrol-dev01-final` on corrected runtime | PASS: disposable PostgreSQL populated preservation, empty migration round-trip and schema comparison; onboarding and scope negatives; controlled engine/incident/notification; actual authenticated browser and five access browser checks. |
| `ACCESS_EVIDENCE_DIR=/tmp/opscontrol-dev01-access backend/.venv/bin/python scripts/access-acceptance.py` | PASS: 25 access check groups, including populated migration, customer/department RBAC, scope and unsafe downgrade refusal. |
| `cd backend && .venv/bin/python -m unittest tests.test_registry_contracts tests.test_unified_v15_contracts tests.test_access_control -q` | PASS: 43 tests, 0 failures. |
| `npm run lint --prefix frontend` | PASS. |
| `npm test --prefix frontend -- --run` | PASS: 5 script suites, 0 failures. |
| `npm run build --prefix frontend` | PASS; existing chunk-size warning. |
| `cd backend && .venv/bin/python -m alembic heads` | `0037_access_boundaries` (head). |
| `git diff --check` | PASS. |

The acceptance harness uses script-owned disposable PostgreSQL containers and synthetic customer/resource records; it did not touch persistent UAT databases or volumes. Existing positive save/resume and telemetry-gated activation checks, stale revision and customer-scope negatives remain in the harness. CI and independent UAT are reported separately on the PR. No real monitoring or Pentaho runtime acceptance is implied.
