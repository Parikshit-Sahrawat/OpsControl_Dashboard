# PR #34 remediation verification

Review method: a second-pass source review of the existing F-01–F-03 fixes and new PostgreSQL/browser regressions. This records automated and code-review evidence; repository owners retain independent approval and merge authority.

| Finding | Code locations | Additional verification | Result |
|---|---|---|---|
| F-01 | `backend/app/data_pipelines/runtime.py:258` (`read_only_connection`), `:325` (`run_operation`); `service.reconcile_discovery` | Draft/unverified discovery, inactive/unauthorized actor rejection, incomplete inventory protection, revocation during provider I/O | Passed; no collection activation proof is inferred from inventory |
| F-02 | `backend/app/data_pipelines/service.py:292` (`reader_contract`), `:336` (`reader_equivalence`), `:444` (`check_ticket`); method add/edit/activate/apply in `api.py` | Equivalent bindings; differing credential references, endpoint, transport, query/step options and checkpoint schema; durable contract and API add/enable rejection; shared pause | Passed; mismatches fail closed and require the reviewed generation workflow |
| F-03 | `backend/app/data_pipelines/runtime.py:25` (`_source_failure`), `:77` (`run_source`), recovery selection in `tick` | Failed SQL transaction rollback, invalid recovery, stale source owner/fence, active replacement lease, replacement recovery operation fence, restart recovery, verification errors | Passed; no failed-preparation checkpoint progress or stale cleanup of replacement claims |
| Staging preservation | `backend/scripts/existing_database_upgrade_probe.py`, `cleanup_fixture` | Actual 0024→0016→HEAD populated migration; automatic dependent resource cleanup; unrelated organization retained; unexpected dependency rolls back the whole cleanup | Passed locally; current-head remote workflow outcome is recorded in the PR |

The cleanup checks only the explicitly identified disposable organization/source UUIDs and fixture code. It identifies API projections first and deletes those exact rows before their Data Source, in one transaction. It refuses ambiguous identities or unexpected resource bindings. No constraint is disabled, no CASCADE is added, and unexpected remaining references roll back all fixture deletion.

## Commands and results

```sh
V16_STAGING_PRESERVATION=1 V16_API_ACCEPTANCE=1 V16_BROWSER_ACCEPTANCE=1 \
  V16_EVIDENCE_DIR=/tmp/opscontrol-v16-remediation-evidence \
  backend/.venv/bin/python scripts/v16-acceptance.py
(cd backend && ENV=test .venv/bin/python -m unittest \
  tests.test_unified_monitoring tests.test_unified_v15_contracts \
  tests.test_pipeline_runtime_v15 tests.test_pipeline_adapters \
  tests.test_native_incidents_v15 tests.test_access_control tests.test_remote_auth \
  tests.test_pipeline_transport_v16 -v)
npm run lint --prefix frontend
npm test --prefix frontend
```

Local results: **48 actual PostgreSQL tests, 111 selected backend regressions, nine HTTP acceptance groups, six frontend authorization tests and the expanded real Playwright flow passed**. The browser lab's mandatory Vite production build succeeded before preview startup. Alembic head remains `0032_pipeline_ownership`; populated preservation, zero drift, empty downgrade/re-upgrade and populated downgrade refusal passed. No new migration was required.

Browser evidence covers connection/profile persistence, two independent methods, fixture-driven native discovery through the actual worker/database, explicit selection (the second discovered job remains unselected), confirmed source association, backend activation denial, scoped viewer inventory and direct 401/403/404 negatives. The vendor inventory is explicitly a controlled fixture, not live platform or runtime capability verification. Screenshots and machine-readable results are in [remediation](remediation).

Exact-head Docker verification and the remote `phase1-staging.yml` job are published in PR #34 after the source commit. Any committed Docker evidence identifies the tested commit and source manifest; later evidence-only commits do not change the application manifest. No merge or production deployment is authorized by these results.

## Follow-up CI regressions

The legacy job-order creation API flushed a VM projection before attaching its
validated host source. Its subsequent attempt to change that immutable binding
failed. The initial projection now receives the server-authorized source; two
PostgreSQL regressions prove initial creation succeeds while replacement and
cross-customer binding remain prohibited. No ownership guard or migration changed.

Existing browser gates were aligned with the actual V1.5 navigation and contracts:
API resource tabs and independent customer filtering; the removed Organization
Access UI remains absent while paired grants are exercised through authenticated
APIs; sensitive-action confirmations are accepted by the controlled test; async
locked-source loading is awaited; inventory expansion survives domain navigation;
resource PUTs retain required identity/configuration; and superseded fetch aborts
cannot erase newer inventory. The same-type File Log test now checks the two real
sources after adding the second, accounting for the fixture's preceding deletion.
No production UI or endpoint was added to satisfy these checks.

The restore fingerprint's exact approved CHECK list now matches the V1.5/V1.6
migrations, including incident statuses and pipeline source enums. It still rejects changed operators/values and compares every
other constraint byte for byte. Four focused unit tests reject modified values/operators and unvalidated checks,
while proving the documented cast rewrite is equivalent. This changes test
verification, not database constraints or incident behavior.

The API compatibility projection also recognizes the existing `HTTP` collector
type, allowing persisted remote probes to appear in unified reports. Two actual
PostgreSQL regressions prove first binding preserves customer/source identity,
does not activate monitoring, and never replaces an existing primary collector.
No reporting, event/alert, incident, SLA or correlation evaluation logic changed.
ETL browser selectors distinguish the execution table from the inventory table;
monitoring activation targets the embedded configuration panel. Theme tests
preserve expanded inventory state across repeated domain navigation.

The full local release gate passed populated backup/restore with every row
fingerprint, FK/CHECK integrity and audit trigger; retention, restricted runtime
roles, TLS, browser CRUD and inventory pagination. See `remediation/release-report.json`.
The first subsequent remote staging run could not pull the public ECR mirror
(`toomanyrequests: Data limit exceeded`); its PostgreSQL service now uses the same
official `postgres:17` image directly. No TLS verification or constraints were disabled.

`remediation/docker.json` records the completed exact-head five-service smoke for
`0a91418d462cf5ec846e3969857be1f8128cbeab`. Its 190-file image manifest covers both
API and worker. The final PR head is verified again after the remaining source
correction; its result is recorded in the PR to avoid a self-referential evidence
commit. Previously failed owned Docker smoke images were removed only from the
task's isolated VFS daemon, leaving 15.9 GiB free; original volumes and deployment
were preserved. This report does not treat an older source manifest as proof of
subsequent application changes.

The NOC report-denominator probe now retains its controlled executions and
collector projections until the owning disposable PostgreSQL container is
removed. It no longer deletes parent jobs/collectors referenced by retained
monitoring resources. This test-only change neither deletes customer records nor
changes runtime retention or FK constraints.

The complete local controlled Carte/Linux/NOC acceptance then passed all eight
ETL browser phases, configured/failure/recovery NOC browser checks, role/customer
negatives, alert relapse, stale evidence, audit attribution and report-denominator
checks. The theme browser reports 13 checks across desktop/mobile, both themes,
all primary tabs, contrast and session behavior, with zero page/server errors.
These are controlled local runtime results, not genuine vendor acceptance.
