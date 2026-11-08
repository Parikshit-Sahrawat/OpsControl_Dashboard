# Sprint 1 integration and CI recovery report — 2026-11-08

> This report records the4081fc7 handoff. See the [subsequent closure follow-up](closure-followup-2026-11-08/REPORT.md) for new commits, tests and current blockers.

**Result: PARTIAL / BLOCKED; Sprint1 NOT COMPLETE.** Semantic integration is delivered; controlled tests below passed. Source-context writer cutover and remaining configuration UX/contracts are explicitly incomplete. Ruleset changes were refused403. Image/licence findings are unresolved. No merge, deployment or release approval.

## Baseline and branch preservation

Verified main: `2e4fe5d8cb0f39170b0d789fdd7e07be4ac0219a`, including merged85. Starting PR89 head: `d03579be078506ac51174645f554e90d6f198f92`. All six heads in INTEGRATION_LEDGER.md are ancestors of this branch. Three-way merge commits:1b24df3,99aea37,077e627,e5f6cee,5bc997e,100cb1f. See MERGE_PROVENANCE.json for full parents/conflict reproduction.

PR80 ETL models/native authority/workflow UI, PR81 reconciliation, PR82 lifecycle/RBAC, PR83 policy/AUTH694, PR84 workspace/theme and PR86 incident-UI retirement are preserved with main85 CI. Source branches/main were not modified or merged in GitHub. Unrelated uncommitted CI002 evidence in `/tmp/oc-ci-main` remains untouched.

Main controlled application candidate: `89f8a554aa4656d0f5f0c02e13729224b855e1d7`. Historical-schema/cleanup harness correction: `76c53e9f2ea91510509fb06e6500b2e11090526c`. Final configuration validation/fencing follow-up: `917da636670524f656d7db74e9324435eb5e9721` (final product implementation identity; evidence-integrity CI follow-up25cd3bf; documentation-only packaging follows). Source hashes bind exact files and distinguish these executions. No claim that an older hosted workflow qualifies the final documentation HEAD.

## Implemented contracts and source

- Additive0042 after unmodified0041: DataSource configuration head and immutable tenant-owned revisions, composite ownership/parent/restore FKs, command uniqueness, canonical content/hash, authenticated actor/time and safe package/context snapshots. Unsafe populated downgrade is refused before DDL. Existing migrations and ETL guards remain.
- `backend/app/services/source_configuration.py` and `api/source_configuration.py`: source-locked expected-revision commands, actor/source idempotency, atomic projection+history+head, preview/current/history/detail/diff, explicit legacy import and new-revision rollback. Existing attachment POST/PATCH/DELETE require revision/idempotency preconditions and use the same command. No activation, secret value or checkpoint restoration.
- `template_applicability.py`: explicit typed Windows/Linux/VM source families and real six-method schemas; source/OS conflicts and excluded/unknown declarations fail closed. Explicit API manifests reuse bounded HTTPS GET/HEAD settings. Worker egress/DNS/TLS authorization remains required at activation/dispatch; no authority is inferred from declaration.
- `template_resolution.py`, `api_monitoring_config.py`, `worker/egress.py`: reuse pure HTTPS/settings validation, keep actual allowlist checks in execution paths, preserve pinned effective settings and reject retired/unverified templates. No collector-version change.
- ResourceTemplateConfiguration shows real pins, overrides, saved effective configuration, source revisions and audited restore. TemplateEditor preserves explicit applicability edits and supports existing HTTP package type. Full context/diff/history UX and writer transition gaps remain listed, not claimed complete.
- FeatureDirectory/TopNav: approved in-panel expandable navigation, permission-filtered leaves, keyboard and persistence; remove flyout. AuthGate fails closed on unavailable verification, retaining a token only for transport failures, clearing on401/403. Actual browser fault/revocation checks verify the boundary.
- Browser helpers follow real expandable controls. Preserve excluded Incidents route/nav assertions and all backend alert, correlation, incident-processing and historical data tests.

## Executed development verification

Counts are **per suite, not additive**. BACKEND_TEST_RECONCILIATION.json resolves imported/repeated identities and overlapping groups:642 unique backend unittest identities have executed PASS evidence. The68 discovery skips are covered by owned ETL/source runs; they are not counted as PASS in discovery. This does not certify providers or independent release gates.

