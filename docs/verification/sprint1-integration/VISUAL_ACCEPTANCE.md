# Owner visual review — PENDING, not accepted

The actual [supplied reference](../../design/references/OpsControl_Approved_UI_Admin_Reference.png) and its original/provenance remain unchanged. Both the reference and current desktop capture were visually inspected. No pixel-equivalence or owner signoff is asserted. The earlier Sprint1 visual candidate was owner-REJECTED; no approval is inferred for this revised candidate.

| Viewport | Administrator | Operator |
|---|---|---|
|1920×1080|[Admin](runtime-evidence/pr89-consolidated-full/admin-desktop-1920x1080.png)|[Operator](runtime-evidence/pr89-consolidated-full/operator-desktop-1920x1080.png)|
|1440×900|[Admin](runtime-evidence/pr89-consolidated-full/admin-desktop-1440x900.png)|[Operator](runtime-evidence/pr89-consolidated-full/operator-desktop-1440x900.png)|
|1366×768|[Admin](runtime-evidence/pr89-consolidated-full/admin-desktop-1366x768.png)|[Operator](runtime-evidence/pr89-consolidated-full/operator-desktop-1366x768.png)|

The candidate uses a fixed navy sidebar and light desktop workspace, compact horizontal filters, expandable advanced filters and a persisted three-level in-panel Feature Directory. Multiple categories stay open. No flyout/secondary panel or invented route is added. Role differences hide unauthorized mutations in the same workspace; real server403 is verified. Keyboard navigation, active routes, tenant switching, search, saved filters, reload, targeted accessibility and both themes were exercised against actual FastAPI/PostgreSQL.

Differences from the reference requiring owner review:

- This is Resource Management, with real persisted inventory/configuration. The reference's live KPI charts, process/service panels, per-target rollouts and historical monitoring dashboard are not fabricated to make the screenshot match; later telemetry/UI work remains separate.
- Typography and table rows are larger than the dense reference; fixed sidebar224px and nested labels use more vertical space. Review density/readability at1366×768.
- Contextual resource tabs and advanced filters use existing supported backend dimensions. Unsupported saved views/monitoring summaries are not simulated.
- Readiness is CONFIGURED/UNVERIFIED where appropriate, never fake green health or successful rollout.
- Responsive/tablet/narrow screenshots are grace checks, not mobile-product acceptance. Desktop remains primary.

See runtime-evidence/pr89-consolidated-full/workspace-ui.json (14 groups), accessibility-checks.json and the reference provenance. The operational theme suite additionally passed13 checks with6 status text contrast measurements,0 page errors and0 server errors. This is targeted accessibility evidence, not comprehensive WCAG certification.

**Request:** owner review of these administrator/operator captures for visual acceptance, followed by independent PR review. This request does not authorize merging an incomplete or security-blocked candidate.
