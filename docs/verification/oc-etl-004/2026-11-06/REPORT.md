# OC-ETL-004 — Workflow/Job configuration and bounded readiness

2026-11-06 UTC. Baseline `ed4c011dddd8de7a5f5d8c816d391608c1597f5f`; branch dev/post-pr78-architecture-closure-20261105; draft PR80. Implementation `1d3004d24c67279746b6225e8951c9bf2b534075`, read-only details follow-up and exact clean tested source **`6a9c7a2cc2eafbac76b6e7b48a54d35c9d115f19`**. Final evidence commit adds documentation/traceability only. Prior OC-ETL-002/003/003A evidence and corrections are retained.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**

## Implemented and verified scope

Resource Management → Data Sources / Resources → Data Pipelines → select one customer → ETL Workflows. The existing customer/environment filters own scope; no second configuration plane or separate ETL application is introduced. Existing legacy resource/source integration tools remain available.

- Workflow list/create/edit/details with name, immutable owning customer, environment, supported timezone/weekdays, expected windows, optional expected Workflow duration and SLA. Existing schemas validate writes; expected fields persist and reload. Supported inputs do not execute or schedule external workloads.
- Child Job create/edit with immutable parent/customer/environment, host identity on creation, name and expected runtime. Saved host and native execution receipt are read-only projections. Workflow timing/SLA are not copied into the child editor. Unassigned legacy Jobs are not automatically grouped or reparented.
- Directed dependency editor with self/duplicate checks for usability and actual transactional backend cycle/ownership validation as authority. Existing per-workflow and authorization locks are unchanged and all seven concurrency/security cases rerun.
- Backend-confirmed bounded configuration state and existing collector telemetry freshness. Missing history = MISSING; persisted receipts reuse existing `_item` collector status calculation (including STALE). Workflow activation remains BLOCKED, provider connectivity UNVERIFIED. Saved flags are labeled settings, never healthy/operational proof.
- Read-only users can inspect saved windows/calendar/duration/SLA and evidence but cannot see mutation controls. Actual backend rejects unauthorized writes, cross-customer reads, cross-workflow edges and populated environment changes.
- Generation/tenant guards, unmount invalidation, selected-customer headers, loading/empty/error states, retained unsaved fields after invalid/network saves, accessible names/native controls, and mobile rendering. Tests delay a **real** old-tenant response and inject one network failure; normal responses and persistence use actual authenticated APIs.

Only the existing `get_workflow_monitoring` API function changed, adding hostname, telemetry status and explicit bounded readiness metadata. No mutation handler, scope hook, audit/authorization behavior, schema, applied migration, collector pin or runtime engine changed. PROTECTED_CONTRACT_SHA256.json compares protected bytes and the DAG function against baseline. Backend schema error redaction remains intact; frontend supplies field-specific timezone checks without exposing backend internals.

## Actual verification at the committed source

| Check | Result | Evidence |
|---|---|---|
| Existing OC-ETL-002/003 regression baseline plus one actual UI integration test | **85 PASS, 0 failures/errors/skips** (84 retained + 1 new) | acceptance/regressions.log; RESULTS.json |
| Authenticated Chromium | **19 PASS groups**, zero page runtime errors | acceptance/workflow-browser-results.json and workflow-browser.log |
| Independent PostgreSQL reconciliation after browser flow | Workflow windows 08:00–10:00, SLA900, duration500; Jobs150/120 seconds, expected parent/customer/environment/hostname; exactly one dependency; legacy/foreign parent preserved | acceptance/workflow-db-reconciliation.json |
| Authenticated HTTP baseline assertions | **21 PASS** included in retained suite | acceptance/http-results.json |
| Migration, preservation and actual dump/restore | **6 PASS groups**, no guard bypass | acceptance/rollback-results.json; raw logs and synthetic backup archive |
| Frontend unit checks | **45 PASS, 0 failures/skips** | frontend-acceptance.log |
| Frontend lint and production build | PASS, exit0; existing chunk-size warning retained | lint-acceptance.log; build-acceptance.log |
| Focused Python Black/Ruff/compile and pinned actionlint | PASS | black-check.log; ruff-final.log; workflows-acceptance.log |
| Cleanup | Container absent; API and UI stopped; scoped removal only | acceptance/RESULTS.json; every attempt records cleanup |

Counts overlap; browser groups and HTTP assertions are not additional unittest case counts. Provider certification and independent owner UAT were not run and are not inferred from these fixtures.

