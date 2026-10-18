# REC-04 — legal-hold preservation

**PASS for the existing service and cleanup paths in a synthetic restored database.** An active `PipelineHold(kind='LEGAL')` was created against one A-owned fenced source before backup. Its original ID, source ID, owner-actor ID, reference and `released_at=None` survived restore. A 40-day-old PipelineEvidence row on that source retained its original identity and full payload.

The originating actor's attempted `release_hold` returned `INDEPENDENT_LEGAL_RELEASE_REQUIRED`. After rollback, `pipeline_service.cleanup` completed; the held evidence payload was unchanged and the hold remained active. In the same final owned run, the pre-existing independent-release and held-retention PostgreSQL tests passed. These checks enforce legal-hold precedence over this ordinary cleanup/retirement path; they do not claim that a database superuser cannot directly delete a row, that every evidence class has been exercised, or that an authorized independent release can never occur. Safe detach/retirement where protected evidence is not erased remains permitted by the existing rules.

GOV-07 separates protected legal evidence from ordinary backup, telemetry and audit retention. No retention job or production policy was changed. [REC-02](RESTORE_PRESERVATION.md) covers the corresponding restored IDs and [VERIFICATION.md](VERIFICATION.md) records the execution.
