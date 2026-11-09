# OC-S1-CI-003 — controlled closure and CI remediation, 2026-11-09

**PARTIAL/BLOCKED; Sprint1 NOT COMPLETE.** Starting PR89/head54f26e51106469e285dd747dd6b8afd09ca43ce6, main2e4fe5d8cb0f39170b0d789fdd7e07be4ac0219a. Exact code/test identities and hashes: SOURCE_IDENTITIES.json. Existing draft PR89 only; no merge/deployment/publication. Typography is separately committed on design/typography-system-v1-issue90, not imported or implemented here.

## Required CI: observed causes, fixes and limits

BASELINE_REQUIRED_CHECKS.json records all13 exact contexts:10 success,3 failures at54f26e5. No check names, thresholds, strictness, approvals or ruleset26082467 were changed.

| Check | Exact baseline failure | Correction / verification |
|---|---|---|
|verification — run42532627097,job128889962913|Black would reformat backend/app/unified/api.py; formatting step exited2. Subsequent always-run coverage exited1, “No data to combine,” because test stages never executed.|Black formatting corrected. Current quality command passes48 Black files, Ruff, pinned Prettier, ESLint and real Vite build. Coverage reporting executes successfully with real data; configured subset combined line/branch measurement62.94%, not whole-product coverage. Existing quality policy/thresholds are unchanged.|
|image-validation — run42532627312,job128889963340|BuildKit “secret proxy_ca: not found” in frontend apk-upgrade required=true mount.|Both validation build actions and quality cache build actions now supply a runtime-only CA secret file. Required=true and SSL verification unchanged. Real tiny BuildKit negative missing-secret exits1; provided-secret build exits0 and verifies CERT_REQUIRED + hostname checking, with network disabled. This proves the mount/trust boundary, not a full application build.|
|access-rbac — run42532627147,job128889962536|Actual access migration/security25 groups and browser8 groups passed; owned Compose build then exited through generic private-diagnostics error.|Uploaded artifact lacks the private Docker failed.log; historical exact failing instruction is NOT RECOVERED. Independently inspectable Compose defect: frontend requires proxy_ca but no build secret was passed. Harness override now wires it to API/worker/frontend, validates trust and exports redacted failure logs/cleanup. Cannot certify this was the sole hosted cause or claim a fresh full Compose PASS locally.|

The managed Docker backing filesystem remains about0–350MiB free. Full application/Compose builds are **BLOCKED locally**, not silently skipped as success. Hosted isolated runners must verify them on the final commit. No broad Docker cleanup is used; the old optional broad builder-prune path is now refused. No secret/CA bytes are committed or baked into image layers. CA trust is not a credential; its BuildKit runtime provisioning still fails closed when absent/invalid.

The first local security attempt hit an unwritable pip-audit cache; retry used an owned cache and preserved strict options. First quality attempt lacked a usable pinned Prettier because npm's default cache was unwritable; retry used an owned cache. Both failure logs remain. These were environment failures, not fabricated vulnerability/quality passes.

## Coordinated child-source contract

The existing Data Source revision ledger remains the only configuration authority. A scoped configuration-context read returns parent/child source and child resource revisions. The UI captures this once on open/resume, clears it on identity/tenant/authorization changes and disables Save until the authorized snapshot is available. It explains unavailable snapshots. It never silently fetches newer tokens at save time or overwrites unsaved input.

For opted-in revisioned child API sources, the parent PUT requires both child-resource and source expected revisions plus a command key. Same-customer ownership and resources.update are checked; unexpected references reject422. Child keys derive deterministically from the parent command key/source ID. Source commands revalidate applicability and flush within the existing parent transaction; only the final resource commit commits all changes. A stale child rejects409 and rolls back even preceding source flushes. Existing nonrevisioned legacy paths remain separate; this is not certification of every older binary.

Actual PostgreSQL/auth HTTP tests verify stale-child rollback, successful parent/child source head transitions and viewer denial. Actual React/FastAPI browser editing changes parent/child environment together and independently reads persisted source revision2. A new browser test exposed a real save-before-snapshot UX race: the earlier attempt correctly withheld persistence but left a confusing error. Disabled-save/loading feedback fixes the interaction; no timeout/assertion was weakened.

## Catalogue publication CAS

PATCH requires expected_version; DELETE requires Expected-Version. Missing preconditions428, stale409 with STALE_CATALOGUE_VERSION/current_version. Row locks serialize the check/update. Every accepted metadata/package update and retirement advances the catalogue version and appends an immutable snapshot; prior source version pins are retained. Current actor comes from authentication, not client committed_by. No package change means a disabled catalogue is not implicitly re-enabled. Catalogue publication remains distinct from source configuration CAS and monitoring activation.

