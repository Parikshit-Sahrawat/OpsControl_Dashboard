# OC-ETL-008A — Pentaho native scheduler preparation

2026-11-07 UTC. Baseline **`c12db2764f6d581850b9d3ac5a89d6771a2fc002`**; existing branch dev/post-pr78-architecture-closure-20261105 and **draft PR80**. Exact final offline tested source **`80de546078d773c0a07f88c8ebd99ce920666447`**. Initial preparation commit830e785; final test guard80de546. Final evidence HEAD and hosted conclusions are recorded in the PR80 closure comment.

**Offline preparation VERIFIED; genuine-provider qualification BLOCKED / NOT RUN.** No Pentaho connection, credential use, discovery, workload execution, deployment or shared-data migration occurred. All5 endpoint candidates remain UNVERIFIED; installed builds are unknown. Synthetic build10.2.0.0-222 is an invented test label, not an observed provider.

## Deliverables

- [Read-only plan and source inventory](READ_ONLY_QUALIFICATION_PLAN.md)
- [Native identity matrix](PENTAHO_NATIVE_IDENTITY_MATRIX.md)
- [Endpoint safety review](ENDPOINT_SAFETY_REVIEW.md) and [candidate inventory](ENDPOINT_CANDIDATES.json)
- [Authority evidence mapping](AUTHORITY_EVIDENCE_MAPPING.md)
- [Offline and future qualification test matrix](OFFLINE_TEST_MATRIX.md)
- [Live authorization checklist](PROVIDER_AUTHORIZATION_CHECKLIST.md) and [nine Pending selections](OWNER_ACCEPTANCE_SELECTIONS.json)
- [Immutable historical references](SOURCE_REFERENCES.json), [unchanged migration hashes](UNCHANGED_MIGRATIONS_SHA256.json), [validation](VALIDATION.json), [artifact manifest](ARTIFACT_SHA256.json)

Server scheduler/repository authority remains separate from Carte execution/status. Native schedules, repository objects, occurrences, execution attempts and source generations have distinct scopes. Display names, PID, HTTP200, connection success and signed operator assertions cannot substitute for native identity evidence. No Server-to-Carte alias relationship is certified. Current JOB-only envelope is unchanged; schedule/epoch facts remain in referenced original evidence rather than unsupported new envelope fields.

## Reproducible bounded verification

```sh
backend/.venv/bin/python scripts/pentaho-qualification-offline.py
backend/.venv/bin/python -m black --check backend/tests/test_pentaho_qualification_offline.py scripts/pentaho-qualification-offline.py
backend/.venv/bin/python -m ruff check backend/tests/test_pentaho_qualification_offline.py scripts/pentaho-qualification-offline.py
python scripts/check-ci-roadmap.py
```

Uses the existing backend development virtual environment. No packages installed. The runner blocks SQLAlchemy connections, Python socket/DNS and subprocess operations and sets an inert database URL; no application service or provider transport starts. These are process-level guards, not a kernel network sandbox.

| Check | Actual result | Evidence |
|---|---|---|
| Committed-source offline suite | **60 PASS;0 failures/errors/skips; exit0** | [final log](logs/offline-final-guarded.log) |
| New tests |10 synthetic preparation cases, included above | backend/tests/test_pentaho_qualification_offline.py |
| Retained tests |50 Pentaho R1/surface/historical Carte/parser and OC-ETL-007 pure envelope cases, included above | final log |
| Forbidden I/O attempts |0; no DB connections, network requests, DNS or subprocesses | runner result in final log |
| Black/Ruff |PASS, exit0 | logs/black-final.log, logs/ruff-final.log |
| Requirements traceability |PASS;56 IDs,31 included journeys,nine historical decisions | logs/traceability-final.log |
| Prior migrations |All44 tracked migration files byte-identical to baseline, including0040/0041 | UNCHANGED_MIGRATIONS_SHA256.json |
| Runtime PG/browser/live qualification |NOT RUN in this local preparation; previous002–007 evidence retained, not reclassified | SOURCE_REFERENCES.json |
| Prepared qualified admission cases Q01–Q08 |BLOCKED / NOT RUN | OFFLINE_TEST_MATRIX.md |

The stale fixture deliberately demonstrates that parsing old SUCCESS does not prove freshness. Only the independently enforced proof expiry gate is asserted to reject expired proof. Duplicate fixture equality is a deterministic identity test, not PostgreSQL deduplication/receipt completeness or exactly-once certification. Valid CONTRACT_TEST_ONLY signatures stay unqualified; assurance escalation refuses. No genuine qualified rows or receipts are seeded.

## Preserved failed/intermediate attempts

- [offline-attempt1](logs/offline-attempt1.log): startup blocked when croniter's architecture probe attempted local `file`; not a provider request or a PASS. Runner now supplies actual interpreter pointer width without process execution.
- [offline-attempt2](logs/offline-attempt2.log):60 PASS in the precommit candidate.
- [ruff-attempt1](logs/ruff-attempt1.log):E731 lambda style; replaced with ordinary function.
- [ruff-attempt2](logs/ruff-attempt2.log):F401 intermediate unused Engine import; guard wiring corrected in80de546. No production behavior changed.
- [offline-final](logs/offline-final.log):60 PASS at intermediatec371af9 before the explicit Engine.connect guard; superseded by final guarded run, not omitted.

## Remaining decisions and scope

Exact installed build/target, read-only endpoint specification, native object/schedule/execution links, issuer governance, independent reviewer, TLS/network/credential approvals and original accepted runtime evidence remain missing. Future Q01–Q08 require separate authorized fixtures and genuine proof; no synthetic signature grants those prerequisites. D07 recurrence/calendar/occurrence and D08 long-running/freshness/aggregation decisions remain Pending. Existing migration guards, writer fence, RBAC, DAG locks, source contracts and collector pin are unchanged.

All nine current owner-acceptance selections remain **Pending**; prior **OWNER_APPROVED_CONTROLLED_SCOPE — INDEPENDENT_UAT_PENDING** records are preserved. No new owner/provider/independent security acceptance inferred. Journey20 excluded,Journey32 skipped,31 included journeys and30 unrecovered numbered definitions unchanged.

Cleanup: no containers, services, databases, volumes or provider credential/private-key files created by the local tests. In-memory ephemeral test keys disappear at process exit; only synthetic fixtures/logs are retained. No production/live UAT access or broad cleanup. Hosted existing isolated CI is reported separately and never interpreted as genuine certification.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
