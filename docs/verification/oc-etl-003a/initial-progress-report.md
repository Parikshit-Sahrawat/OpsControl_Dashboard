# OC-ETL-003A — in progress

Baseline a420dbc12e66196e00832f450d46a739b7cd0e99, existing PR80 branch.

The pipeline assertion expected only historical per-revision refusal messages; the central preflight now rejects earlier. The corrected assertion requires nonzero exit, stable populated-refusal and actionable backup/restoration fragments, and identical logical pg_dump output before/after (data, schema, constraints, Alembic version). Only PostgreSQL random restriction keys are normalized. Production guard unchanged.

Staging smoke previously used unsupported relative downgrade -1 at revision 0024. Its exact supported predecessor is 0023_worker_heartbeat, now explicit. The database is the workflow's disposable PostgreSQL service before its populated preservation probe.

Executed: DOCKER_HOST=unix:///var/run/docker.sock V16_API_ACCEPTANCE=1 V16_EVIDENCE_DIR=/tmp/oc-etl003a-pipeline backend/.venv/bin/python scripts/v16-acceptance.py — exit 0. Nine HTTP groups passed; raw evidence and preservation hashes adjacent. Harness finally removes its owned container.

NOT YET EXECUTED: revised staging smoke, full OC-ETL-003 regressions, final committed-source rerun, hosted CI. This report is not completion. PostgreSQL exact version still needs capture. Original failures remain under ../oc-etl-004/preflight/.

CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.
