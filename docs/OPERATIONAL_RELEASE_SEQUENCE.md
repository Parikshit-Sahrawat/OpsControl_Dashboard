# Ordered operational release implementation (2026-10-12)

Requested order: stabilization, template activation, telemetry, alerting/correlation, EKS/deployment/release. Baseline main `277ec2c` already includes the controlled HTTP/infrastructure/ETL/NOC architecture and reliability PR #26. Existing working components are preserved; this sequence verifies exit gates and fixes remaining gaps. Original Sprint 1–5 historical evidence retains its original names.

| Execution sprint | Current work | Exit gate / evidence |
|---|---|---|
| 1 Stabilization | Build/syntax/backend regressions; populated Alembic, real browser CRUD/tenant negatives; inactive OTEL registration and edit reconciliation fixed; selected org summary clarified | Controlled PASS: [browser CRUD](acceptance/operational-sequence/resource-crud.json), [migrations/security/restore](acceptance/operational-sequence/sprint1-release.json), actual registration screenshot |
| 2 Template configuration | Verify pinned templates/rules, resolution, assignments and activation against existing golden path | Controlled PASS: [fresh pinned-template HTTP golden path](acceptance/operational-sequence/sprint2-http.json) |
| 3 Telemetry | Verify native Linux/controlled Windows/Carte; complete safe remote HTTPS Basic Auth and authenticated worker heartbeat | Controlled PASS: [actual Basic HTTPS/heartbeat](acceptance/operational-sequence/sprint3-remote.json), [native Linux/Carte/NOC](acceptance/operational-sequence/sprint3-native-noc.json). Real Windows/Carte/AWS acceptance remains separate |
| 4 Alerting/correlation | Verify consecutive breaches/dedup/recovery/incident evidence; harden and validate controlled ServiceNow lifecycle | Pending controlled external API fixture; no real outbound incident delivery authorized |
| 5 EKS/deployment/release | Read-only EKS discovery; clean Docker demo, screenshots/docs/CI/PR review | Pending controlled SDK/runtime evidence and final exact-head CI; new changes not merged without review |

[OWASP verification checklist](security/OWASP_API_2023_CHECKLIST.md) is developed incrementally. PASS is a controlled development result, not independent production security sign-off. AWS setup remains paused; no provider credential or real customer endpoint is used.
