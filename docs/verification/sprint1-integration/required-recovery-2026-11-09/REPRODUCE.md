# Isolated reproduction

Run from the repository root with Docker Engine, Python backend/.venv, installed frontend dependencies and Playwright1.56.1/Chromium. Do not use shared/production/UAT databases. Preserve existing environment credentials; use only the harness-owned synthetic fixtures.

```sh
backend/.venv/bin/python -m unittest tests.test_ci_compose_build tests.test_ci_build_trust -v
ACCESS_EVIDENCE_DIR=/tmp/access-owned ACCESS_BROWSER_ACCEPTANCE=1 PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs PLAYWRIGHT_CHROMIUM_EXECUTABLE=/path/to/chromium backend/.venv/bin/python scripts/access-acceptance.py
RELEASE_EVIDENCE_DIR=/tmp/recovery-owned RELEASE_BROWSER_ACCEPTANCE=1 PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs PLAYWRIGHT_CHROMIUM_EXECUTABLE=/path/to/chromium backend/.venv/bin/python scripts/release-acceptance.py
S01_EVIDENCE_DIR=/tmp/config-owned backend/.venv/bin/python scripts/sprint1-configuration-acceptance.py
```

The exact executed small BuildKit proof source is `bake_probe.py`; its absolute `/tmp/oc-sprint1-integration` import root must point to your checkout when reproducing. It uses only a unique tiny image/project and owned Buildx state, and removes that image/private state in finally. Run from an owned directory; do not disable filesystem entitlements to work around its deliberate negative test. Logs/results live under /tmp/oc-s1-required-recovery/bake-probe-3. It does not certify full application images.

The full hosted Docker path is `ACCESS_DOCKER_EVIDENCE_DIR=/tmp/access-docker-owned backend/.venv/bin/python scripts/access-docker-demo.py`, with an optional validated `OPSCONTROL_BUILD_CA_FILE` pointing to a public PEM trust bundle. It generates its Compose plan and supplies only the exact-file entitlement. Adequate Docker backing-store capacity is a prerequisite; no broad cleanup or volume deletion is authorized.

All harnesses retain redacted failure output. Review failure-owned private files before removing only those task-specific directories. Never include keys, DB dumps, passwords or session files in evidence. Temp PG tests are not disk-failure durability qualification.
