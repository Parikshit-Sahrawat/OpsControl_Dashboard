# Sprint 1–5 acceptance reassessment

Reconciled 2026-10-11 against main `fbe83badb47ee61b81fe60f23dde48c37b1ee1d0`. GitHub API/PR creation is operational. Sprint 3 PR #23, Sprint 4 PR #24 and the approved UI PR #25 are merged. PR #25 passed sixteen head checks; post-merge [Validation](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/38165657701) passed. Earlier Forbidden/unmerged/pending-CI statements are historical and superseded. AWS Toolkit/live AWS setup remains paused.

| Sprint | Verified functional gate | Development state | Remaining acceptance |
|---|---|---|---|
| 1 HTTP | Actual synthetic TLS 200→503→200, scoped activation, pinned rules, same alert recovery, browser/DB/audit negatives | Merged; automated workflow passed | Operator UAT, deployment-specific egress/CA rotation |
| 2 Infrastructure | Live local Linux, AWS SDK-controlled responses, certificate-verified K8s fixture and controlled Windows; native metrics/alert recovery | Merged; controlled workflow passed; disposable K8s/Calico CI separately passed | Genuine AWS/CloudWatch/native Windows and customer-cluster acceptance |
| 3 ETL | Authenticated Carte-shaped TLS lifecycle, No Run/Long Running/SLA, logs/history, host correlation and investigation | PR #23 merged; synthetic workflow passed | Genuine Carte XML/timezone/history/read-only acceptance |
| 4 Operational UI | All primary tabs data-backed; incident/investigation/report/browser scope journeys; approved persistent dark/light UI | PR #24 and #25 merged; head/post-merge validation passed | Independent security review, operator UAT and target-volume usability |
| 5 Release candidate | Incremental security/migration checks; new isolated reliability fixes and populated restore/retention/TLS gate | In progress on separate reliability feature branch | See [priority matrix, fixes and release gates](RELEASE_RELIABILITY.md) |

Functional gates and development merges are established for Sprints 1–4. Independent human review is not inferred from owner merge approval or automated checks. Production rollout remains gated on Sprint 5 acceptance.

## Evidence

- [HTTP guide](HTTP_GOLDEN_PATH.md) and [HTTP reassessment](acceptance/sprint-reassessment/http-report.json).
- [Infrastructure guide](INFRASTRUCTURE_MONITORING.md) and [infrastructure reassessment](acceptance/sprint-reassessment/infrastructure-report.json).
- [Pentaho guide](PENTAHO_ETL_MONITORING.md) and [ETL runtime ledger](screenshots/etl/report.json).
- [Operational UI guide](OPERATIONAL_DASHBOARDS.md), [NOC runtime ledger](screenshots/operational/report.json), [approved UI change](../frontend/UI_TEST_1.md).

Every subsequent PR must record its own exact head checks, review, merge and artifacts. Earlier green checks do not validate later reliability changes. Genuine-provider and production gates stay explicitly pending.
