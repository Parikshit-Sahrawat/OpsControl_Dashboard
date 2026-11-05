# Test And Owner Acceptance Matrix

Baseline: PR #80 source `e69528ad2b826398474382f34126feeca740f6a6`; main/merge-base `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`. Working branch `dev/post-pr78-architecture-closure-20261105`. Assessment date: 2026-11-05. Source presence, controlled verification, genuine-provider certification and owner acceptance are separate dimensions. No product code or migration is changed by OC-ARCH-001.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.** Journey 20 Service Catalog excluded; Journey 32 Kubernetes/container observability skipped. No provider execution, scheduler writes, job retry/termination controls, merge or deployment.

## New execution at the baseline SHA

| Check | Command | Result | What it proves / does not prove |
|---|---|---|---|
| ETL foundation | `cd backend && .venv/bin/python -m unittest discover -s tests -p test_etl_workflow_foundation.py -v` | 16 PASS, 0 FAIL, 0 SKIP; exit 0 | Schema validation, models, mocked route permission/update safeguards. No real request scope, database, migration or browser coverage. evidence/etl-foundation.log |
| ETL Clear filters | `cd frontend && node --test scripts/etl_filters.test.mjs` | 2 PASS, 0 FAIL, 0 SKIP; exit 0 | Source-pattern assertions for four defaults / All environments; not browser execution. evidence/etl-filters.log |
| Actual shared write hook | `evidence/reproduce_scope_gap.py` from backend | FAIL integration behavior: both new models denied 403 | In-memory SQLAlchemy Session calls actual before_flush handler with synthetic admin; no DB/HTTP. Output evidence/workflow-scope-probe.json. Probe exits 0 to report observations, not product PASS. |
| Documentation | `python docs/architecture/unified-implementation-baseline/validate.py` | See VALIDATION.json | File/link/ID/coverage/checksum checks; no runtime acceptance inferred. |

Initial setup had a mistaken relative Python version-check path (exit 127); correct backend .venv command above ran successfully. Initial GitHub search lacked a required type qualifier (422), then was repeated with is:issue/is:pull-request; raw scoped search results retained. No repository code was changed for those tooling errors.

## Required next acceptance boundaries

| Requirements | Controlled execution still required | Owner/provider acceptance |
|---|---|---|
| ETL-01–04/16 | B01/B02 authenticated HTTP + PostgreSQL + 0039 preservation, authorization, audit, DAG race | Product/backend/security owner reviews exact evidence, not just mocked guard calls |
| ETL-05–08/14 | Stable native source IDs, mutable row terminal transition, late updates, independently persisted receipts, restart/retention/fencing | Provider owner authorizes exact build/schema; independent reviewer certifies only executed methods |
| ETL-09–13 | Effective policy version snapshots, event/alert lifecycle, missing data, dedup/outbox/recovery and channel negatives | Product approves unresolved catalog/channel/override details first |
| ETL-15 | Actual browser Workflow→Job editor, persistence, errors, narrow roles and tenant switches | Owner UAT after integration; filter source test is insufficient |
| V1.6 A1–D5 / RT-001–020 | Use approved reconstructed index from ARCH_ETL_001_V16.md; retain exact source/method/build/customer/generation/hash/expected/actual evidence | Genuine installed CLI/Server/Carte runtime plus independent approval; no mocked certification |
| LIC-001–008 | Cryptography/offline/grace/identity and licensing-specific authorization tests after contract decisions | Accountable product/security/license owner; no invented signoff |
| 30 missing journey definitions | No executable acceptance criteria invented | Recover signed-off numbered source before allocating behavior |

Each acceptance record requires immutable source SHA, schema revision, method/build, environment, sanitized fixture hash, command, exit, passed/failed/skipped count, log/screenshot, persisted evidence, cleanup and reviewer decision. Distinguish BLOCKED approval/provider access from FAIL behavior and NOT TESTED. No owner signoffs supplied for this task.

PR78 historical tests at fa3a9a24107f465dac6692b2a9ea69b910ff06ee: 552 backend, 38 frontend, controlled HTTP/browser and restoration results are retained in docs/verification/stage-2a-full-development-closure. They predate PR80 migration 0039 and do not certify it. No full backend, browser, PostgreSQL migration, provider, load or collector reliability suite was executed in this documentation-only baseline task. Existing nine owner cases remain linked there, not replaced by CI.



## Follow-on disposition: OC-ETL-003 (2026-11-05)

Source `f57153836615fb07d748ede6b49af6a11dba96fe` closes the bounded CF-02 populated-foundation rollback and CF-03 supported HTTP concurrent graph risks with controlled PostgreSQL evidence: [report](../../verification/oc-etl-003/REPORT.md), [rollback contract](../../verification/oc-etl-003/ROLLBACK_COMPATIBILITY.md), [concurrency acceptance](../../verification/oc-etl-003/CONCURRENCY.md). ETL-01 workflow/job foundation and dependency integrity, inherited §10 evidence preservation, and backlog B01/B02 now have 84 passing regression tests plus six migration/recovery groups. Per-workflow serialization and shared authorization-reader locking preserve exclusive revocation protection. Applied migrations are unchanged. Prior rows remain historical baseline observations. This does not complete the remaining workflow UI, policy evaluation or provider work, certify every historical downgrade, or recover missing numbered journey authority. Owner acceptance remains pending; all release gates remain unchanged.
