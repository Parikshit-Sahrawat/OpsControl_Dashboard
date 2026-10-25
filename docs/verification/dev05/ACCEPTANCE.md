# DEV-05.0 disposable product acceptance

**Overall result: FAIL — release blocked by saved API-setting reload defect.**

Application baseline: `f617cc653a965c2ad1bb7edf9e20237e40044b97`.
Branch: `test/dev-05-0-disposable-product-verification`.
The runner builds application source using `git archive` of that exact commit;
only the verification harness is overlaid. No application code, production
configuration, dependency declarations, migrations or existing tests were changed.
No production infrastructure, real customer endpoint or real credential was used.

The recorded final run has **20 PASS, 1 FAIL, 1 BLOCKED, 1 NOT TESTED** check groups.
These are check groups, not a fabricated aggregate test-case count. Machine-readable
outcomes, timings and artifact SHA-256 hashes are in [acceptance.json](evidence/acceptance.json).
The intentional failure run separately returns exit 1 by design and confirms cleanup;
it is not a product acceptance failure or a passing product run.

| Verification area | Observed result | Evidence |
| --- | --- | --- |
| Fresh PostgreSQL, all migrations, API and frontend startup | PASS | Service/build logs and image IDs |
| Synthetic users, tenants, built-in role grants, workers, versioned rules | PASS | Authenticated golden-path setup |
| Organizations, Data Sources, template draft → explicit activation → collector materialization → deactivation | PASS | Commands log |
| Real TLS GET healthy → HTTP 503 → recovered | PASS | `report.json`; metric/log/evidence rows checked in PostgreSQL |
| Alert lifecycle and identity | PASS | OPEN → RESOLVED on the same alert, persisted timestamps |
| Dashboard and diagnostics in all three phases | PASS | Three dashboard and three diagnostics screenshots; actual API response assertions |
| Playwright activation, idempotence, active configuration after reload | PASS | `configured.png` and phase logs |
| Real HEAD, approved header, latency bound and persisted evidence | PASS | Completed HEAD job, zero response body, HTTP 200, latency ≤ 10,000 ms |
| Saved request settings repopulate after reload | **FAIL** | `saved-api-settings.json`, screenshot and assertion failure |
| Live Linux process healthy → stopped → recovered | PASS | `infrastructure.json`: HEALTHY → CRITICAL → HEALTHY, history 1 → 2 → 3, alert recovery |
| Anonymous/human/invalid/revoked worker, forged heartbeat, cross-tenant assignment/result and unsafe activation requests | PASS | Authorization checks in commands log |
| TLS trust/hostname, host/CIDR policy, forbidden methods/headers, injection, URL credentials/query and latency failures | PASS | 22 checks in `worker-negatives.json` |
| Read-only synthetic Carte over real verified TLS | PASS | Existing `get_job_status` parser with controlled XML; not installed-build certification |
| Related existing backend regressions | PASS: 63 passed, 2 skipped, 0 failed/errors | `regressions.json`, exact module list and skip reasons |
| Existing frontend regressions, lint and build | PASS: 26 tests, 0 failed; lint/build passed | Commands log |
| Audit redaction/append-only, artifact credential scan | PASS | Golden report and raw artifact scan; no generated credential values found |
| Normal completion cleanup (despite product failure) | PASS | `evidence/cleanup.json` |
| Intentional post-start failure cleanup | PASS | `failure-cleanup/cleanup.json` |
| Genuine cloud/Windows/Pentaho provider certification | BLOCKED | No real targets or credentials authorized; not claimed |
| OpenTelemetry Contrib binary runtime checks | NOT TESTED (2 explicit skips) | Pinned Contrib binary not configured |
| Production deployment | NOT TESTED, strictly prohibited | No deployment commands or production configuration changes |

## Confirmed defect DEV05-001

The API monitoring form does not restore saved request settings after reload.

Reproduction on the exact baseline:

1. Sign in as the synthetic organization operator; open Fictional HTTPS Portal's
   legacy monitoring configuration.
2. Select the three version-1 rules, set method HEAD, maximum response time
   `10000`, and approved header value `dev05-ui`.
3. Validate/preview and activate. The real activation POST returns HTTP 200.
4. Reload the page and reopen the same resource configuration.
5. Observe method GET, empty maximum response time, and empty approved header.

Expected values are HEAD, `10000`, and `dev05-ui`. The test fails with
`Saved method must rehydrate after reload: 'GET' !== 'HEAD'`. Its JSON records
`"saved": true`, `"reloadedMethod": "GET"`, and both other fields empty.

The baseline `frontend/src/pages/MonitoringSetup.jsx` initializes these controls
to defaults and does not hydrate them from saved collector configuration. This
can mislead operators about the active check and risks replacing saved settings
with defaults during a later activation. The harness deliberately leaves this
assertion failing and does not change production application behavior. Fix the
form hydration in a separate product change, then rerun this same harness.

## Isolation, artifacts and cleanup

The stack has three internal Docker networks: database (API/PostgreSQL), control
(API/frontend/browser/worker), and target (worker/HTTPS fixture). It publishes no
host ports. The worker has no database route or database credentials; it receives
only its synthetic worker token and public fixture certificate. The browser
receives only synthetic UI login credentials. No container receives a host Docker
socket or real provider identity. Plain HTTP is used only for the isolated local
control plane/frontend; production control-plane TLS is not certified here.

[Evidence directory](evidence/) contains machine-readable reports, actual test
logs, nine synthetic-data screenshots, image IDs and a SHA-256 artifact manifest
inside `acceptance.json`. Screenshots show no secret values. Audit output is
checked before export; exported text is additionally redacted. Session files,
passwords and TLS private keys are never exported.

Both run projects report zero remaining containers, networks and volumes, Compose
exit 0, and removal of their synthetic secret directories. The pre-existing,
unrelated `opscontrol-dev-postgres` container remains untouched. Cleanup is scoped
to the unique Compose project and its labels. No broad Docker/container/image
prune was used. During harness development, only exact cache IDs belonging to
this task's abandoned large browser build were removed to recover VFS disk space.
Reusable image/build caches may remain; these are not running services.

The harness's early setup failures were diagnosed and corrected (internal proxy
settings, fixture mounts, VFS disk use and correct template activation semantics).
They are not reported as product defects. The final run uses Playwright 1.56.1,
Chromium 156.0.8078.47, Node 24.22.1, Python 3.12 and PostgreSQL 17.11; exact images
are recorded. System Chromium and image tags may advance on future rebuilds, so
use recorded image IDs when comparing runs.

## Remaining release gates

- DEV05-001 must be fixed and this failing browser check rerun successfully.
- The two Contrib runtime tests require the repository's pinned collector binary;
  their skips are not PASS results.
- Synthetic Pentaho/Carte and Linux evidence do not certify genuine Pentaho
  installations, EC2, Windows or Kubernetes. Kubernetes monitoring is deferred in
  this baseline; no live provider acceptance was attempted.
- No release-wide regression, performance/load, real notification delivery,
  production deployment or production control-plane TLS certification is claimed.
  Unrelated green CI workflows were not manually rerun.

Run instructions and the deliberate failure cleanup command are in
[the harness README](../../../verification/dev05/README.md). This change is for
review only; do not merge or deploy automatically.
