# OC-DEV-COMP-CI-003 corrective handoff

Three isolated workstreams; no integration/merge between them.

| Workstream | Branch | Core implementation commit | Delivery HEAD before push |
|---|---|---|---|
| CI003B product scope | fix/ci003-excluded-incidents-ui | e74038d8248b0849127339230ef89a942b5700c5 | e74038d8248b0849127339230ef89a942b5700c5 |
| PR84 browser recovery | dev/oc-dev-comp-001-resource-workspace | cead86d4360c9dd9fed2366301e089f9af47894b | 8427cbc8c6387ab6e496a44c210db3c9eb3101e3 |
| CI003A artifact exclusion PR85 | ci/oc-dev-comp-all-pr-verification-20261108 | c53d0a87e33ee4d614720a07b04e8f66935c473d | Evidence-only final commit supplied in handoff |

Remote baselines verified: PR84 cbbaec54ea74139f51b1d75a26ce91378f89a298; PR85 5318e741993616a90f894092565acee915166d8f; scope branch origin/main ffe5ac285ab8aef33a1139bce6f3da79be3d6d33. PR84 working tree was clean. PR85 tracked tree was clean with known local CI002 assessment artifacts preserved untouched. Environment runtime ready, Docker28.4 usable; old Docker backing storage nearly full caused owned fixture startup failures. Only disposable PG fixture storage changed to tmpfs; no production/telemetry durability contract changed. No database power-loss certification.

Six original failed PR84 workflow logs/artifacts were downloaded and independently inspected. Access and ARCH private diagnostics were locally reproduced. Fixes cover real category expansion, authentication-shell readiness, navigation aliases/current semantic controls, obsolete excluded UI positives and relocated Display clock. No arbitrary timeout increase or blanket skip. Source/hash/changed-file inventory and failures are on PR84 in docs/verification/oc-dev-comp-ci-003/recovery/. Two probe outputs originally named JSON were mixed JSON/text; retained as raw stdout and not falsely validated as JSON.

## Tests and limits

- Scope branch: existing frontend38 PASS, background20 PASS, real PostgreSQL98 PASS; actual API23 groups; authorization browser5 groups plus existing eight-step workflow; original unchanged ci_scope_acceptance assertion PASS; three retired hash routes PASS. Lint/build PASS and allocated resources removed. No merge into84/85.
- PR84: frontend46 PASS, backend344 PASS/220 SKIP, focused background/access27 PASS (overlaps backend). Access API25/browser8 groups PASS, ARCH/browser/access-v15 five groups PASS, operational lifecycle/browser/tenant harness PASS, release restore/retention/TLS harness PASS, staging18 local commands PASS, consolidated real PostgreSQL/TLS/pinned OTel/browser compatibility PASS, quality/lint/build PASS. These are local component/harness results; full hosted workflow installation/image/runtime stages not asserted locally complete.
- PR85: all27 workflow definitions actionlint PASS, controller/CI90 PASS. Six original hosted artifact sets repacked with every flat evidence file byte-identical. Original combined compressed size 3359587743 bytes; local repack 5187520 bytes. This is a measured local repack, not a claimed new hosted upload. SBOM, Grype findings/CVEs, DB provenance/freshness, tool versions, image identity, licence inventory and hash records preserved. Only grype-cache/** excluded. No vulnerability/licence threshold or scan result change.
- No new provider qualification or formal UAT. No collector pin change (tested0.123.0), no D1–D4 modification, no protected checks changed. Current security/vulnerability/licensing and durability blockers remain.

Push each authorized branch; update draft PR84/85 and open separate draft scope PR; trigger affected CI and record available run links once, then stop. CI TRIGGERED — RESULT PENDING at final handoff; no polling/completion claim. No live deployment, image publication, branch-protection changes, merge or Sprint2.

**Sprint1 NOT COMPLETE · CHK001 FAIL · CHK002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**

Four principal harnesses were rerun against committed PR84 HEAD8427cbc8c6387ab6e496a44c210db3c9eb3101e3 after all helper changes: access, ARCH001, operational and release each exit0. Exact commands/source IDs/elapsed times and raw logs in final-source-verification/. Repeats do not add distinct coverage. Final Docker process list is captured separately. Staging18-command and consolidated compatibility evidence remains on PR84.
