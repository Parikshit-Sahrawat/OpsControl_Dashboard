# ARCH-ETL-001 V1.6-R1 — Sprint 02

Branch: `feat/arch-etl-001-v16-r1`; baseline `24e8684`.
Authority: [immutable specification](../../../architecture/ARCH_ETL_001_V16.md).
[Prior milestone](../sprint01/REPORT.md). No PR, merge, deployment, production
access, live source activation or genuine provider acceptance was performed.

## Delivery and capability boundaries

This sprint delivers executable read-only observation normalization, an opt-in
scoped Carte reader and existing collection integration. It **does not complete
all three native producer integrations**. Every surface remains PARTIAL and
runtime-unverified. Static descriptor revision is now 2; observation schema is 1.

| Surface | Implemented and locally tested | Documented / unverified | Unsupported or unknown |
| --- | --- | --- | --- |
| Kitchen/Pan | Resource-bound structured process-start, process-exit and invocation-bound native-result observations; job/transformation distinction; Windows/Linux OS validation; executable hash and optional scheduler identity provenance; arguments retained only as a hash/count | Exact installed binary/native-log identity, invocation capture and native result authority need real evidence | No automatic OS-native process probe or arbitrary log parser; no installer changes, native Windows acceptance, retry grouping, workload execution/control or completion inferred from exit alone |
| Pentaho Server | Authenticated structured repository, scheduler and execution-history export handling; native IDs scoped to authority/environment/customer; repository/scheduler claims retained without execution projection | Authorized native export mapping, repository identity, credential privileges and exact-build result semantics | No universal Server HTTP endpoints, database queries or authenticated export producer are invented. Network collection deliberately returns `UNSUPPORTED_CAPABILITY` until exact-build API/auth/schema evidence is supplied |
| Carte | Pinned TLS GET reader for fixed `/kettle/status/`, `/kettle/jobStatus/`, `/kettle/transStatus/`; bounded DTD/entity/alternate-encoding rejection; explicit execution-ID checks; job/transformation roots; conservative result handling; server/restart-epoch-scoped IDs; unchanged-response checkpoints and epoch mismatch rejection | Each endpoint, XML schema, Basic Auth privilege, exact installed build and stable job-to-execution mapping require independent native runtime proof | Inventory never becomes persistent authoritative discovery. Restart epoch is operator-supplied, not automatically detected; no continuity proof across restart, R1 bounded replay, transformation-step schema or automatic execution discovery |

CLI and Server observations use **existing FILE_LOG/AGENT transport**, not a new
canonical execution model. A read-only, authorized producer must supply the
versioned structured observations. Schema acceptance does not prove that producer
actually observed Pentaho. Native raw artifacts referenced by hashes must be
available separately for independent certification; the schema is not a native
Pentaho log/API format and cannot substitute for native evidence capture.

The legacy Carte adapter/configuration remains unchanged when `monitoring_context`
is absent. Existing legacy limitations remain; its support does not certify R1.
The other eight adapter classes, their accepted fields and execution semantics are
unchanged and covered by the existing adapter regression suite.

## Configuration and integration

Use existing integration connection versioning and method `adapter_overrides`.
An optional `monitoring_context` object selects the R1 contract. For example,
this is a **configuration example**, not a known installed or certified build:

```json
{
  "monitoring_context": {
    "version": 1,
    "surface": "KITCHEN_PAN",
    "exact_build": "10.2.0.0-222",
    "authority_id": "controlled-host-installation",
    "environment": "TEST",
    "workload_kind": "JOB",
    "native_job_id": "operator-confirmed-native-guid",
    "host_resource_id": "4d24797e-fd9b-4d8b-b5e3-9478aca07687"
  }
}
```

Surfaces: `KITCHEN_PAN`, `PENTAHO_SERVER`, `CARTE`. Workloads: `JOB` or
`TRANSFORMATION`. Exact-build syntax accepts a four-part version with optional
build suffix; families/unknown values fail closed. Syntax does **not** establish
installed-build detection or version compatibility. Other genuine vendor build
formats require explicit compatibility work, not guessed acceptance.

