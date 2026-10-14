# Sprint 4 — operational dashboards and reports

Merged development slice: PR #24, followed by approved UI PR #25 on main `fbe83ba`. This slice replaces the remaining navigation placeholders with backend evidence. AWS Toolkit/live AWS setup stays paused. Local synthetic acceptance, independent review, remote CI, merge and production acceptance are distinct gates.

## Operator workflow

| Screen | Data and actions |
|---|---|
| Overview | Scoped ETL, infrastructure, HTTP and incident counts; all four KPI cards navigate; recent incidents open their investigation |
| ETL Jobs | Current executions, environment/status/search filters, source steps/logs/timeline, correlation and retained execution history |
| VM Health | Provider/health/search filters, clickable health counts, collector freshness, actual metrics, resource evidence, alerts and operational history |
| APIs | HTTP service health, search and clickable health filters, collector status/freshness, HTTP status/latency, stored runs and alert lifecycle drawer |
| Incidents | Search, source/status filters and clickable counts; source episode, acknowledgement, investigation, notes and operator closure; ETL and resource drill-downs |
| Reports | 1/7/30/90-day windows, HTTP sampled success, ETL runtime SLA, incident counts, filtered operational history, collector/execution drill-downs and JSON export |
| Resource Management | Existing organization-scoped sources, collectors and templates; the lab creates resources through these real APIs |
| Monitoring Setup | Existing versioned rule selection, scoped source activation and diagnostic evidence |
| Access Management | Platform-only users/memberships administration; ordinary users do not see this navigation item. Security audit evidence remains available through the admin API |

The shared organization selector is a display preference; server authorization remains mandatory. New pages reset their evidence on a scope change and cancel or discard obsolete requests. ETL refreshes also discard previous-scope responses. Drawers provide close/Escape handling and keyboard focus containment. VM and reporting timestamps display IST.

## Incident semantics

Migration `0021_operational_incidents` introduces `OperationalIncident` and append-only `IncidentActivity`. It backfills existing native metric AlertState episodes and ETL_MONITOR open/recovery events without inventing operator closure. Deterministic backfill IDs preserve identity when the migration is reapplied in the disposable test.

Workers project incident creation and source recovery in the same transaction as alert evidence. Each metric alert state or ETL open event owns one episode. Repeated collection does not duplicate episodes; relapse creates a new episode and preserves the closed one. Rule evaluation is serialized per metric rule; older observations cannot regress the most recently evaluated alert condition. A still-breaching value cannot resolve an existing alert merely because fewer samples remain in the consecutive-breach window.

Source condition is **ACTIVE → RECOVERED**. Operator workflow is **OPEN → ACKNOWLEDGED → INVESTIGATING → RESOLVED**, with ACKNOWLEDGED → RESOLVED allowed after recovery. Resolution requires source recovery. Recovery alone leaves the operator investigation open. Historical ETL failures and their separate execution investigations remain available after a successful run.

Viewers read evidence. Operators/org administrators act only in their own permitted organization; platform administrators act across organizations. Endpoint checks and ORM scope/FK integrity both apply. The signed-in username supplies activity attribution. Database triggers reject UPDATE/DELETE of incident activity, and the existing redacted security audit records successful and rejected API actions. Dashboard feeds omit HTTP response bodies and credential configuration. These are **local OpsControl incidents**, not a verified ServiceNow integration.

## Report definitions and limits

HTTP sampled success = successful runs / runs with SUCCESS or FAILED status, multiplied by 100. Other statuses are counted as unknown and excluded. This is a ratio of stored probes, **not time-weighted uptime**. Mean latency uses only recorded non-null latency values. First/last observations describe coverage, not continuous observation. Sources without runs contribute no observed success result.

