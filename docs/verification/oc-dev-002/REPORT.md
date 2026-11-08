# OC-DEV-002 — Sprint1 implementation and preservation

Outcome: **PARTIAL implementation; remaining sprint acceptance gaps explicit**. Planning authority: draft PR81 `af9bad0428dd4023829e210cb923d32fa0adba3c`. Refreshed main `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`. PR80 remains draft at958193f266c89302b2f1919e3703faece591e0af; PR81 remains draft at its approved planning head. New branch `dev/oc-dev-002-secure-resource-preservation` starts from main; no unmerged work overwritten or merged.

Implementation078d477053e23facfd8bfbd4b5df066c606bd6bf; preservation/test increment and exact final tested source **a4aea63ce07c24a9431aba121804df59e35de00d**. Final evidence commit is reported in the development PR handoff. CI policy: **TRIGGER AND EXIT — CI TRIGGERED — RESULT PENDING**. No CI completion monitoring or required-check bypass.

## Changed behavior and workstream disposition

| Item | Implemented / demonstrated | Remaining acceptance gap |
|---|---|---|
|103 authorization/revocation | Protected/unknown ownership fields now422 rather than silently ignored in DataSource/Collector updates. Actual authenticated viewer mutation denied403; persisted organization unchanged. Existing scope and authorization hooks retained | This was input-contract hardening, not a proven prior cross-tenant write exploit. Broad cross-resource revocation/stale-session authenticated coverage not added or certified; existing56 integration cases remain bounded |
|121 preservation | Existing main migration guards unchanged. Fresh/populated upgrade, drift, empty downgrade/re-upgrade and populated refusal pass. New pg_dump/pg_restore comparison matches all100 public tables' counts/content hashes/columns/FKs; source unchanged and restore DB removed | Main is0038. PR80's0039–0041 guards remain unmerged and untouched, not silently included in this candidate. Whole-table restore is not WAL/PITR/DR certification |
|105 resource lifecycle | Both collector PATCH APIs now refuse enabling on disabled parent409 before mutation. Real HTTP create/disable/forbidden mutation and persisted ownership/collector flags tested | Full Compute ResourceManagementV2 create/edit/reload browser journey and every stale-session/tenant-switch negative remain NOT TESTED here. Existing browser is pipeline wizard, not blanket resource acceptance |
|106 template/configuration lifecycle | Retained actual API/browser configuration/draft/association/activation-negative evidence passes; no false healthy/active state introduced | No new template attachment/resolution feature implemented. Full monitoring-template version/override/reload matrix remains incomplete; passing pipeline configuration is not that proof |
|135 global responsiveness | Repeatable bounded concurrent PostgreSQL sample writes and authenticated infrastructure reads; stable ID accounting and latency raw samples retained | Global RM-DEF-036 NOT REPRODUCED by this probe. No verified bottleneck fixed. Full OTLP ingestion, all-module query counts/plans and representative browser load remain NOT TESTED |

Changes: `backend/app/schemas/monitoring.py` (extra fields forbidden on update); `backend/app/services/collector_lifecycle.py` (disabled-parent guard); both `api/monitoring.py` and `api/resource_management.py` call guard; `backend/tests/test_sprint_resource_lifecycle.py` (five regressions); `backend/scripts/v16_api_probe.py` (authenticated lifecycle and bounded load); `backend/scripts/sprint1_restore_probe.py` (complete synthetic restore); `scripts/v16-acceptance.py` invokes restore after downgrade refusal. No applied migration bytes, collector version, RBAC catalog or authorization hook changed. No new scheduler/workload control.

Compatibility: clients that resend protected/unknown response fields on PATCH now receive422 instead of silent dropping. Supported ResourceManagementV2 editor sends explicit editable fields. Broader third-party/legacy-client compatibility remains unqualified.

## Actual verification

| Check | Actual outcome | Evidence |
|---|---|---|
| New unit/policy tests |5 PASS,0fail/error/skip |unit-final.log |
| Owned PostgreSQL regressions |56 PASS,0fail/error/skip |committed-lab/ownership.txt |
| Authenticated real HTTP |11 groups PASS; includes prior9 plus lifecycle and concurrent-load groups |committed-lab/api.json |
| Browser |Actual Chromium eight-step pipeline/draft/configuration/mobile/viewer flow PASS |committed-lab/browser.json and4 screenshots |
| Fresh/populated migrations |PASS, no model drift; unsafe populated downgrade refused |committed-lab/report.json, staging-preservation.txt |
| Complete synthetic backup/restore |100 tables identical; source unchanged; archive SHA and all table hashes retained |committed-lab/restore.json, synthetic-backup.dump |
| Bounded load |200 expected IDs,200 distinct persisted,200 physical rows,0missing/duplicates;20 authenticated reads. P50=73.831ms,P95=90.147ms,max409.783ms |committed-lab/controlled-load.json |
| Frontend Node helpers/source tests |38 PASS,0fail/skip; not mounted-component coverage |frontend.log |
| Focused Ruff |PASS |static.log |

Counts overlap; do not sum HTTP/browser/integration groups as unique tests. No formal UAT, genuine provider or release certification. The load producer writes synthetic MetricSample rows directly, not OTLP receipts; it cannot prove upstream durable admission or exactly-once delivery. No latency SLO was invented.

Reproduction (existing dependencies; Docker local engine/postgres17-alpine, API/Vite loopback, existing Playwright browser):

```sh
PYTHONPATH=backend backend/.venv/bin/python -m unittest tests.test_sprint_resource_lifecycle -v
V16_API_ACCEPTANCE=1 V16_BROWSER_ACCEPTANCE=1 V16_STAGING_PRESERVATION=1 PLAYWRIGHT_MODULE=/tmp/oc-closure-tools/node_modules/playwright/index.mjs PLAYWRIGHT_BROWSERS_PATH=/tmp/oc-etl003a-browsers V16_EVIDENCE_DIR=/tmp/oc-dev002-committed backend/.venv/bin/python scripts/v16-acceptance.py
npm test --prefix frontend
```

Failed attempts retained: attempt1.log import invocation failed because backend was absent from module path; attempt2.log new mock fixture lacked collector_type/configuration and caused two errors; fixture repaired without changing security checks. Intermediate lab-attempt1 and lab-final records9/10 groups; load-precommit adds11 before full restore. Committed-lab is final exact sourcea4aea63 and11 groups plus restore. No failure relabeled as a skip/PASS.

## Parallel bounded work

[SPOOL_TRANSACTION_CONTRACT.md](SPOOL_TRANSACTION_CONTRACT.md):201 reviewable admission/ack/lease/retry/retention/crash contract preserving centralized PostgreSQL. Accountable review remains pending; **101 NOT STARTED**.

[PARALLEL_REVIEW.md](PARALLEL_REVIEW.md):501 source/mixed-version boundaries,503 deterministic empty trusted-workflow mapping refusal (offline regression), protection-read403 evidence,123 security remediation prerequisites. No bypass or unapproved mapping enabled. Historical full publish logs unavailable; source blocker is reproducible, not asserted to be the sole historical cause. No independent security/license clearance.

## Cleanup and release boundaries

Harness finalizers removed only randomized task-owned PostgreSQL container/tmpfs and terminated owned API/UI processes. Restore clone dropped; synthetic backup preserved for review. No production or owner's UAT resources accessed; no broad Docker cleanup. No formal UAT, provider credential or workload execution, publication, deployment or merge. Prior worktrees and draft PR80/81 preserved. All nine owner selections Pending; historical controlled approvals unchanged. D07/D08 Pending; genuine Pentaho qualification BLOCKED. No OC-DEV-003 started.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
