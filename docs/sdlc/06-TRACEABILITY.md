# DOC-06 — Requirements Traceability (Initial)
**Status:** Draft; implementation mappings are candidates, not verified.

| Requirement | Candidate implementation | Planned validation |
|---|---|---|
| FR-001 | `api/organizations.py`, `models/entities.py` | Organization isolation negative tests |
| FR-002 | `api/resource_management.py`, `pages/ResourceManagementV2.jsx` | CRUD and validation E2E |
| FR-003 | `worker/collector_runtime.py` | Schedule, failure and retry integration tests |
| FR-004 | `services/template_resolution.py`, migration 0010 | Template activation -> collector run -> evidence |
| FR-005 | `api/monitoring.py`, migrations 0005/0007 | Ingestion/query tests |
| FR-006/007 | `api/etl.py`, `docs/PENTAHO_COLLECTOR.md` | Pentaho adapter contract + synthetic run tests |
| FR-008/009 | `worker/alert_engine.py`, `worker/notifications.py` | Transition, dedupe, retry and mock-provider tests |
| FR-010 | `services/correlation.py`, `api/investigations.py` | Time/resource-scoped correlation tests |
| FR-011/012 | `pages/Overview.jsx`, `pages/ETLJobs.jsx` | Filtered drilldown UI tests |
| FR-013 | `docs/API_BASIC_AUTH_COLLECTOR.md`, worker modules | Adapter-specific integration tests |
| FR-014/015 | To be located/implemented | Audit and export tests |

## Risk register
| Risk | Severity | Mitigation |
|---|---|---|
| Cross-tenant data leakage | Critical | Server-side scoping and negative tests before production |
| Templates saved but not executed | High | End-to-end activation test and runtime health |
| Credential leakage | Critical | Secret references, redaction, scanning and least privilege |
| Alert storms / duplicate incidents | High | Idempotent transitions, delivery keys and bounded retries |
| Incorrect ETL failure classification | High | Separate source failures from collector/network outages |
| Stale UI counts / inconsistent filters | Medium | Scoped query contracts and navigation tests |
| Migration drift / regression | High | Fresh-db and upgrade-path CI tests |

## Approval checklist
- [ ] Release-1 scope and priorities agreed
- [ ] Role/tenant security model agreed
- [ ] Adapter and notification integration priorities agreed
- [ ] Data retention and availability targets agreed
- [ ] Current-state runtime audit completed
- [ ] Stakeholder sign-off recorded