ETL runtime SLA = terminal executions with MET / terminal executions with MET or BREACHED. Evaluation also requires source start/end times in order and a positive captured SLA budget. Running, No Run and unknown timing are excluded and shown explicitly. Job success/failure counts remain separate: a failed job can finish within its runtime budget. Reports use the execution detection time for the window; HTTP uses the run observation/start time. Incident counts use episode opening time and current operator status.

Report aggregates cover all persisted observations within the selected window, independently of UI row limits. Service/incident lists default to 200 and allow up to 500; truncation is disclosed. Service and job detail history defaults to 100, incident activity to the latest 200, and unified history shows the latest 100 events. Report windows are bounded to 90 days. The separate reliability feature adds service/incident/infrastructure paging, true inventory totals, service prefetch and bounded raw evidence maintenance. History pagination, complete fleet health aggregation, infrastructure query optimization, load acceptance, time-weighted SLOs and external incident delivery remain open; see [current matrix](RELEASE_RELIABILITY.md).

## Reproduce the virtual lab

Use the existing checkout; no worktree or live cloud credentials are required. Backend dependencies live in the Python virtual environment. Frontend dependencies and Playwright are installed from their existing manifests/pin:

```bash
python3 -m venv backend/.venv # only if missing
backend/.venv/bin/pip install -r backend/requirements-providers.txt -r backend/requirements-hosts.txt
npm ci --prefix frontend --no-audit --no-fund
npm install --prefix /workspace/.golden-tools --no-audit --no-fund playwright@1.56.1
export PLAYWRIGHT_MODULE=/workspace/.golden-tools/node_modules/playwright/index.mjs
export PLAYWRIGHT_CHROMIUM_EXECUTABLE=/usr/bin/chromium # cloud environment's system browser
backend/.venv/bin/python scripts/operational-acceptance.py
```

Docker and OpenSSL are required. The runner reuses the disposable ETL harness: PostgreSQL 17 on loopback **11432**, API **18800**, Vite **15174**, and a certificate-verified Docker HTTPS fixture bound to the machine's private interface **443**. Those ports must be free. On other machines install Playwright Chromium and omit the executable override if `/usr/bin/chromium` is absent. CI uses Playwright's installed browser.

To keep a routine rerun outside documentation, set `OPERATIONAL_EVIDENCE_DIR=/tmp/noc-evidence`. The runner generates protected random credentials/certificates, applies/reverses/reapplies migrations, bootstraps users, performs actual HTTPS remote-worker enrollment/activation/probing, authenticates read-only Carte collection, observes a real Linux process and drives Chromium through real password login. It cleans only its own containers/processes and does not touch the development database. Failed runs print the protected log directory for diagnosis; do not dump its credentials.

The HTTP sequence is **200 → 503 → 200**, followed by a second failure/recovery episode for relapse validation. The ETL sequence retains No Run, running, long running, SLA breach, failed, poll failed and recovered states. Backend checks include report denominators, pure read-only feeds, viewer/mixed-role/foreign-tenant/worker negatives, stale health, invalid transitions, immutable activity and audit evidence. The normal ETL runner stays usable without Sprint 4 hooks.

## Acceptance evidence

Local final run on **2026-10-11: PASS**, using the restored Python virtual environment, disposable PostgreSQL/TLS fixtures and real Chromium. The complete runner exited 0. All eight primary navigation tabs and the platform-only Access Management screen passed; no browser page errors or HTTP 5xx responses were observed. The local HTTP and six-resource infrastructure regressions also exited 0 after the alert-engine changes.

