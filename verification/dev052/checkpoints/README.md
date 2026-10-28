# DEV-05.2A.3B checkpoint-only lab

Experimental offline **legacy backup restore plus bounded archive replay**. There
is no direct protobuf/BoltDB converter, default-version change, promotion, new
dependency, CVE/pip/license/image/CI remediation or production deployment.
See [operator procedure](OPERATOR_RUNBOOK.md) for prerequisites and refusal cases.

Run focused unit tests from the repository root:

```bash
backend/.venv/bin/python -m unittest discover -s verification/dev052/checkpoints -p test_recovery.py -v
```

The native lab needs the existing backend Python environment, OpenSSL, local Docker
and the immutable fixture images already required by A.3. Provision and checksum
verify both runtimes with the unchanged legacy provisioner and separate A.3
candidate provisioner. Do not prune unrelated Docker resources to obtain space.

Prepare a **new private archive of the unchanged legacy control-plane source**:

```bash
backend/.venv/bin/python - <<'PY'
from pathlib import Path
import hashlib, json, subprocess, tarfile
stage = Path('/tmp/dev052a3b-review-source')
stage.mkdir(mode=0o700, exist_ok=False)
archive = stage / 'source.tar'
with archive.open('wb') as target:
    subprocess.run(['git','archive','HEAD','backend/app','backend/scripts',
                    'backend/tests','backend/migrations','backend/alembic.ini','agent'],
                   stdout=target, check=True)
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
with tarfile.open(archive) as tar:
    tar.extractall(stage, filter='data')
archive.unlink()
(stage/'overlay-provenance.json').write_text(json.dumps({
    'source_commit': subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
    'source_archive_sha256': digest, 'production_guard_modified': False,
    'scope': 'checkpoint-only direct-runtime experiment; no Agent transition'
}, indent=2)+'\n')
PY
```

Run with fresh output paths and the verified binaries:

```bash
backend/.venv/bin/python verification/dev052/checkpoints/run_lab.py \
  --stage /tmp/dev052a3b-review-source --output /tmp/dev052a3b-review-evidence \
  --binary /approved/experimental/otelcol-contrib \
  --guarded-binary /approved/legacy/otelcol-contrib

backend/.venv/bin/python verification/dev052/checkpoints/reconcile_evidence.py \
  --run /tmp/dev052a3b-review-evidence
```

The benchmark uses **direct pinned collector processes** to isolate storage
behavior. It does not bypass/modify an Agent constructor, change the advertised
Agent contract or claim a coordinated Agent/control-plane upgrade. The fixture API
stays at 0.123.0; the approved synthetic producer token/method scopes still pass
actual authentication and ingestion. The test-only ASGI wrapper preserves original
requests/responses and durably records successful API payload hashes and event IDs
in SQLite, reconciled independently against PostgreSQL events and receipts.

The shared A.3 fixture owner gained explicit opt-in hooks; its default behavior and
strict failure behavior remain unchanged. This benchmark deliberately continues
independent recovery checks after recording an interrupted-upgrade assertion
failure. The fixture process and overall lab **still exit 1/status FAIL**. A passing
finite recovery reconciliation never turns that failure into a global PASS.

Expected dated observation: interrupted default upgrade left 16 source IDs missing
after restart. Bounded recovery recovered all 44 IDs, with 100 stored source-event
rows and 56 duplicate rows. `event-accounting.json`, `api-receipts.json`,
`db-events.json`, `db-receipts.json` and phase reconciliation expose those counts.
Do not replace failing assertions or discard state to obtain a zero exit code.

Failure injection covers partial/empty staging, durable boundaries and actual
process death immediately after atomic exchange. Native tests additionally cover
clean upgrade, SIGKILL interruption, protobuf downgrade rejection on a clone,
active-state lock refusal, retained rotation/truncation, bounded replay and repeated
legacy/candidate restarts. The raw evidence tar contains only checked synthetic
checkpoint/log snapshots, not identities/TLS/passwords. Cleanup remains scoped to
owned containers, anonymous volumes, networks and private fixture secrets.

Recorded results cover only the finite synthetic fixture. **Security BLOCKED; release
NO-GO; transition/recovery execution approval still required.**
