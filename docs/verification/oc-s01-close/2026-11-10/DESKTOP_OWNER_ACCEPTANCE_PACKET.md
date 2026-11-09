# Desktop owner acceptance packet — preserve approved visual baseline

Accepted Resource Management source:54f26e51106469e285dd747dd6b8afd09ca43ce6 per Issue90. Latest application`ecfdff2cf3f9d1a7b7b284e79a7f708d1baea8ce`. This review inspected the accepted-source admin1440/operator1366 captures alongside latest captures at the same sizes. All six capture hashes and exact paths are in raw/r02/visual-comparison-provenance.json.

The baseline capture files are present in the accepted source snapshot but were originally captured earlier;do not mislabel them as newly executed tests at54f26e5. Current captures are the actual PR #101 PostgreSQL-backed execution. Different synthetic resource UUIDs/customer strings are fixture differences,not a product-layout defect. No pixel-equivalence,full accessibility certificate or new owner approval is inferred.

|Viewport|Latest administrator|Latest operator|
|---|---|---|
|1920×1080|[Admin](runtime/browser/admin-desktop-1920x1080.png)|[Operator](runtime/browser/operator-desktop-1920x1080.png)|
|1440×900|[Admin](runtime/browser/admin-desktop-1440x900.png)|[Operator](runtime/browser/operator-desktop-1440x900.png)|
|1366×768|[Admin](runtime/browser/admin-desktop-1366x768.png)|[Operator](runtime/browser/operator-desktop-1366x768.png)|

The navy single-panel three-level Feature Directory,light workspace,compact horizontal filters,table/action alignment and read-only operator layout remain visually consistent in inspected pairs. No stylesheet changed between54f26e5 andPR89. Source delta affects ResourceManagementV2.jsx,UnifiedResourceManagement.jsx andresourceApi.js;exact diff retained in raw/r02/accepted-baseline-ui-diff.patch.gz. Typography remains a separate pending decision;do not retroactively invalidate accepted layout.

|Case|Owner-observable expected result|Implementation/evidence|Change since accepted source|Owner decision|
|---|---|---|---|---|
|VA01 desktop admin/operator density|Readable inventory/filter/actions at all3 sizes;operator cannot mutate|Six captures;workspace-ui.json;targeted accessibility26controls|Layout styles retained|Prior visual acceptance preserved;latest review PENDING|
|VA02 catalogue stale conflict|409 preserves unsaved template;explicit review/adopt/retry|ResourceManagementV2.jsx TemplateEditor;workspace-ui.json;test_catalogue_concurrent_publication_and_stale_retirement|Added explicit catalogueCAS/adoption controls|PENDING functional acceptance|
|VA03 parent/child context save|Authorized context snapshot loaded before save;all revision heads coordinated;failure leaves edits|UnifiedResourceManagement.jsx;resource-security.json;test_coordinated_child_sources_are_atomic_and_revision_checked|Revision snapshot and related source/child updates|PENDING|
|VA04 keyboard form submission|Tab/focus/Enter honors native validation;single submission;persisted reload|UnifiedResourceManagement.jsx;resource_crud_acceptance.mjs;CI006 retained evidence|Native form/in-flight guard and stable control behavior|PENDING|
|VA05 history/detail/diff|Immutable revision detail,comparison,paging and actor/time displayed|[History capture](runtime/browser/configuration-history-diff-detach-draft.png);resource-security.json|Panel component unchanged since accepted source;function not individually owner-certified|PENDING functional acceptance;do not revoke prior visual approval|
|VA06 detach androllback|Reviewed detach appends;restore creates new audited revision;no secrets/checkpoints/activation restored|Same panel;test_attach_reload_history_rollback_and_detach|Same component;current backend contract exercised|PENDING|
|VA07 stale conflict/staging|Draft remains non-operational;explicit refresh retains unsaved work;discard clear|template-stale-edit-preserved.png;resource-security.json|Same panel;latest coupled writer contract|PENDING|
|VA08 scope/revocation/navigation|Tenant switch drops old context;delayed response denied;revocation closes editor;no retired IncidentsUI|resource-security.json;workspace-ui.json;ci-scope.json|Current trace/keyboard regressions retained|PENDING;backend enforcement is not waived|

These are development acceptance cases,not formal UAT. All nine separate owner selections remain Pending. Request only explicit disposition for the current source and these changed interactions;do not request AUTH-694 reapproval or new typography approval as an invented Sprint1 dependency.
