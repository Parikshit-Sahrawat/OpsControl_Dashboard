# Sprint 1 Resource Management / approved UI implementation

**Disposition: PARTIAL — bounded implementation verified; full template closure BLOCKED; owner review Pending.** Do not start Sprint2 automatically. No merge, deployment or formal UAT.

Implemented a shared approved light workspace: navy collapsible rail/mobile drawer, blue tokens, contextual resource tabs, real scoped filters/chips/URL persistence, CtrlK resource search and exact detail selection, responsive resource counts/cards, timezone/density/theme preferences, role-aware controls and real template catalogue. Supplied image preserved with hashes and lossless JPEG-to-PNG provenance; [visual comparisons](VISUAL_COMPARISON.md) show actual authenticated application screenshots rather than invented dashboards.

Reviewed PR82 safeguards selectively reused: strict protected/unknown PATCH fields, disabled-parent collector checks, template package shape validation, immutable package pin preservation, scoped editor reset, persisted overrides and saved effective configuration. Save does not imply active/healthy telemetry. Resource create/edit/reload and configured collector flows execute against actual FastAPI/PostgreSQL. Incident UI navigation/render entry points removed under the approved scope; internal alert/correlation/notification/history regressions preserved. No schema migration, collector pin or permission catalog change.

## Commits and integration

- `95b4ab6d172e77c13b8b3e34be1568d2927dbed5`: shared workspace/resource/template implementation and focused security/API/browser fixtures; broad test source.
- `b9b6a95`: legacy browser regression aligned with approved incident UI exclusion; internal API record still asserted.
- `fcd385a76a30efb23eea667bba9b6d1fc9073b54`: bounded label wrapping/dark screenshots; expanded browser test source.
- `048d77f7d4259d54e69eb4b71945b8cb384de879`: additional CI job for real PostgreSQL/authenticated resource/security/workspace browsers. Existing required checks untouched.
- `ba80b49816d5ad216f699610ebb25f9203ea6ecf`: accessible long customer labels and normalized screenshot scrolling; final workspace tested application source.

See [exact baselines](BASELINES.json), [changed files](CHANGED_FILES.json), [source hashes](SOURCE_SHA256.json), [dependency review](PREFLIGHT_AND_DEPENDENCIES.md) and [traceability](DESIGN_AND_REQUIREMENT_TRACEABILITY.md). Parent PR83/Sprint0 is an explicit unmerged dependency; PR80/81/82 remain draft/unmodified. Main remains `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`. No intermediate main merge.

## Verification and acceptance limits

[Results](TEST_RESULTS.md): broad backend562 PASS/2 existing binary-dependent SKIP, frontend44 PASS, final12 focused tests PASS, expanded68 PASS (overlapping, not additive). Actual HTTP resource/template15 groups, resource browser security7, new workspace9, retained authorization14 HTTP/5 browser, Pentaho17 browser and additional4/5/4/5 synthetic HTTP groups; existing pipeline browser passes. Disposable release harness13 groups passes, including independent100-table/1197-row/499-constraint restore, TLS and fault negatives. Broad100-table/14522-row/schema/FK restore also matches. No genuine-provider or formal UAT acceptance inferred.

Fresh audits remain failing: Python10 advisory records in installed Black/pip/oauthlib toolchain, npm4 moderate entries. Full touched-existing-file Ruff has19 findings (baseline20), zero new signatures; focused configured checks pass. No installed image scanner/final release image clearance. Hosted CI follows **TRIGGER AND EXIT — RESULT PENDING**; no waiting/polling or green-CI inference. [Blockers](BLOCKERS.md) and failed attempts are retained.

COMP-S01-01 has bounded source/API/browser/preservation evidence; PR80 convergence remains unqualified. COMP-S01-02 is PARTIAL: committed package versions and saved configuration work, but exact enforceable applicability, immutable attachment/override history and older-writer compatibility require precise approved contracts/additive design. No artificial history or activation authority was invented to close the sprint.

## Owner review and next slice

Review the reference comparison and real resource flows; decide exact template applicability/history/fencing and authorize the combined migration plan separately. Then consider Sprint2 collector installation/configuration and exact binary provenance, with prerequisite gaps carried explicitly. Later charts/process/service/live freshness/report work remains in its approved sprint, not prematurely implemented here. All nine owner selections Pending; historical controlled-scope approvals unchanged, D07/D08 Pending. SOURCE_NOT_RECOVERED journey definitions remain unreconstructed.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.** PostgreSQL durable spool remains architecture until implemented/verified. No release promotion, genuine-provider access, shared UAT, production data or deployment.
