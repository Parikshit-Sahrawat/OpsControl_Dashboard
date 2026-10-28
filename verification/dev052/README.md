# DEV-05.2 release gates

Linux amd64 requires Python 3.12+ and Docker Engine for online extraction:

```sh
python verification/dev052/provision_contrib.py --output /tmp/dev052/otelcol-contrib
backend/.venv/bin/python verification/dev052/run_contrib_tests.py --binary /tmp/dev052/otelcol-contrib --report /tmp/dev052/contrib-tests.json
```

Offline/inside disposable CI containers: copy the approved artifact into a read-only
mount and use `--offline-artifact /approved/otelcol-contrib`. The same hard-coded
SHA-256 is mandatory. A missing or mismatched file fails before execution; never
replace the expected hash to accommodate an arbitrary download. Only Linux amd64
is pinned. The existing continuous-quality workflow now uses this verifier.
No existing test assertion or skip decorator was changed. The focused runner
requires exactly two tests and zero skips.

Version 0.123.0 comes from the repository's existing immutable upstream image
`otel/opentelemetry-collector-contrib:0.123.0@sha256:e39311df1f3d941923c00da79ac7ba6269124a870ee87e3c3ad24d60f8aee4d2`.
Docker validates image content; extraction yielded binary SHA-256
`6bca4ddd928b4b0880f7ec6c16511922f740c497b4efa4b33915b2d54a729213`.
The binary is not committed or redistributed. The upstream distribution is
Apache-2.0; retain upstream license/NOTICE and dependency notices if packaging it.
This provisioning step is not a complete transitive-license or vulnerability review.

Extraction containers use unique dev052 names and network none, and are removed
in finally. The verified binary cache may remain; it contains no test secrets.
Existing real runtime tests own their temporary files/processes/local HTTP servers.
No broad Docker cleanup is permitted. Do not run provider acceptance from these
instructions: use the separate approved-runtime certification runbook.
