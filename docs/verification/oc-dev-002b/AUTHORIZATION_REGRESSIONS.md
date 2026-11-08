# Authorization and revocation

Actual authenticated API/PostgreSQL, no mocked transaction boundary:

- `final-application/api.json`14 groups includes protected ownership422, viewer403, disabled-parent409 on both PATCH APIs and legacy create, authenticated allowed writer and source-scoped persistence.
- Membership role change revokes original session; raw authenticated PATCH with stale token returns401, no name change. New scoped writer succeeds before revocation.
- Race: test-owned transaction holds existing advisory lock(782104,8), queues real admin revocation first, waits for a real PostgreSQL waiter, queues actual writer PATCH, waits for two waiters, releases lock. Revocation commits, waiting update401/403; original authorized description unchanged. No global auth lock or permission check disabled.
- `rbac/sprint08-http.json`14 retained groups: direct/inherited roles, department vs customer grants, environment/resource restrictions, exact action permission, stale revision, concurrent boundary edits, existing-session grant revocation and ALL delegation denial. `rbac/ownership.txt`42 executed cases include imported incident fixture tests; not42 unique RBAC requirements.
- `rbac/sprint08-browser.json`5 retained Chromium groups verify live revision clears sensitive drawer/cache, restricted selectors, delegated policy restrictions and department form.
- `preservation-final/deep_tenant_security_probe.log` and security_release_probe.log retain actual cross-customer API and session/audit/throttle negatives.

Generic transactional mutation/denial audit policy is retained. Existing release tests cover audit immutability/rollback; this task adds no audit policy or secrets in request logs. No permission catalog changes. Current tests do not independently certify every Resource UI A/B-switch interleaving, every resource type or external identity integration. Unexecuted cases remain explicit rather than synthetic PASS.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
