# OpsControl Typography System v1 — proposed, pending owner choice

Tracking: [Issue90](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/90). Design branch `design/typography-system-v1-issue90`, based on main `2e4fe5d8cb0f39170b0d789fdd7e07be4ac0219a`. Product audit baseline `54f26e51106469e285dd747dd6b8afd09ca43ce6`; running login observation at2ceef37 has unchanged typography CSS. **No product CSS, functionality, font dependency or release gate is changed.**

Issue90 records owner acceptance of PR89's Resource Management visual candidate. That decision is retained; this proposal does not retroactively reject it. Font family and exact scale remain **NOT APPROVED**. Independent review, security/CI, UAT and release decisions remain separate.

- [Audit and design decision memo](DESIGN_DECISION.md)
- [Proposed token stylesheet — never imported by product](TOKENS_PROPOSED.css)
- [Exact source declaration inventory](TYPOGRAPHY_AUDIT.json)
- [Actual running product font observation](ACTUAL_PRODUCT_FONT_OBSERVATION.json)
- [Font provenance, official source revision and checksums](FONT_PROVENANCE.json)
- [Migration, acceptance and rollback plan](MIGRATION_PLAN.md)
- [Browser cases and native zoom limitation](screenshots/RESULTS.json), [numeric/keyboard checks](screenshots/METRICS_AND_KEYBOARD.json), [contrast pairs](CONTRAST_RESULTS.json)

## Compare the same specimen

These are isolated design specimens with fictional, labelled sample values, **not implemented product before/after acceptance**. Current hard-coded roles are represented, not a pixel-identical copy of every page. No live health, activation, provider certification or operational controls are simulated.

| Candidate | Light1440×900 | Dark1440×900 |
|---|---|---|
|Current fallback / representative roles|[Before](screenshots/baseline-light-1440x900.png)|[Before dark](screenshots/baseline-dark-1440x900.png)|
|Inter|[Inter](screenshots/inter-light-1440x900.png)|[Inter dark](screenshots/inter-dark-1440x900.png)|
|IBM Plex Sans|[Plex](screenshots/plex-light-1440x900.png)|[Plex dark](screenshots/plex-dark-1440x900.png)|
|Source Sans3|[Source Sans3](screenshots/source-light-1440x900.png)|[Source Sans3 dark](screenshots/source-dark-1440x900.png)|

[Three-font comparison](screenshots/three-candidate-comparison.png). Full-content specimens include logs, forms and history: [fallback](screenshots/baseline-light-full-content.png), [Plex](screenshots/plex-light-full-content.png). [Actual current login](screenshots/actual-product-auth-before.png) is separately identified. Approved PR89 [Resource Management captures](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/54f26e51106469e285dd747dd6b8afd09ca43ce6/docs/verification/sprint1-integration/VISUAL_ACCEPTANCE.md) remain the product visual reference.

Desktop1920×1080,1440×900 and1366×768 are primary.32 Chromium cases cover four font modes, both themes, three desktops and100/125/150/200% **CSS zoom emulation** for Plex. Native browser zoom is **BLOCKED**, after two retained extension-service-worker failures; CSS zoom is not relabelled as native browser zoom.33 primary screenshots plus full-content/current-login captures are included. Targeted contrast8 pairs and tabular-number/keyboard cases pass; no full WCAG or multilingual certification is claimed.

## Reproduce without copying font binaries into the repository

Use the recorded Playwright1.56.1 / Chromium141.0.7390.37 tool paths or compatible explicitly reviewed tools. `serve_specimen.py --cache /tmp/oc-typography-assets --port-file /tmp/oc-type-server.json` downloads exact official-font files from the pinned Google Fonts source commit, verifies SHA256 and serves only an allowlist on an allocated loopback port. Set TYPE_SPECIMEN_URL to that URL, TYPE_OUT to an owned artifact directory, PLAYWRIGHT_MODULE and PLAYWRIGHT_CHROMIUM_EXECUTABLE, then run `capture_specimens.mjs` and `inspect_specimen.mjs`. Font files stay in the external cache; only OFL texts, provenance, screenshots and design/test code are committed. Stop the owned server after capture. No runtime external font-CDN request occurs in the specimen tests.

**Decision requested:** choose Inter / IBM Plex Sans / Source Sans3, approve or revise the semantic scale and loading/fallback strategy. Recommendation is Plex Sans + Plex Mono, subject to owner approval and native-zoom validation. Product-wide migration must be a separate authorized implementation.

CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO. No merge/deployment/UAT or Sprint2 authorization.

Original OFL licence texts retain upstream CRLF/trailing whitespace and exact hashes. Whole-tree whitespace warnings on those raw legal files are retained; they are not modified to satisfy formatting.
