# Independent manual UAT — PENDING

Use the exact reviewed14R revision and existing [owned UAT harness](../../../scripts/uat/local_environment.py); do not reuse another project's storage. All seeded telemetry is synthetic, never live source monitoring. Generated credentials stay in private local state, not this report. Existing [full recovery checklist](../sprint14-baseline/ui-recovery/MANUAL_UAT_CHECKLIST.md) remains applicable.

- [ ] Reviewer records exact commit, browser/OS, viewport and independent outcome.
- [ ] At1366/768/720/390px in both themes, expand/collapse desktop then resize; mobile content has no72px offset or page overflow.
- [ ] Tab reveals skip link; Enter focuses main without changing deep-link hash. Link hides after focus leaves. Menu focuses first permitted item; Escape returns toggle. Test keyboard and assistive technology.
- [ ] Group/current-child labels, Back/Forward/refresh/deep links and six Data Pipeline pages remain correct.
- [ ] Customer Organizations differ from internal Departments; create actions remain singular, permission-controlled and in headers.
- [ ] Resource inventory loads actual seeded rows, supports search/page/filter and internal horizontal/vertical scrolling with readable sticky headers.
- [ ] Collector configuration keeps multiple independently added methods, enable/disable/remove controls and revision guards. Configured does not mean runtime-verified.
- [ ] Organisational Access preserves direct/inherited/restricted/explicitALL semantics. A-only viewer cannot see B data or mutation controls; direct unauthorized requests remain denied.
- [ ] Switch customer, role/session and scope while requests/drawers are pending; stale sensitive data/actions clear.
- [ ] Verify outcome, monitoring health and evidence completeness separately; incomplete/unknown cannot become success/NO_RUN. Original failure stays failed after separate manual recovery.
- [ ] Contrast, high-contrast/forced-color, zoom200%, reduced motion and focus stay usable; automated token ratios are not full accessibility certification.
- [ ] Record screenshots and any actual defect with source/reproduction; do not sign off genuine RT001–020 or production readiness.

Start/seed/status/stop/reset use `OPSCONTROL_UAT_EXPECTED_HEAD=<exact40-characterSHA>` and `OPSCONTROL_UAT_STATE_DIR=<new private /tmp path>` with `backend/.venv/bin/python scripts/uat/local_environment.py <action>`. The existing reset verifies owned project/repository before removing only that disposable project's storage; never run generic Docker prune or volume deletion. No permanent runtime environment is promised by committed screenshot artifacts.
