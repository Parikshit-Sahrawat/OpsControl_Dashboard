# Issue95 — sequential bounded architecture alignment

2026-11-09 UTC / Asia/Calcutta. Per owner task OC-S1-CI-005, this patch follows the locally verified recovery and its evidence commit dffb7668e3609847b9817a2c500d39e979cd9da9. Product/acceptance source db1109801c76977fd77cd41b24f0ac4cec21a575. No competing product modifications, new runtime features, collector changes, migrations or deployment. All changes stay in draft PR89.

Deliverables: [architecture alignment](../../../architecture/SPRINT1_E2E_ALIGNMENT.md), [workflow matrix](../E2E_WORKFLOW_MATRIX.md), machine-readable E2E_WORKFLOW_MATRIX.json, scripts/ci/e2e_alignment.py and tests/test_ci_e2e_alignment.py. Issue95 and its owner comment6736751070 are preserved in ../ci005-2026-11-09/ISSUE95_AUTHORITY.json; parent Issue92 snapshot also retained there. Eight reference ideas are acknowledged without copied code/assets, new commercial dependencies or implied architecture approval.

The7 required workflows have6 PARTIAL and1 BLOCKED whole-path dispositions. Source paths and evidence paths are pinned to separate immutable commits and content hashes. Controlled subpath PASS results remain visible without certification of a whole provider-to-UI chain.0 whole-path certifications,0 genuine-provider qualifications,0 independent acceptance/release transitions are claimed.

The integrity guard rejects missing/duplicate workflows, unknown/contradictory statuses, missing evidence or required real-component declarations for controlled verification, nonexistent/unpinned/tampered evidence, Markdown/JSON drift, unauthorized provider/independent/release claims and changed release gates. It cannot establish a real-world claim from self-declared flags; accountable review still applies.

Default GitHub checkout is shallow. To avoid a new false CI failure or weakening immutable provenance, only the2 workflows executing repository-root CI tests now explicitly prepare the register's exact source/evidence commit IDs via a bounded read-only fetch. No checkout, branch advancement, deploy credentials, implicit network fallback in unit tests or full-history fetch was introduced. A real tiny shallow local Git fixture proves that pinned history can be obtained without changing HEAD; a second preparation is idempotent. Existing permissions, triggers, names and13 required contexts are unchanged.

Actual commands/results:

- `backend/.venv/bin/python -m unittest tests.test_ci_e2e_alignment -v`:8 PASS/0 FAIL/0 SKIP (alignment-tests-final.log). These are static guard/negative fixtures and a real Git-history regression, not provider/runtime certification.
- `backend/.venv/bin/python -m unittest discover -s tests -v`:112 PASS/0 FAIL/0 SKIP; includes the8 guard tests, so do not double-count (unit-alignment.log).
- `backend/.venv/bin/python scripts/ci/e2e_alignment.py`: PASS,7 rows,0 whole paths verified; exact file/hash/source checks succeeded (alignment-validation.json).
- `backend/.venv/bin/python scripts/ci/policy.py`: PASS;814 inventoried entries including all8 newly reviewed SHARED_SECURITY/RUN guard tests,786 UNKNOWN remain RUN,28 workflows,13 required contexts (policy-alignment.json). Previous806 rows remain classified as before.
- `bash scripts/check-workflows.sh`: exit0; all28 workflow files checked by checksum-pinned actionlint (actionlint-final.log/exit).
- CI005's real PostgreSQL/FastAPI/React/Playwright/Agent+Contrib/TLS/recovery evidence remains immutable at its original tested commits. This documentation-only architecture patch does not relabel them as newly executed qualification.

Deferred until individual post-Sprint1 approvals: exact provider qualification targets/builds/authority, D07/D08 schedule policy, independent history-range/frequency/aggregation reconciliation and any new query/cardinality semantics, older-writer cutover, externally verified Email/PagerDuty delivery, durable spool implementation/certification, UI/typography redesign, storage engine/brand/licence changes. Keep configuration readiness, applied collector state, telemetry freshness, native ETL attempt outcome and operational health separate.

The owner-accepted54f26e5 Resource Management visual baseline and historical evidence remain unchanged. Later interaction acceptance, independent engineering approval, nine owner selections Pending and independent UAT remain separate. No merge authorized. Final hosted workflows will be triggered against the pushed combined SHA; **CI TRIGGERED — RESULT PENDING**, then stop without polling. All7 image-role vulnerability/licence failures remain enforced pending genuine remediation and accountable legal/NOTICE review.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO · Sprint1 NOT COMPLETE.**
