# Four-phase gates

| Phase | Entry / exit | Current decision |
|---|---|---|
| 1 Development | Approved scope, source implementation, durable persistence, security/behavior/migration checks and required CI; owner dispositions for gaps | NOT Development Complete |
| 2 Manual/automated testing | Exact build/schema/environment; independent case receipts, genuine providers separately | Owner parallel UAT in progress; no acceptance inferred |
| 3 Improvements and fixes | Evidence-backed defects and bounded approved slices; affected regressions and migration/security gates | Planning only, no implementation authorized |
| 4 Deployment/release | Independent security, provider, recovery and operational gates plus explicit approval | NO-GO |

Issue47 and merged scripts/test-quality.sh supersede historical fixed65%/80% development gates; measurements remain historical and mandatory behavioral/security/CI checks remain. No threshold or workflow changed. ENG-001 full original authority remains missing.
