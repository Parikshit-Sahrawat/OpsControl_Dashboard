# Resource UI acceptance

`preservation-final/resource-crud.json`: actual authenticated Playwright and isolated PostgreSQL. One extended flow records7 checks: create/save; collector registration edit and same-ID reload; resource edit/refresh with deliberately delayed older inventory response; disable; re-enable; page reload and backend active-state reconciliation; duplicate409; foreign-account mutation denial; mobile390px and keyboard focus. Request bodies go to the actual backend. No whole-backend route mocking. Retained delayed inventory response is a stale-order test, not a substituted fixture response.

Screenshots: preservation-final/resource-registration.png,resource-mobile-keyboard.png. Separate retained scope-browser verifies excluded platform entry points absent. Retained pagination exercises205 resources, both themes and independent expected IDs.

Source changes in ResourceManagementV2: close config editors when customer filter or authorization revision changes; disable reassignment of existing ownership in legacy wizard; do not treat failed attachment GET as an empty set; preserve existing immutable template version during ordinary resource edit. Supported nullable fields remain clearable; required null PATCH fields get422.

Failed attempt: browser-failed/failed-command.log timed out finding Search resources after reload. Cause unconfirmed; no product navigation fix is claimed. Browser-retry passed and final clean-source preservation-final passed independently. No timeout/assertion was removed. All failed cleanup evidence retained.

Limits: mobile test exercises list viewport and focus, not complete keyboard-only form traversal. Exact delayed customer A/B-switch while an open config dialog saves remains NOT TESTED; actual authorization-revision cache/drawer handling is separately proven by retained Sprint08 browser. Full template-selection/version edit browser flow remains NOT TESTED. This is development evidence, not owner UAT.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
