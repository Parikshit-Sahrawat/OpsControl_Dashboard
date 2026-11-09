# OC-S1-CI-005 — targeted recovery

2026-11-09 UTC / Asia/Calcutta. Draft PR89 only; baseline72382ad1535c2d5a84d1e55fc19f692c351197a4. Source recovery commits30bbd43c46cfdd529742a4b73f970d7fa55d0aba and db1109801c76977fd77cd41b24f0ac4cec21a575. Main2e4fe5d8cb0f39170b0d789fdd7e07be4ac0219a unchanged. No product API/model/migration/collector/TLS/RBAC behavior changed.

## Exact-head observations and root cause

| Check | Exact-head evidence | Cause / bounded correction |
|---|---|---|
|verification|dispatch42593230847/job129079642757; PR42593037967/job129078987690; verification.zip|`make test-e2e` fails invoking `node scripts/arch001_acceptance.mjs`; controlled runtime passed. Coverage reporting itself succeeded at66.22% combined configured subset, not whole-product coverage. No coverage threshold changed.|
|native-monitoring|dispatch42593170246/job129079439605; PR42593038098/job129078988552; native.zip|Same browser subprocess fails after draft-switch evidence. Hosted wrapper did not export its private failure.log, so the exact hosted assertion was NOT RECOVERED from artifacts. An unchanged72382ad PostgreSQL/API/browser reproduction independently fails at arch001_acceptance.mjs:241, waiting30s for an obsolete JavaScript banner after clearing hostname. The native form correctly rejects the field before React onSubmit. Replace the stale banner assertion with **stronger** native validity/valueMissing/nonempty validation feedback/focus assertions, zero mutation requests and independently read PostgreSQL state unchanged. Test both hostname and DNS/IP, then preserve linked/unlinked draft switching and authorized save.|
|scope-policy|dispatch42593173629/job129079451179; no artifact emitted|Three prior Compose-build tests absent from .ci/scope-manifest.json. Regenerated and reviewed these plus4 newly added tests as SHARED_SECURITY/RUN. All799 previous rows unchanged;806 total,786 UNKNOWN still RUN. Missing/stale errors now identify exact entries. New negative tests prove omissions, stale entries and new Python/Node tests fail until explicitly inventoried.|
|restore-retention-tls|PR42593037863/job129078987231 failed, although dispatch42593208742 succeeded at the same SHA; recovery.zip|`route.fulfill: Route is already handled!` in delayed genuine context response. A response event can precede completion of the route callback; plain unroute does not drain it. Use Playwright `unrouteAll({behavior:"wait"})`, with no exception suppression, to drain real handlers before continuing. Assert0 in-flight and>0 completed real responses. Apply the same lifecycle correction to ARCH's delayed linked-detail route. Retain all keyboard/no-early-write/revision/reload checks.|

`baseline-reproduction/failure.log` contains the actual local assertion. Historical private secrets/keys were removed after retaining redacted failure output and hashes. All3 downloaded ZIPs match GitHub API SHA-256 (DOWNLOAD_SHA256.json). Raw hosted artifacts remain unchanged. Old browser report labels claiming an incident UI/ten-stage wizard were stale; new metadata correctly records excluded incident UI and0 identity-editor wizard stages, matching real assertions.

## Focused regressions and actual execution

No timeout increases, assertion bypasses, blanket skips or route error suppression. `scripts/acceptance_diagnostics.py` exports only redacted *.log, never fixture/session/key/dump files;2 tests verify secret removal while preserving failure assertions and prohibit private-file export. ARCH wrapper now retains failed-command identity/exit, redacted subprocess logs and owned cleanup metadata on success/failure. This fixes missing diagnostics, not the product.

