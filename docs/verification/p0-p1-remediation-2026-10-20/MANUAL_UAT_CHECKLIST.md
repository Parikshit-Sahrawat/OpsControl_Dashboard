# Independent UAT preparation

Automated fixtures and screenshots are development evidence. Owner/independent manual acceptance of this remediation remains PENDING. Use only a reviewed remediation commit; this is not deployment or source activation.

From the remediation checkout, after installing the existing locked dependencies:

```bash
export OPSCONTROL_UAT_EXPECTED_HEAD=$(git rev-parse HEAD)
export OPSCONTROL_UAT_STATE_DIR=/tmp/opscontrol-remediation-owner-uat
python scripts/uat/local_environment.py start
python scripts/uat/local_environment.py seed
python scripts/uat/local_environment.py status
python scripts/uat/local_environment.py logs
python scripts/uat/local_environment.py stop
# Explicitly removes only this random UAT-owned project/storage:
python scripts/uat/local_environment.py reset
```

`start` records repository root, exact commit and source fingerprint and refuses stale/unrelated state. Do not repoint an existing state directory across commits. Private generated credentials remain in the owner-only state directory; never paste them into reports. Existing Compose configuration is reused. Dependencies may be provided through `OPSCONTROL_UAT_PYTHON`/`OPSCONTROL_UAT_NODE_MODULES` as documented in the script. No real monitoring source is enabled.

- [ ] Record exact commit, generated browser/API URLs, migration head0037 and synthetic fixture IDs privately.
- [ ] Verify customer Organizations are distinct from provider Departments; admin/read-only/customer-A identities match expected direct/inherited scopes.
- [ ] Navigate Organizations, Collectors, Organisational Access and all six pipeline pages; refresh, Back/Forward and keyboard/mobile menu remain usable at390/768/1366px.
- [ ] Create a new synthetic customer and resource atomically as authorized platform administrator; parameter import succeeds under the new explicit ID, cancellation/failure leaves no orphan; ordinary employee cannot use this path to expand access.
- [ ] Verify resource/source/collector/report lists beyond the old caps; dependency history loads beyond50 with no omission/duplicate on a static dataset.
- [ ] Switch customer while requests/drawer are pending; previous customer's rows/actions clear. Foreign-ID direct requests remain denied.
- [ ] Inspect synthetic step metrics: distinct copies/repeated rows, actual0 versus missing Unknown, native status and errors visible. Synthetic values are clearly labeled; no child UUID claim.
- [ ] Replay approved sanitized native artifacts only through isolated tests; missing/contradictory evidence stays unknown/review-required without overwriting the prior defensible outcome.
- [ ] Confirm monitoring transport health differs from execution failure and coverage incompleteness; partial inventory never establishes NO_RUN.
- [ ] Record independent findings/screenshots and explicit remaining limitations. Do not accept RT001–020 or production readiness from this checklist.