CLI requires FILE_LOG on the inherited host. Server exports also require FILE_LOG
and an authorized source-bound Agent. They need no fictitious network URL.
Carte requires PLATFORM_API/BACKEND and the existing URL, job-name, independent
worker/customer egress allowlists and optional managed Basic Auth reference.
Its context also requires `restart_epoch`. Explicit execution configuration and
confirmed native identity must be supported by genuine evidence; display names
alone do not prove a persistent job identity. Inventory-only reads are advisory,
return no execution events and never mark collection complete.

The Agent transport accepts JSONL records shaped as
`{"pentaho_observation": {...}, "evidence_origin": "..."}`. Observations repeat
connection scope/build fields and include `native_execution_id`, `observation_id`
and timezone-aware `observed_at`.

CLI adds `host_resource_id`, `os`, `executable_kind` (`KITCHEN`/`PAN`),
`executable_sha256`, `invocation_id`, `process_start` and `state`:
`PROCESS_STARTED`, `PROCESS_EXITED` or `EXECUTION_RESULT`. Optional `argv` is
hashed and discarded before persistence. Exit alone yields UNKNOWN, never SUCCESS.
A native result needs matching invocation, `NATIVE_STRUCTURED_LOG` provenance,
artifact SHA-256, terminal result and source end time. Optional scoped scheduler
IDs are preserved as observations; they do not group retries in this sprint.

Server exports add `authority` (`REPOSITORY`, `SCHEDULER`, `EXECUTION_HISTORY`),
`source_evidence_sha256` and source result/times where actually known. Only
execution-history authority can assert an execution result. Non-execution claims
have no routable job ID and are retained through existing identity quarantine.
Scheduler/repository-only observations therefore cannot supply the execution
identity proof required by the existing activation gate; execution history/native
outcome evidence is required separately. An authorized producer must map genuine Server fields; no undocumented mapping
is built into this sprint.

Existing routes handle all changes: versioned `/api/v1/data-pipelines/integrations`
connections/methods, capability verification and source lifecycle; authenticated
`/api/v1/agent/pipeline-claim` and `/pipeline-evidence`. No new API route, customer
identity, execution/incident model, migration, permission or frontend flow exists.

## Durability and security

- Native identity hashes include customer, surface, authority, environment,
  workload, stable job and native execution. CLI adds host/start epoch; Carte adds
  restart epoch. PID, name, nearby time and exit code cannot establish completion.
- Existing source lock, reader-equivalence hash, generation, fence, lease, holds,
  customer-bound Agent and confirmed source/job association remain authoritative.
- Backend normalization runs after ticket validation and inside evidence/checkpoint
  acceptance. Invalid scope, OS, generation, schema or normalized-event bypass
  leaves evidence/checkpoints unchanged. Unknown job identity remains quarantined.
- Caller events cannot override raw observation normalization. Raw command
  arguments are not retained. Credential references and existing redaction apply;
  source producers must still avoid secrets in unstructured logs/identifiers.
- New profile verification checks exact-build/surface proof before changing its
  label; runtime eligibility repeats that check plus existing independent native
  proof, reader hash, source generation and method gates. Metadata cannot certify.
- R1 observation replay is explicitly unsupported until range/continuity proof is
  implemented; legacy replay behavior is preserved. No live/recovery cursor is
  shared or silently reset. No new retention/deletion operation is added.
- Existing V1.5 reducers, retry/recovery reconstruction, conflict reconciliation,
  incident behavior, schedules, alerting, retention and legal holds are unchanged.

## Changed files

- `backend/app/pipeline_adapters/pentaho_observations.py`: context, scoped identity,
  CLI/Server normalization, transactional bridge, method/proof checks.
- `backend/app/pipeline_adapters/pentaho_carte.py`: allowlisted reader/parser and
  conservative, epoch-bound status checkpoints.
- `backend/app/pipeline_adapters/native.py`: opt-in R1 delegation; legacy fallback.
- `backend/app/pipeline_adapters/{__init__,pentaho_contracts}.py`: optional object
  schema and conservative partial capability declarations.
- `backend/app/data_pipelines/{api,bridge,service,transport}.py`: validation,
  customer binding, capability proof, fenced normalization and raw JSONL transport.
- `backend/tests/{test_pentaho_r1,test_pentaho_surface_contracts,test_pipeline_transport_v16,test_pipeline_ownership_v16}.py`:
  new and updated deterministic/security/durability regressions.
