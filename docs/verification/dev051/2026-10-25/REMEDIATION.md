# DEV-05.1 / DEV05-001 remediation — 2026-10-25

**DEV05-001: FIXED in the recorded disposable verification.**
The exact previously failing Playwright assertions pass unchanged. The full run
returns `PASS_WITH_LIMITATIONS`, with **21 PASS, 0 FAIL, 1 BLOCKED, 1 NOT TESTED**
check groups. These are groups, not an invented combined test-case count.

- Issue: [#66](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/66).
- Original failed verification: [PR #65](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/65), untouched.
- Original product baseline: `f617cc653a965c2ad1bb7edf9e20237e40044b97`.
- Tested fix commit: **`77c9d8b15caf8304fe626f711c219a95fc4f297a`**.
- Original harness commit: `0e237026c7f1f293d2b0d0e8c94255ed4597c0dc`.
- Fix branch: `fix/dev-05-1-saved-api-settings-rehydration`.

## Root cause and change

Monitoring Setup initialized its API request controls to GET/defaults and reset
some controls on source changes, but never fetched the persisted active collector
configuration. The real worker continued using the correct persisted HEAD job
contract; worker execution was not the defect.

The form now reads the existing organization-authorized Data Source activation
endpoint to identify the canonical collector, then reads that collector through
`GET /api/v1/monitoring/collectors/{id}`. Its existing `CollectorOut` serializer
redacts configuration secrets. No new configuration-read endpoint was needed.
The activation response adds only persisted rule-version IDs and a template
selection flag. New activations store that flag; older plans infer it where
supported. No raw plan, credential value or worker token is added to the response.

The frontend copies only URL, GET/HEAD, status, timeout, latency, the approved
`x-opscontrol-check` header, worker ID and persisted rule/template selections.
It resets to defaults for absent/inactive/disabled collectors, checks collector
ownership, remounts the editor when organization/locked source changes, and guards
pending reads/actions against source changes and user edits. Configuration loads
once per source/reopen/deactivation; diagnostics polling does not hydrate the form.
Preview is invalidated on edits/context changes. Settings/rule controls become
available only after saved values are ready, preventing transient default values
or checkbox state changes during loading. Failed reads leave preview unavailable.

The HTTPS, method/header allowlists, worker protocol, egress policy, tenant
boundaries, and secret providers are unchanged. No migrations, deployment changes,
real customer endpoint or real credential were introduced.

## Before / after — actual unchanged Playwright assertions

| Assertion after save, full reload and reopen | Original PR #65 | Tested fix |
| --- | --- | --- |
| `reloadedMethod == HEAD` | GET — FAIL | **HEAD — PASS** |
| `reloadedLatency == 10000` | empty — FAIL | **10000 — PASS** |
| `reloadedHeader == dev05-ui` | empty — FAIL | **dev05-ui — PASS** |

See [saved-api-settings.json](evidence/saved-api-settings.json), the
[actual screenshot](evidence/saved-api-settings.png), and
[runner output](evidence/commands.log). `saved` is true and the activation returned
HTTP 200. Other screenshots show dashboard alerts, diagnostics, configured and
other-tenant views with synthetic data only.

## Tests and execution

| Check | Recorded outcome |
| --- | --- |
| Existing + focused frontend unit regressions | **36 passed**, 0 failed (10 focused hydration/async tests) |
| Frontend lint and production build | PASS |
| Relevant backend activation, authorization, API configuration/worker and credential-reference tests | **30 passed**, 0 failures/skips |
| Unchanged DEV-05.0 disposable Docker harness | **21 PASS**, 0 FAIL, 1 BLOCKED, 1 NOT TESTED groups |
| Exact saved API settings Playwright regression | PASS |
| Browser activation/reload, GET health/failure/recovery, persisted evidence, alert identity and dashboard | PASS |
| Real HEAD, approved header and latency persistence | PASS |
| Organizations, Data Sources, template activation, collectors, live Linux process lifecycle | PASS |
| Worker/tenant authorization, append-only audit and secret scan | PASS |
| Real TLS/egress/method/header/latency negatives and synthetic Carte | **22 passing checks** |
| Existing scoped backend contracts inside Docker | **63 passed**, 2 explicit skips, 0 errors/failures |
| Frontend checks inside Docker | **36 passed**, lint/build PASS |
| Project cleanup | PASS |

The focused tests exercise persisted values and defaults, absent/disabled
activation, ownership/permission failures, pinned selections, out-of-order reads,
source cancellation, edit preservation, preview invalidation, and publishing
saved values before enabling controls. Organization changes use a keyed editor
remount; embedded locked-source reopening is exercised by the actual browser
harness. No claim is made that every edge case has a separate browser scenario.

The separate [DEV-05.1 adapter](../../../../verification/dev051/README.md) extracts
PR #65's immutable harness outside the checkout and overrides only the in-memory
product archive SHA with an explicit committed fix. Original assertions and runner
files are byte-identical. [Provenance](evidence/remediation-provenance.json) records
the baseline/fix/harness SHAs and verifies every original harness file hash.
The original runner's default baseline-pinned behavior and all PR #65 evidence
remain unchanged. No unrelated green CI workflow was manually rerun.

Two earlier remediation iterations failed on newly exposed loading races: a
checkbox changed while Playwright was checking it, and a value read observed a
loading default before the canonical request completed. Atomic availability of
rules/request controls fixed these races. Their actual failed logs, values,
revision provenance and successful cleanup records remain under [attempts](attempts/);
they are not counted as passes. All other product checks passed in those runs.

## Cleanup and retained artifacts

The final project `dev05-0b26f04e55` was cleaned up after evidence export.
[cleanup.json](evidence/cleanup.json) records Compose exit 0, zero remaining
containers, networks and volumes, and removal of the synthetic secret directory.
Both earlier failed projects also report successful cleanup. Only exact Compose
project resources were removed. No broad Docker cleanup command was used.
Image/build caches may remain; no running verification service or synthetic secret
is retained. No production deployment or PR merge was performed.

[evidence](evidence/) contains generated acceptance JSON, redacted logs, synthetic
screenshots, image IDs and unit-test logs. [artifact-sha256.json](artifact-sha256.json)
records the preserved evidence/attempt file hashes. Original runner artifact hashes
were independently checked after copying. Raw artifact credential scans passed.

## Remaining limitations

- Two existing Contrib-binary runtime tests remain **SKIPPED / NOT TESTED** because
  the pinned Contrib binary is not configured. They are not passing tests.
- Genuine Pentaho/cloud/Windows/Kubernetes provider certification remains
  **BLOCKED** without approved real targets/identities; synthetic tests do not
  establish live certification. Kubernetes monitoring is deferred in this baseline.
- Production deployment remains **NOT TESTED and prohibited**. Production control
  plane TLS, load testing and real external notification delivery are not claimed.
- No remaining failed check blocks this specific DEV05-001 remediation. Review and
  release-wide acceptance decisions remain with the owner; no automatic merge.