PostgreSQL: `PostgreSQL 17.11 on x86_64-pc-linux-musl, compiled by gcc (Alpine 15.2.0) 15.2.0, 64-bit`. Immutable local image identity: `sha256:ab20e934b27ba3ff927c1b4c9ff8cf6c32f315f743efe68dd3441182a87fb085`. The fixture is disposable PostgreSQL Docker with tmpfs and owned loopback API/Vite processes plus Chromium. Browser acceptance does not claim an API/frontend container topology; existing hosted Docker packaging/startup checks remain required. No production or owner UAT resource was accessed.

## Reproducible commands

From repository root, installed locked frontend/backend dependencies and matching pinned Playwright/Chromium:

```sh
ETL_WORKFLOW_UI_ACCEPTANCE=1 PLAYWRIGHT_MODULE=/tmp/oc-closure-tools/node_modules/playwright/index.mjs PLAYWRIGHT_BROWSERS_PATH=/tmp/oc-etl003a-browsers ETL_SCOPE_EVIDENCE_DIR=/tmp/etl004-acceptance backend/.venv/bin/python scripts/etl-scope-acceptance.py
npm test --prefix frontend
npm run lint --prefix frontend
npm run build --prefix frontend
bash scripts/check-workflows.sh
```

The reused harness sets an exact task UI CORS origin before starting its API, generates private synthetic credentials, runs real migrations and authenticated requests, and cleans up only its exact container/processes in finally. Its inherited oc-etl002 prefix/label is intentional compatibility. The private browser fixture is mode0600 inside a temporary directory and removed even on failure; credentials/tokens are not exported in acceptance artifacts. Raw logs, screenshots and source identities are retained before cleanup. Local dependency/cache/build output live under /tmp because the environment's root filesystem is constrained; hosted CI uses its normal clean runner. No TLS verification, security control or assertion was disabled.

## Retained failed attempts

| Attempt | Actual result / repair |
|---|---|
| attempt1 | 85 cases, 84 pass + 1 import error: test imported Role/UserRole from the wrong model module; corrected fixture imports |
| attempt2 | 85 cases, 84 pass + 1 fixture error: grant FK requires persisted role assignment; added the existing required flush, not an authorization bypass |
| attempt3 | 85 cases, 84 pass + 1 browser failure: selector expected obsolete Resource Management button; used actual authenticated navigation |
| attempt4 | 85 cases, 84 pass + 1 browser failure: wrapped select label included option text; added explicit accessible dependency control names |
| attempt5 | 85 PASS / 16 browser groups; preliminary dirty source |
| attempt6 | 85 cases, 84 pass + 1 browser failure: intentionally redacted backend validation could not provide field-specific UI text; retained redaction and added frontend timezone validation plus independent backend-negative assertion |
| attempt7 / final | 85 PASS / 19 groups at preliminary/earlier source; final supported-state and read-only details refinement then rerun |
| acceptance | **85 PASS / 19 groups at clean `6a9c7a2cc2eafbac76b6e7b48a54d35c9d115f19`**, source/hash/database/cleanup evidence retained |

An initial formatting-tool installation could not write the default home npm cache; an explicit /tmp cache resolved it with TLS verification enabled. Its failure log is retained. All test failures remain failures in their historical attempts.

## Remaining approved gaps — no invented contracts

[OPEN_GAPS.md](OPEN_GAPS.md) gives exact contract evidence and prerequisites. Frequency/recurrence, a distinct long-running threshold, Workflow Job/native PipelineJob binding, authoritative Workflow activation and end-to-end provider readiness are **BLOCKED**. The supported-field indicator is explicitly scoped to child runtime configuration and does not certify full Workflow readiness. No stale cutoff was invented: existing backend collector logic is reused. User/provider/native-source certification, occurrence/lifecycle evaluation and owner acceptance remain separate.

See [traceability](../../../architecture/unified-implementation-baseline/ETL_ARCHITECTURE_IMPLEMENTATION_MATRIX.md) and the 56-ID CI matrix. All 31 included journeys remain included, 30 exact numbered definitions SOURCE_NOT_RECOVERED, Journey20 excluded and Journey32 skipped. Nine prior approvals remain OWNER_APPROVED_CONTROLLED_SCOPE — INDEPENDENT_UAT_PENDING; no new ETL owner acceptance is inferred.

## Hosted verification

The existing pipeline job now installs pinned isolated Chromium tools and executes this owned browser/PG harness in addition to its existing checks. Final-head workflow conclusions will be recorded in the PR80 closure comment after the evidence commit is pushed. Local PASS is not a claim that hosted CI has passed; applicable checks must finish without failure. No merge, deployment, branch protection change, schema retirement or release-gate promotion is authorized.