| Suite / evidence directory under runtime-evidence | Actual result | Source |
|---|---|---|
|pr89-consolidated-full: PostgreSQL discovery|662 executions:594 PASS,0 failures,68 SKIPPED|89f8a55|
|pr89-consolidated-etl: actual PG/auth HTTP, native authority/writer/rollback/DAG and3 browser cases|117 PASS,0 fail/skip|89f8a55|
|pr89-api-configuration: revision/history, atomic failure, race/idempotency, tenant/revocation, HTTPS negative and restoration|38 PASS,0 fail/skip|c39ad3c|
|pr89-typed-source-final: endpoint denial/typed source-family follow-up plus configuration/ETL regression|38 PASS,0 fail/skip|8104e4e|
|pr89-final-manifest-validation: malformed manifest and first/legacy writer denial follow-up|2 PASS,0 fail/skip|472f297|
|pr89-final-configuration-closure: full source/ETL contract subset after final malformed/excluded/target safeguards|38 PASS,0 fail/skip|917da63|
|Frontend Node tests|55 PASS,0 fail/skip|89f8a55 (frontend product source unchanged by backend follow-ups)|
|CI policy/unit/actionlint|24 policy regression tests PASS;28 workflows valid;785 scope records retained,772 UNKNOWN still RUN|see final-source logs|
|Lint/build/Python static/dependency integrity|PASS; real Vite production build in consolidated harness; npm audit0 findings; pip check no broken requirements|see logs|
|Consolidated authenticated browser|resource security7 groups; workspace14; pipeline eight-step acceptance; Sprint07 17; Sprint08 5; Sprint09 3; scope exclusion PASS|89f8a55|
|Consolidated authenticated HTTP|pipeline15; Pentaho4/5/4/5; RBAC14; archive/resilience6 +9 measured scenarios|89f8a55; synthetic providers|
|pr89-operational-fixed: controlled HTTPS Carte/live-host/alert lifecycle and NOC|PASS; theme13 checks,6 contrast measurements,0 page/server errors|76c53e9; **not genuine Carte**|
|pr89-consolidated-release: full HTTP/security/browser/restore/TLS harness|13 top-level groups PASS;67 scope HTTP checks;17 scope-browser groups;7 closure-browser groups|76c53e9; isolated production-mode settings, no production infrastructure|

The exact commands, internal exit-code records, logs, screenshots, versions and limits are in TEST_EXECUTIONS.json and runtime evidence. Early shell wrappers printed tails after execution; their outer shell0 is not used to infer the test result. Harness command records and actual result files/unittest summaries establish results. Failed attempts remain in their own directories.

## Preservation and failure evidence

PostgreSQL17.11; fresh0042 upgrade, supported empty0042→0041→head and schema drift check pass. Configuration fixture backup/restore compares108 tables, content hashes and schema. Consolidated populated downgrade before/after normalized dump SHA256 is identical: `37e12c203e63606018f2bf48eca1516c945135b0bcf81009dbc344099b379153`; refusal exit1 is expected. Full release restore verifies every row hash, constraints, migration head and audit triggers; corrupt/overwrite/nonempty-target recovery negatives pass. Synthetic archives/credentials are removed after hash/proof preservation; SECRET_ARTIFACT_DISPOSITION.json records them.

Retained failures include readiness socket race, initial JSON-vs-JSONB trigger comparison, missing test environment, mid-edit first baseline, obsolete browser helper depth, unavailable default Chromium, aborted-auth token destruction, one post-reload read connection reset, and historical-schema mapper seeding. Fixes were retested; no assertion/timeouts/security thresholds were weakened. Only one idempotent GET has a bounded ECONNRESET retry; mutations and HTTP failures are not retried.

## CI and independent gates

All13 legacy required checks remain. sprint-evidence additionally verifies the consolidated artifact inventory/source hashes and immutable gate declarations; tampering/path-traversal regression passes.  Names/actions/triggers/test inventory are reconciled without retiring coverage. Six additional official Actions identities are verified historically; authenticated-workspace identity awaits hosted observation. Proposed additive ruleset update was **refused HTTP403**; a re-read confirms unchanged strictness,13 contexts, bypass actors and independent approval. Repository-admin flag did not grant Administration-write permission. See CI_CLOSURE.md and RULESET_UPDATE_RESULT.json.

All seven historical image policy runs FAIL with unresolved High/Critical/unknown matches and pending licence review. Raw SBOMs/scans, DB/tool/provenance metadata and checksums are retained. PostgreSQL has4 Critical/125 High matches in the examined run. These are historical images, not fresh final-candidate clearance. Local fresh image build/scan is blocked by Docker backing storage0–350MiB; no broad cleanup, digest replacement, finding suppression or waiver was performed.

Final documentation HEAD CI is triggered on push and reported **CI TRIGGERED — RESULT PENDING** with available URLs in the PR handoff. No polling; owner monitors final outcomes. No legacy check removal or release certification is inferred.

## Completion prerequisites

OPEN_BLOCKERS.md is the dependency-ordered remaining-work register: atomic resource-context/legacy writer cutover; full history/diff/detach UX; publication concurrency; exact source-command crash/revocation/application provenance tests; provider-specific qualification where required; security/legal remediation; sufficient build storage; ruleset Administration-write permission; final hosted results; owner visual acceptance and independent review. Existing D07/D08, nine acceptance selections and formal UAT/provider obligations remain pending.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.** PR89 stays draft. Request owner review of VISUAL_ACCEPTANCE.md and independent engineering review; no merge is authorized.
