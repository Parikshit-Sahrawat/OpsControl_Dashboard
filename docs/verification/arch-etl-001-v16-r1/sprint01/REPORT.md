# R1 Sprint 01 focused verification

Controlling source: [ARCH-ETL-001 V1.6](../../../architecture/ARCH_ETL_001_V16.md),
publication commit `ce603a4d298f6871821818e1f0d4fa101bad46a4`.
Source README: `cab0e63c8869c0c8830c4cb0e503ac45c6e38892`.
Canonical SHA-256: `ed8af0f9c3fce3375d0375e2431bdf43567133943551b2c0bc9f0b9882ab5446`.
This report covers Sprint 01 foundations, not complete R1 behavior or runtime certification.

## Executed commands and results

```sh
cd backend
ENV=test .venv/bin/python -m unittest \
  tests.test_pentaho_surface_contracts tests.test_pipeline_adapters \
  tests.test_pipeline_runtime_v15 tests.test_access_control \
  tests.test_in_app_notifications tests.test_native_incidents_v15 -v
cd ..
V16_API_ACCEPTANCE=1 V16_EVIDENCE_DIR=/tmp/arch-etl-r1-sprint01-integration \
  backend/.venv/bin/python scripts/v16-acceptance.py
backend/.venv/bin/black --check backend/app/pipeline_adapters/pentaho_contracts.py \
  backend/app/pipeline_adapters/__init__.py backend/app/data_pipelines/api.py \
  backend/tests/test_pentaho_surface_contracts.py
backend/.venv/bin/ruff check --select E9,F63,F7,F82 \
  backend/app/pipeline_adapters/pentaho_contracts.py \
  backend/app/pipeline_adapters/__init__.py backend/app/data_pipelines/api.py \
  backend/tests/test_pentaho_surface_contracts.py
backend/.venv/bin/python -m compileall -q backend/app/pipeline_adapters \
  backend/app/data_pipelines/api.py backend/tests/test_pentaho_surface_contracts.py
git diff --check
```

| Check | Result | Meaning / limits |
| --- | --- | --- |
| New and existing focused unit tests | 69 passed, 0 failed, 0 skipped | Six new static contract tests plus 63 adapter/runtime/RBAC/inbox/incident regressions; controlled fixtures are not genuine providers |
| Actual PostgreSQL suite | 48 passed, 0 failed, 0 skipped | Existing source ownership, fencing, checkpoints, holds, tenant constraints, discovery and compatibility regressions |
| Actual HTTP integration | Nine groups passed | Existing authenticated draft, multi-job, association, activation-denial and RBAC paths; no live vendor access |
| Disposable migration/schema checks | Passed | Populated 0031→0032 preservation, empty roundtrip, populated downgrade refusal and zero drift; no migration introduced |
| Python imports/model/API registration | Passed | Existing catalogue and `/api/v1/unified/pipeline-platforms/{platform}` routes registered; model mappers configured |
| Black, Ruff correctness, compilation and whitespace | Passed | Scoped files only |
| Authority/reference consistency | Passed | Canonical byte/hash match; REC-01–REC-12 each mapped once; 27 referenced implementation paths exist; local Markdown references resolve |
| Genuine Pentaho runtime RT-001–RT-020 | NOT RUN (all 20) | Requires installed builds, genuine native evidence and independent approval; no result inferred from metadata/unit tests |
| Frontend build/browser | Not run this sprint | Frontend code is unchanged; no UI implementation or browser acceptance claimed |
| Full external integration, load and production acceptance | Not run | Outside the Sprint 01 foundation; no production connection or deployment |

The import/route check uses the actual existing `pipeline-platforms` route; an
initial diagnostic expected `platforms` and was corrected after inspecting route
registration. This was a probe-path error, not an application route change.

## Executable contract coverage

`test_pentaho_surface_contracts` verifies three read-only surfaces, conservative
implemented/proposed states, all runtime flags false, independent exact-build
requirements, JSON serialization and fresh descriptors, unchanged descriptions
for the other eight platforms, unchanged runnable Pentaho adapter/connection
validation, required catalogue permission and unverified version candidates.

No execution reducer, evidence/notification/incident state machine, RBAC resolver,
retention cleanup, collection ownership, migrations or frontend was changed.
No new table, permission key or provider-control endpoint was added. The new
metadata is not consumed by runtime eligibility and cannot certify or activate
an unimplemented adapter. Kernel/OS/Pentaho version compatibility remains unverified.

Logs: [unit](unit.txt), [PostgreSQL](ownership.txt), [HTTP](api.json),
[integration runner](integration.txt). Private fixture credentials and service
failure logs are not included.
