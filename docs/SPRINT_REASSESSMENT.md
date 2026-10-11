# Sprint 1–4 acceptance reassessment

Reassessed on 2026-10-11 after the controlled Sprint 4 implementation, on `feature/sprint4-operational-dashboards`. AWS Agent Toolkit and live AWS setup are explicitly paused at the user's request. Local verification does not establish production acceptance or independent review.

## Functional gates

| Sprint | Gate | Current evidence | Remaining acceptance |
|---|---|---|---|
| 1 — HTTP golden path | Complete scoped onboarding, rule activation, synthetic HTTPS collection and alert failure/recovery | PASS again: actual TLS 200 → 503 → 200; native database samples/logs; same alert resolution; authenticated browser journey; tenant/audit/egress negatives. [Reference guide](HTTP_GOLDEN_PATH.md), [fresh regression report](acceptance/sprint-reassessment/http-report.json) | Remote golden-path workflow status, independent branch review and merge are not established |
| 2 — Infrastructure | A real or controlled environment produces verifiable health evidence | PASS again: six resources, eighteen observations and fifty-four samples; six stable native alerts resolve; real Linux, actual AWS SDK stubs, authenticated TLS Kubernetes fixture and controlled Windows inputs; five browser captures and scoped negatives. [Guide](INFRASTRUCTURE_MONITORING.md), [fresh regression report](acceptance/sprint-reassessment/infrastructure-report.json) | Genuine AWS/Kubernetes/Windows remain pending; AWS live setup is deferred; PR review/merge/remote CI remain unverified |
| 3 — Pentaho ETL | Synthetic ETL lifecycle passes; genuine Carte separately recorded | PASS: seven runtime phases, six histories, eight condition transitions, source entries/logs, live host correlation, poll blindness, investigation lifecycle and eleven browser captures. [Guide](PENTAHO_ETL_MONITORING.md), [runtime report](screenshots/etl/report.json) | Genuine Carte explicitly PENDING; remote CI, independent review and merge not established |
| 4 — Operational UI/reporting | Every primary navigation tab is functional and browser-tested | PASS: all eight primary tabs plus platform Access Management; local incident lifecycle, collector/execution investigations, report denominators/history/export, scope races, populated migrations and security negatives; 31 actual captures. [Guide and ledgers](OPERATIONAL_DASHBOARDS.md). Fresh HTTP/infrastructure regressions also PASS | Remote CI, independent review and merge remain pending; GitHub API requests still return Forbidden |
| 5 — Enterprise release candidate | All release-candidate checks pass, production acceptance separate | Not complete. Auth/tenant/secret/audit negatives and disposable migration checks run incrementally | Independent security review, backup/restore/retention, load/resilience/reconnect/failover, deployment/UAT and formal release acceptance remain |

These results satisfy the local functional runtime gates for Sprints 1–4. The complete Definition of Done includes independent PR review and merge, so none is promoted to fully accepted/merged based only on local tests.

## Reusable Definition of Done

| Requirement | Sprint 1 | Sprint 2 | Sprint 3 | Sprint 4 |
|---|---|---|---|---|
| Implementation committed on feature branch | `fb036f5` | `5033221`, follow-up `c3d68ab` | `084bea3` on `feature/sprint3-pentaho-monitoring` | `feature/sprint4-operational-dashboards` |
| Backend and frontend automated checks | Local gates PASS; previous baseline CI evidence separately recorded | Local gates/build PASS | Local ETL/provider/schedule tests, security/remote trust probes and build PASS | Local complete virtual-lab gate, four offline probes, frontend build and HTTP/infra regressions PASS |
| Security and cross-org negatives | PASS | PASS | PASS | PASS, including mixed-role and scope-race negatives |
| Real or synthetic runtime evidence | Actual synthetic HTTPS | Live Linux + controlled provider environments | Actual authenticated synthetic Carte HTTPS + live Linux | Actual synthetic TLS HTTP/Carte + live Linux |
| Actual browser screenshots | Five reference captures; fresh regression captures also generated | Five reference captures; fresh regression captures also generated | Eleven committed captures | 31 actual PNGs (20 NOC + 11 ETL) |
| README, roadmap and architecture | Updated | Updated | Updated, with separate genuine Carte and reassessment ledgers | Updated with precise report definitions, evidence and pending gates |
| PR review and merge after validation | Not established for sprint branch | Branch published; draft PR API previously Forbidden; review/merge pending | Branch pushed; draft PR creation returned GitHub API Forbidden; review/merge pending | Native Git publication; GitHub API Forbidden; independent review/remote CI/merge pending |

## Findings resolved during reassessment

1. Carte had fixed-execution reads but lacked retained inventory ingestion and operational No Run/runtime SLA evidence. Sprint 3 adds those paths; genuine XML/timestamp/retention compatibility stays separate.
2. Investigation GET created records and could fail for viewers. It now reads only; writes occur through authorized transitions/notes.
3. Submitted operator names could misrepresent the actor. Transitions and notes now use the authenticated username.
4. First correlation creation flushed a missing required summary, rolling back source ingestion. The creation path now populates the summary before flushing; the actual failure fixture and operator reanalysis exercise it.
5. The ETL frontend filtered out non-PROD executions before its environment selector and left recent history empty. The API supplies scoped current records across environments; the drawer now reads real steps, logs, timeline, condition history and historical execution drill-downs.

## Next development target

The Sprint 4 local synthetic gate is complete. Proceed to Sprint 5 independent security review, backups/restoration/retention, load/resilience/reconnect/failover, deployment and UAT when authorized. Complete the still-pending PR review/merge gates before representing the development work as accepted. Live provider setup can resume independently when the user chooses; no AWS credentials or infrastructure provisioning are required to continue controlled development.
