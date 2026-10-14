# DOC-03 — Current-State Assessment
**Status:** Repository inventory only; runtime validation pending | **Date:** 2026-10-10

## Evidence and method
Inspected the `main` repository tree and sampled existing monitoring, Pentaho, alert and correlation documents. This is **not** a completed code audit or runtime test.

## Confirmed repository artifacts
- React/Vite frontend: `frontend/src/App.jsx`, pages `Overview.jsx`, `ETLJobs.jsx`, `ResourceManagement.jsx`, `ResourceManagementV2.jsx`.
- FastAPI backend: `backend/app/main.py`; API modules for organizations, resource management, monitoring, ETL and investigations.
- SQLAlchemy model module and Alembic migrations `0001` through `0011`.
- Worker modules for collectors, alert engine, credentials and notifications.
- Correlation and template resolution service modules.
- `.github/workflows/validation.yml`, `docker-compose.yml`, demo seeding script.
- Existing documentation: monitoring configuration, Pentaho collector, alert engine, correlation engine, metric samples, log events, API basic-auth collector and demo scenarios.
- Screenshot SVG assets in `docs/screenshots/`.

## Evidence matrix
| Area | Evidence observed | Functional verification |
|---|---|---|
| Organizations and isolation | API/model paths exist | NOT VERIFIED |
| Data source and resource UI | Two ResourceManagement page files exist | NOT VERIFIED |
| Collector scheduler | Worker module exists; design describes lifecycle | NOT VERIFIED |
| Templates and attachments | Template resolver and migrations exist | NOT VERIFIED |
| Metrics and logs | Models/migrations and documentation exist | NOT VERIFIED |
| Pentaho | Collector design document exists | NOT VERIFIED |
| Alerts/notifications | Worker modules and alert design exist | NOT VERIFIED |
| Correlation | Service and design document exist | NOT VERIFIED |
| CI and Docker | Workflow and compose files exist | NOT VERIFIED |
| UI screenshots | SVG screenshot assets exist | NOT VERIFIED against current UI |

## Known reported issues requiring reproduction
- Organization create/edit affordances and isolation behavior.
- Template activation into actual operational collector configuration.
- Resource Management redesign, totals-to-filtered-list navigation.
- Syntax, relationship and integration regressions following UI changes.

These are user-reported observations from project planning, not independently reproduced defects.

## Audit checklist for next iteration
1. Read routes, models, migrations, worker logic and frontend navigation in full.
2. Build a feature-by-feature inventory: implemented / partial / broken / missing / unverified.
3. Run backend tests, frontend build/lint, migrations and startup checks.
4. Exercise tenant boundary negative tests and template-to-sample flow.
5. Reconcile screenshots and README against the current UI.
6. Record evidence, reproduction steps and issues before modifying behavior.
