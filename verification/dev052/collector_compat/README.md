# DEV-05.2A.3 experimental collector contract

This directory **does not promote** Contrib 0.163.2. Production backend/Agent,
installers, packaging, CI pins and `verification/dev052/provision_contrib.py` keep
the 0.123.0 contract. No environment switch broadens production acceptance.

`experimental-0.163.2.patch` is applied only to a newly archived private source
tree. It selects exactly 0.163.2, rejects neighboring/prerelease/custom version
strings, and supplies `--feature-gates=-filelog.protobufCheckpointEncoding` at
backend validation and all supervisor validation/start paths. Without that flag,
the actual 0.123.0 rollback binary cannot decode newly written file checkpoints.
No TLS, authorization, egress, secret, receiver or exporter policy is changed.

The provisioner is separate and explicit. It pins Linux amd64 image, config digest
and binary SHA-256, verifies before executing, refuses mismatched existing files,
supports checked offline input, and removes only its extraction container. It is
evaluation authorization, not distribution or promotion approval.

Prerequisites: local managed Docker Engine, the existing backend Python 3.12
environment, OpenSSL, Git, and the exact local fixture images referenced by
`run_lab.py`. At least 900 MiB free is required; more than 1.5 GiB is recommended
with VFS. Do not prune unrelated images/caches to make room. The lab API runs from
the local Python environment and staged sources; the stdlib runner is a small,
immutable fixture image, not a release image. No production service is deployed.

Run from the repository root, using **new** stage/output paths:

```bash
python verification/dev052/provision_contrib.py --output /tmp/dev052a3-guarded/otelcol-contrib
python verification/dev052/collector_compat/provision.py --output /tmp/dev052a3-candidate/otelcol-contrib

# First run the unchanged baseline, before staging a new contract.
(cd backend && OPSCONTROL_OTEL_BINARY=/tmp/dev052a3-guarded/otelcol-contrib .venv/bin/python -m unittest tests.test_collection_v15 -v)

backend/.venv/bin/python verification/dev052/collector_compat/prepare.py \
  --stage /tmp/dev052a3-review-source --binary /tmp/dev052a3-candidate/otelcol-contrib

# Reuse unchanged assertions; only two fixture files' old-version literals follow
# the explicit staged contract. No test assertion/skip is removed.
(cd /tmp/dev052a3-review-source/backend && \
  OPSCONTROL_OTEL_BINARY=/tmp/dev052a3-candidate/otelcol-contrib \
  /workspace/OpsControl_Dashboard/backend/.venv/bin/python -m unittest \
  tests.test_collection_v15 tests.test_agent_v15 tests.test_agent_reenrollment \
  tests.test_managed_telemetry tests.test_access_control tests.test_api_worker_v2 -v)

backend/.venv/bin/python verification/dev052/collector_compat/run_lab.py \
  --stage /tmp/dev052a3-review-source --output /tmp/dev052a3-new-evidence \
  --binary /tmp/dev052a3-candidate/otelcol-contrib \
  --guarded-binary /tmp/dev052a3-guarded/otelcol-contrib
```

Adapt the absolute Python path to the checkout. For exact version rejection tests,
copy `test_contract.py` into the staged `backend/tests/test_dev052a3_contract.py`
and run that module there. `test_provisioning.py` runs from this directory using
unittest discovery. `scan.py` uses checksum-verified Syft/Grype paths and the frozen
DB cache recorded in dated evidence; provision those verified tools first, or mark
scanning BLOCKED. It saves one exact image at a time, verifies archive config and
binary SHA, scans that archive, and removes only its own temporary archive.

The E2E lab owns two internal networks, PostgreSQL, a bounded non-root/read-only
Agent container and an owned disjoint-network denied target. PostgreSQL is reached
through its owned bridge IP, without a public port. The TLS API binds only the lab
bridge gateway. The owner briefly stops/restarts that API to test queue recovery.
It preserves redacted logs before removing containers and their owned anonymous
volumes, networks, synthetic credentials, database and TLS material in finally.
SIGINT/SIGTERM also enter cleanup. Existing images, sources and baseline evidence
are not overwritten. Fixture credentials never belong to customers.

Results prove synthetic Linux process/collector/API behavior, not genuine
systemd/Windows/Pentaho certification or production capacity. The downgrade probe
proves configuration/storage startup compatibility, not an approved coordinated
control-plane/Agent downgrade. Owner review, platform/provider validation,
license/NOTICE fulfillment and final release identity gates remain mandatory.
