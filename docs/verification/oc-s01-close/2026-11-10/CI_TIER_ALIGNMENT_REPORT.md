# CI tier alignment — no gate changes

Current ruleset26082467/effective main rules are retained under raw/. Required checks remain strict,GitHub Actions app15368,and one independent approving review is required. PR89 has **no submitted review**. No rule,job name,permission,trigger or workflow changed in this assessment.

|Required context|Integration app|Reporting category|PR89 exact-head rollup|
|---|---:|---|---|
|frontend-build|15368|Sprint functionality/regression|SUCCESS|
|frontend-dependency-audit|15368|Security|SUCCESS|
|image-validation|15368|Security|SUCCESS|
|contracts|15368|Sprint functionality/regression|SUCCESS|
|python-dependency-audit|15368|Security|SUCCESS|
|secret-history-scan|15368|Security|SUCCESS|
|staging-smoke|15368|Sprint functionality/regression|SUCCESS|
|private-https|15368|Sprint functionality/regression|SUCCESS|
|verification|15368|Sprint functionality/regression|SUCCESS|
|pipeline-contracts|15368|Sprint functionality/regression|SUCCESS|
|restore-retention-tls|15368|Reliability/preservation|SUCCESS|
|access-rbac|15368|Sprint functionality/regression|SUCCESS|
|noc|15368|Sprint functionality/regression|SUCCESS|

PR89 `ecfdff2cf3f9d1a7b7b284e79a7f708d1baea8ce` currently reports25SUCCESS,8FAILURE. All13 required contexts above succeed, but this does **not** override seven image-role failures and security-sbomFAIL. Thus "required13 green" is not release clearance. Raw/pr89.json preserves check links; all28 workflows/jobs/triggers/commands and source hashes are in CI_WORKFLOW_ALIGNMENT.json. Category labels are reporting only: mixed jobs retain shared security,protective excluded-feature and legacy-preservation coverage.

## Exact-head security evidence

Completed image run42630435435 is associated with PR headecfdff2cf3f9d1a7b7b284e79a7f708d1baea8ce, but its image provenance says merge commit `6d0057de00cf4606fdff029bc2b442c345c14b20`. The GitHub commit has parents main/currentPRhead and **exactly the same tree** `4ae504ba6a4b639557dba46ea085f0bcfba1c2f9`. These identities are recorded separately,never silently substituted. All7 artifact ZIP SHA256s,provenance-file checksums and CDX/Syft/Grype config IDs were independently verified from downloaded completed-run artifacts.

The seven current scans retain exactly the SEC001 baseline finding multiset:984matches,41Critical,371High,4Unknown. Backend runtime/migration each59High;PostgreSQL3Critical/32High;collector19Critical/81High/2Unknown;UAT19Critical/140High/2Unknown. Frontend/gateway each3Medium but pending legal review still blocks their gates. All7 licence statuses PENDING_ACCOUNTABLE_REVIEW. Exact identities and individual scanner findings/fixes are retained in raw/EXACT_HEAD_SCAN_RECONCILIATION.json; no new image scan or remediation was performed here.

Scope gap: current frontend role scans demo Dockerfile,not production runtime. R01 draft#99 adds exact-image bindings/8th production-frontend coverage; unmerged and not applied here. R02 draft#100 provides35-row PostgreSQL/gosu static qualification,zero cleared. These separate drafts do not close SECURITY. Final registry manifest approval,bundled JS/transitive licensing,NOTICE/source offers and accountable legal signature remain missing.

## Ten-sprint policy alignment

The exact source plan `b8c1615340828d1d3031c635fb319565dd9f222a` is preserved under raw/APPROVED_CI_PROGRAM.md; current planning-path absence is a traceability gap. TierA source/build/scope, TierB actualPG/FastAPI/React/Playwright/migration/concurrency and TierC scanner/secrets/egress/licence remain distinguishable. Current S01 tests execute real boundaries. Seven E2E register rows validate structurally but **zero are classified whole-path verified** by that register; do not promote classifications from grouped successes. Later genuine OS/provider/durable-spool/release qualification cannot be replaced by unit tests. Publisher/UAT deployment stay manual-only,not enabled here.

Proposed clearer reporting,documentation only: display separate fields technical-contract result,scope/source gap,independent review/owner acceptance,security/licence and reliability/release qualification;attach exact head/build/manifest identities and artefact links. Keep failing jobs failing; distinguish known compliance blockers from product regressions without suppressing either. Any future required-name migration needs verified equivalent coverage plus separate administrator authorization. No such migration is requested or executed here.

Existing hosted results were read once for this audit. After pushing this review draft,Trigger-and-Exit applies:record new workflow links/PENDING,do not monitor completion or rely on older green runs for the new docs SHA.