The editor sends its saved version, retains unsaved text on conflict, loads a review snapshot only at user request and requires explicit adoption before retry. Browser evidence verifies an actual concurrent publication, rejected stale save, preserved title, explicit review/retry and version3 persistence. API concurrency gives one200/one409; versions/history survive and missing retirement preconditions are rejected. Updated harness assertions account for the new immutable retirement version5 rather than discarding its history. Mixed-version binaries bypassing these API preconditions remain unqualified; no deployment/rollback compatibility is inferred.

## Applicability and provider boundary

APPLICABILITY_SCHEMAS.json exports the actual registered HOST_METRICS, SERVICES, FILE_LOG, METRIC_SCRAPE, OTLP_RECEIVER and SYSLOG_RECEIVER schemas and host/API template contracts. Executed source tests include invalid OS/method/overrides, unsupported manifests, HTTPS schema validation, secret rejection and no automatic collector activation. These are approved current schemas, not invented recurrence or provider semantics. Synthetic Pentaho fixtures and native-authority tests remain synthetic. No genuine Pentaho/Windows/EC2 target was authorized/accessed; genuine qualification remains BLOCKED.

## Executed checks — suites overlap, do not add

| Suite | Actual result / identified source |
|---|---|
|Broad PostgreSQL backend discovery|670 executions:594 PASS,76 SKIPPED,0 FAIL at2ceef37. Later HTTP retirement-version assertion failed; retained as partial wrapper, not full harness PASS.|
|Source configuration/ETL HTTP/PG|46 PASS,0 FAIL/SKIP at2ceef37; migration0043, rollback/refusal, source/context races, catalogue concurrency, parent/child atomicity, revocation and API SIGKILL/replay;108-table restore.|
|ETL regression|117 PASS,0 FAIL/SKIP at2ceef37; actual auth HTTP/PG/browser, no genuine provider certification.|
|Final integrated HTTP/browser|98 backend cases PASS; pipeline15 HTTP groups, Pentaho4/5/4/5, RBAC14, archive6 + resilience9; Resource Security9 browser groups, Workspace15, other browser17/5/3 at ebddbe5.|
|Access security|25 real PostgreSQL/HTTP groups +8 browser groups PASS at2ceef37. Scope is recorded by the harness; do not substitute this for blocked Compose packaging.|
|Frontend / CI / quality|55 frontend tests;30 CI policy tests; all28 workflows;48 Black files; Ruff/Prettier/lint/build PASS.799 scope records,786 UNKNOWN still RUN.|
|Security unit and dependency checks|7 access-control +10 release-hardening +4 remote-auth cases PASS; strict pip-audit0 vulnerabilities and npm0 findings on retry. Not independent security certification.|
|Seven image policies|All seven still FAIL: strict vulnerabilities and/or licence review. Exact984 matches and2,451 component/role licence records retained.|

Failures/retries include obsolete retirement-history expectation, incorrect browser selector, genuine snapshot-loading UX race, missing local tool caches and the raw hosted failures. Browser screenshots, scoped cleanup and database hashes remain in raw/. Coverage's62.94% covers only the configured executed module subset/data; no threshold was lowered, no missing-data error converted to PASS. No full program or release coverage claim.

## Images, licensing and unresolved gates

See IMAGE_AND_LICENCE_DECISION.md, IMAGE_SUMMARY.json, CVE_REMEDIATION.csv and LICENCE_NOTICE_REVIEW.csv. All original SBOM/Grype/provenance hashes remain valid. Backend vendor-wont-fix High findings, PostgreSQL Go/gosu findings, pinned collector findings and accountable licence/application licensing decisions remain unresolved. No suppression, severity reclassification, signature or waiver. Typography OFL review is separate and does not clear application images.

Issue90 explicitly accepts the54f26e5 Resource Management visual baseline. Newly added interactions still need owner review, and typography choice/scale remain pending. Independent engineering PR approval, nine owner selections, D07/D08, formal UAT, genuine-provider and release qualification remain separate.

Final-head workflows are triggered after push under mandatory **Trigger-and-Exit**; exact links/status at trigger are recorded in the PR handoff. No polling/waiting, no substitution of historical green runs. Full Compose/image-validation and all final hosted conclusions remain PENDING until owner inspection.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.** No Sprint2.
