# Resource browser acceptance

Review date: 2026-11-08 (Asia/Calcutta). Execution logs retain their original UTC timestamps. Tested source `80835f0065de24ebf271fc621b6d1e5e83d73bd2`; main `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`.


Final raw/final-retry/resource-security.json has7 real-browser/HTTP groups: create resource A; prohibited workload fields422; template V1 pin through V2 plus override save/reload/validation/stale save; authentic delayed A inventory during B selection; B-scoped A detail404; open-editor revocation/stale PUT401/no mutation; viewer no Edit/actual PATCH403. API responses were not fabricated. route.fetch obtains an authentic response; interception only holds delivery to create a race.

Canonical Compute editor includes the new template panel, scoped by exact source/customer and authorization revision. Explicit accessible names follow the existing Field contract. It does not poll over unsaved edits; scope/unmount generations reject stale reads. Server200/409 conflict handling preserves JSON text. Full page reload produces the same effective configuration. Mobile template screenshot checks no document overflow.

Broad release-final resource-crud.json retains create→save→edit→reload, disable/re-enable persisted active state, same collector ID/config name, cross-tenant denial, delayed older inventory and five repeated reloads. Keyboard-only Edit navigation→name replacement→Save→persisted reload passes; mouse/fill was used for initial creation. This is not full keyboard-only creation or all screen-reader certification.

Screenshots: raw/final-retry/template-stale-edit-preserved.png, template-mobile.png, resource-tenant-b.png, resource-revoked-editor.png, resource-security-desktop.png; raw/release-final/resource-registration.png and resource-mobile-keyboard.png. Sanitized request/status/timestamp traces are in the JSON exports. No full trace archive containing session headers is published. Earlier failed screenshots/logs are retained separately.

Outstanding: exact global A/B switching while the template modal save is in flight at every boundary, every supported collection method, full keyboard-only initial onboarding and independent owner UAT remain unverified. Existing five Sprint08 browser groups are additional bounded evidence, not substitutes.


**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
