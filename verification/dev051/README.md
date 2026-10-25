# DEV-05.1 remediation verification

Run the exact DEV-05.0 assertions from PR #65 against a committed product fix:

```sh
python verification/dev051/run.py --product-commit <fix-sha> --output /tmp/dev051-unique
```

The output directory must not already exist. The adapter requires the original
baseline to be an ancestor of the selected commit, extracts the immutable harness
from commit `0e237026c7f1f293d2b0d0e8c94255ed4597c0dc` outside the checkout, and changes
only the original runner's **in-memory** product archive SHA. No original runner
file or assertion is edited. Its default remains pinned to `f617cc6`; no original
failed evidence is copied, replaced or modified. Product working-tree changes are
excluded because the runner tests a Git archive of the explicit commit.

The original runner owns its unique disposable Compose project, synthetic secrets,
redacted artifact export and label-scoped cleanup. The adapter verifies that the
original harness files remain byte-identical and records baseline/product/harness
SHAs plus file hashes in `remediation-provenance.json`. All original checks,
including the exact HEAD/10000/dev05-ui reload assertions, run without adjustment.
Nonzero exit status and FAIL outcomes remain failures; skips and unsupported real
provider certification remain distinct. No real customer endpoints, production
operations, original PR changes, broad cleanup or automatic merges are permitted.