| Command / owned boundary | Actual result | Evidence |
|---|---|---|
|`backend/.venv/bin/python -m unittest discover -s tests -v` from root|104 PASS,0 FAIL,0 SKIP;4 new cases|unit-final.log|
|focused CI contracts + diagnostics|27 PASS,0 FAIL,0 SKIP; subset of104|unit-first.log|
|`backend/.venv/bin/python scripts/ci/policy.py`|PASS:806 entries,28 workflows, all13 required identities preserved|policy-local.json; SCOPE_REVIEW.json|
|`bash scripts/check-workflows.sh`|exit0, checksum-pinned actionlint|actionlint.exit/log|
|`npm test --prefix frontend`; lint; build|55 PASS,0 FAIL,0 SKIP; lint/build exit0; bundle-size warning remains|frontend-*.log/exit|
|Unchanged72382ad `ARCH001_API_ACCEPTANCE=1 ARCH001_ENGINE_ACCEPTANCE=1 ARCH001_BROWSER_ACCEPTANCE=1 ... python scripts/arch001-acceptance.py`|FAIL retained: obsolete banner timeout|local-arch-baseline.log; baseline-reproduction/failure.log|
|Same browser command at30bbd43, then db11098 final|both exit0; actual FastAPI + migrated disposable PostgreSQL + production React build + Playwright;5 access checks also PASS|local-arch-browser-1/ and local-arch-browser-final/; identity-validation.json proves2 invalid fields,0 writes, independent DB preservation|
|`ARCH001_API_ACCEPTANCE=1 ARCH001_ENGINE_ACCEPTANCE=1 ARCH001_RUNTIME_ACCEPTANCE=1 OPSCONTROL_OTEL_BINARY=/tmp/oc-closure-tools/otelcol-contrib ... python scripts/arch001-acceptance.py` at db11098|exit0; actual Agent/0.123.0 Contrib logs/metrics/traces over verified TLS,100 API requests per mode with4 concurrent workers, native reconstruction/failure alert, enrollment/rotation/revocation/receipt checks|local-arch-runtime/ (runtime.json, performance.json, agent-v15.json); local-arch-runtime.log|
|`RELEASE_BROWSER_ACCEPTANCE=1 ... python scripts/release-acceptance.py` at30bbd43|exit0;13 top-level groups;8 nested resource CRUD groups; new handler-drain assertions PASS with2 real completed context responses and0 remaining;0 premature writes,2 committed Enter commands, revisions advance and reload persists|local-recovery-1/report.json, keyboard-regression.json, cleanup.json|

Browser/runtime env used Playwright1.56.1, Chromium141, Python3.12.14, Node24.19.0, PostgreSQL17.11, Docker28.4.0 (usable). All service ports/DBs/keys were task-owned fixtures. Runtime pin remains0.123.0, SHA-2566bca4ddd928b4b0880f7ec6c16511922f740c497b4efa4b33915b2d54a729213. No new provider or durable-spool certification. Counts are nested runner/group counts, not summed unique requirements. Cleanup reports confirm allocated processes/containers removed; no broad prune or shared UAT access.

## Hosted status and security

BASELINE_RUNS.json retains all36 exact-head hosted runs (18 PR +18 dispatch).14 dispatch workflows passed; verification/native/scope/security failed. Recovery's PR failure and dispatch success are kept separately, not cherry-picked. Source recovery is locally verified; final combined head will trigger/dispatch all18 PR-safe workflows, then **CI TRIGGERED — RESULT PENDING** under mandatory Trigger-and-Exit. No final-head green claim or polling.

All7 exact72382ad image-role jobs and security-sbom remain FAIL in image-jobs.json; original scan artifacts/identities remain linked by image-artifacts.json. Previous byte-preserved SBOM/Grype/licence packages and review remain under ../required-recovery-2026-11-09/. Those historical984 matches (41 Critical/371 High) belong to their recorded earlier candidate identities; they are not relabelled as fresh scans. No image remedy, legal reviewer, scanner exclusion, threshold change, collector upgrade or waiver is claimed. Final-head security scans remain pending and actionable failures must stay enforced.

After these focused corrections pass, issue95 may proceed sequentially as the separately authorized architecture-documentation/evidence-guard patch. No concurrent product implementation or Sprint2. Source authority: ISSUE95_AUTHORITY.json (includes owner extension to8 references); individual later-sprint design choices remain deferred. Owner visual acceptance of the54f26e5 baseline remains in ../VISUAL_ACCEPTANCE.md; later interactions and independent PR approval remain separate.

**Sprint1 NOT COMPLETE · CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