- Five actual HTTP requests: **200, 503, 200, 503, 200**; one incident per failure episode, source recovery and authorized operator closure preserved independently.
- Seven ETL phases, six retained executions and live Linux host correlation; the earlier failed execution remains investigable after recovery.
- Reports checked at 50% and 66.67% HTTP sampled success; terminal ETL runtime SLA 2 met / 0 breached / 4 excluded at recovery. Separate negatives verify missing timing, in-progress SLA, unknown HTTP results, a breached terminal result and out-of-window exclusions.
- Populated upgrade/downgrade/re-upgrade backfill passed twice: four archived episodes, six source activities, deterministic IDs and no invented operator closure.
- Anonymous/worker/viewer/mixed-role/cross-organization negatives, stale evidence, invalid active-source resolution, append-only UPDATE/DELETE denial and redacted audit history passed. The [runtime report](screenshots/operational/report.json) records 202 audit events.
- Four offline ETL/infrastructure/provider/deep-check probes and the frontend production build passed. Automated remote CI passed before the approved development merges.

**31 actual Playwright PNGs**: twenty NOC captures plus eleven ETL regression captures. These are produced by real password login and actual backend responses, without mocked browser APIs.

| Browser evidence | Capture |
|---|---|
| Overview KPIs | [Overview](screenshots/operational/overview.png) |
| ETL jobs and historical investigation | [ETL Jobs](screenshots/operational/etl-jobs.png), [incident → ETL](screenshots/operational/incident-etl-investigation.png) |
| VM health and operational evidence | [VM Health](screenshots/operational/vm-health.png) |
| HTTP configured / failure / recovery | [configured](screenshots/operational/apis-configured.png), [failed](screenshots/operational/apis-failed.png), [recovered](screenshots/operational/apis-recovered.png) |
| Viewer / operator incident workflow | [viewer](screenshots/operational/incidents-viewer-failed.png), [investigation](screenshots/operational/incident-operator-failed.png), [closed after recovery](screenshots/operational/incident-operator-recovered.png) |
| SLA report and source drill-downs | [Reports](screenshots/operational/reports.png), [execution history](screenshots/operational/reports-etl-history.png), [Carte collector history](screenshots/operational/reports-collector-history.png) |
| Configuration and admin tabs | [Resource Management](screenshots/operational/resource-management.png), [Monitoring Setup](screenshots/operational/monitoring-setup.png), [Access Management](screenshots/operational/access-management.png) |
| Scope-change race and tenant isolation | [organization switch](screenshots/operational/organization-switch.png), [other tenant](screenshots/operational/tenant-isolation.png) |
| Mobile service screen | [APIs](screenshots/operational/mobile-apis.png) |

Browser assertion ledgers: [configured](screenshots/operational/browser-configured.json), [failed](screenshots/operational/browser-failed.json), [recovered](screenshots/operational/browser-recovered.json). ETL runtime/security evidence: [ETL regression report](screenshots/operational/etl/report.json). Fresh separate regression reports: [HTTP](acceptance/sprint4-regression/http-report.json), [infrastructure](acceptance/sprint4-regression/infrastructure-report.json).

Actual browser artifacts are produced under `screenshots/operational/`, with the ETL regression in its `etl/` subdirectory. The redacted `report.json` and phase-specific `browser-*.json` record assertions and real browser versions. The [CI workflow](../.github/workflows/operational-acceptance.yml) reproduces the gate and uploads artifacts; remote execution is separately recorded.

Remaining gates: independent human security review, genuine provider/Carte acceptance, and the [Sprint 5 reliability/UAT release gates](RELEASE_RELIABILITY.md). This synthetic lab does not establish production readiness.

## Publication and review

PR #23 (ETL), PR #24 (operational dashboards) and PR #25 (approved UI) are merged. GitHub API/PR creation is working; the earlier Forbidden blocker is resolved. PR #25's sixteen head checks passed, and [post-merge Validation](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/38165657701) passed at main `fbe83ba` on 2026-10-11. Owner approval to merge is recorded separately from independent human security review, which remains pending.

The new reliability feature branch adds true inventory counts, paging and service prefetch; page-local health summaries/search and remaining infrastructure/history query bounds are explicitly listed in the [priority matrix](RELEASE_RELIABILITY.md). Its changes require their own head validation and review. AWS setup remains paused; controlled runtime evidence does not establish production acceptance.