- `ARCH-001_IMPLEMENTATION_STATUS.md` and this evidence directory: delivery status.

## Executed checks

```sh
cd backend
ENV=test .venv/bin/python -m unittest \
  tests.test_pentaho_r1 tests.test_pentaho_surface_contracts \
  tests.test_pipeline_adapters tests.test_pipeline_transport_v16 \
  tests.test_pipeline_runtime_v15 tests.test_access_control \
  tests.test_in_app_notifications tests.test_native_incidents_v15 -v
cd ..
V16_API_ACCEPTANCE=1 V16_EVIDENCE_DIR=/tmp/arch-etl-r1-sprint02-final \
  backend/.venv/bin/python scripts/v16-acceptance.py
backend/.venv/bin/black --check backend/app/pipeline_adapters/{pentaho_observations,pentaho_carte,pentaho_contracts,native,__init__}.py \
  backend/app/data_pipelines/{api,bridge,service,transport}.py \
  backend/tests/{test_pentaho_r1,test_pentaho_surface_contracts,test_pipeline_transport_v16,test_pipeline_ownership_v16}.py
backend/.venv/bin/ruff check --select E9,F63,F7,F82 \
  backend/app/pipeline_adapters backend/app/data_pipelines \
  backend/tests/{test_pentaho_r1,test_pentaho_surface_contracts,test_pipeline_transport_v16,test_pipeline_ownership_v16}.py
backend/.venv/bin/python -m compileall -q backend/app/pipeline_adapters backend/app/data_pipelines backend/tests/test_pentaho_r1.py
# In backend: ENV=test .venv/bin/python -m alembic heads
git diff --check
```

| Check | Actual result / limit |
| --- | --- |
| Focused unit/security/adapter/compatibility tests | 110 passed, 0 failed, 0 skipped; includes 27 new R1 deterministic cases and existing eight-platform regressions |
| Actual disposable PostgreSQL | 56 passed, 0 failed, 0 skipped; includes eight new R1 acceptance/scope/proof/OS/projection cases |
| Actual isolated backend HTTP acceptance | Nine existing groups passed: drafts/methods/associations, activation denial, authorization, isolation, legacy compatibility |
| Migration upgrade/downgrade/schema | Passed populated 0031→0032 preservation, empty roundtrip, populated downgrade refusal, zero drift; head remains `0032_pipeline_ownership`; no new migration |
| Imports, model mappers, route registration | Passed using actual catalogue and Agent ingestion routes |
| Black, Ruff correctness, compile, whitespace | Passed scoped checks |
| Authority integrity | Approved specification unchanged; SHA-256 `ed8af0f9c3fce3375d0375e2431bdf43567133943551b2c0bc9f0b9882ab5446` |
| Genuine Pentaho RT-001–RT-020 | All 20 NOT RUN; no live vendor environments accessed and no runtime certification |
| Frontend/browser, full stack image rebuild, native OS installers | NOT RUN; unchanged frontend/Dockerfiles/installers, no new UI or native installation claim |

The database/HTTP pass covered final ingestion/eligibility changes. The subsequent
profile-label guard was tested directly through the API function with deterministic
fixtures and included in the final unit pass; it is not a genuine attestation.
Initial local failures (egress error classification and an incomplete API test
fixture) were corrected; no failure or skipped test was suppressed.

Logs: [unit](unit.txt), [PostgreSQL](ownership.txt), [HTTP](api.json),
[migration summary](migrations.json), [integration runner](integration.txt).
Private fixture credentials/service logs are excluded.

## Remaining evidence and next sprint

Supply exact installed Pentaho builds and approved, read-only native source
artifacts before implementing/certifying Server endpoints, automatic process/log
producers or build-specific Carte detail/step schemas. Automatic server restart
epoch discovery and bounded provider continuity/replay remain unverified.

Sprint 03 can build logical executions/attempts/retry/recovery reconstruction on
the scoped evidence contract. Sprint 04 owns conflict-safe projections. These
semantics and new frontend workflows were deliberately not implemented here.
Stop after Sprint 02; independent review and genuine runtime acceptance remain
separate activities. No merge, deployment or PR authorization is implied.
