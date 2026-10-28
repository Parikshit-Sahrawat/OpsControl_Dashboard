# DEV-05.2A.3C — CHK-001 causal delivery lab

**CHK-001 FAIL; CHK-002 BLOCKED; SECURITY BLOCKED; RELEASE NO-GO.**
The synchronous-handoff candidate closes two observed in-memory windows. It does
not repair the 0.123.0 full-queue crash-recovery deletion, permanent rejection, or
expired source retention. This is an isolated synthetic fixture, not an approved
runtime transition or a recovery utility. Do not use it on existing agent state.

## Reproduce

Use Linux amd64, a usable local Docker Engine, the existing backend virtualenv
and migration dependencies, host `strace` 6.13 and its listed glibc/unwind/lzma
libraries, and the two exact binaries pinned by the shared lab wrapper. The
wrapper requires at least 900 MiB free; allow substantially more for other Docker
storage drivers. No capabilities/seccomp exemptions are added for tracing.

Create a private stage with `git archive <source-commit>` containing
`backend/app`, `backend/scripts`, `backend/tests`, `backend/migrations`,
`backend/alembic.ini`, and `agent`. Write `overlay-provenance.json` at its root:

```json
{
  "source_commit": "<exact source SHA>",
  "source_archive_sha256": "<SHA-256 of the git archive>",
  "production_guard_modified": false,
  "durability_suite": "fixed",
  "durability_versions": ["0.123.0", "0.163.2"],
  "durability_cases": ["before_enqueue", "after_enqueue_before_checkpoint"]
}
```

Run from the repository root, supplying approved local binary paths:

```sh
backend/.venv/bin/python verification/dev052/durability/run_lab.py \
  --stage /tmp/dev052a3c-source \
  --output docs/verification/dev052/security/<new-unique-run> \
  --binary /approved/otelcol-contrib-0.163.2 \
  --guarded-binary /approved/otelcol-contrib-0.123.0
```

The wrapper rejects binary hash mismatches and existing output directories. It
owns its named internal networks, PostgreSQL volume, non-root read-only runner,
TLS API, synthetic credentials and cleanup. The API uses the actual staged app
and commits to disposable PostgreSQL. Candidate binaries run as direct producers;
the application's 0.123.0 registration/validation guard is never bypassed.

Use `durability_suite: baseline` with source
`76a97e3fcf6709533151fffb36b16138e4475aba` to reproduce the instrumented batch gap.
The exact original 44-ID reproduction uses the unchanged
`verification/dev052/checkpoints/run_lab.py` with that same stage. Do not modify
that utility or its assertions.

Omit `durability_cases` for the main 10-case suite. Additional cases:

- `before_enqueue`, `after_enqueue_before_checkpoint`: path-filtered strace
  pwrite delays, read-only committed-page snapshots while SIGSTOPped, then
  SIGKILL while still stopped. No checkpoint mutation or patched binary.
- `production_queue_saturation`: default 256-request queue, burst source append.
- `staggered_production_saturation`: default queue, independent append/checkpoint
  barriers; run separately on 0.123.0. This **fails** with missing IDs.

`queue_saturation` uses a documented two-request/one-consumer test overlay. The
staggered default test distinguishes missing checkpointed IDs from source replay
that can mask queue recovery deletion. Every run uses unique run-local event IDs,
an fsynced producer inventory, a separate synchronous SQLite API timeline and an
independent PostgreSQL query. Counts include accepted attempts, distinct IDs,
physical rows, duplicates and missing IDs. Negative delivery cases return a
nonzero result, even when the detector correctly finds the loss.

## Reading evidence

`e2e.json`: observed barriers, timestamps, snapshots and failures.
`api-timeline.json`: receipt/commit/send events (server send is not client ACK).
`db-events.json`, `db-receipts.json`: independently persisted rows and payload
hashes. `reconciliation.json`: per-case accounting, including failed attempts.
`runtime.log`, `controller.log`, syscall and metrics logs: raw instrumentation.
`synthetic-state.tar.gz`, `state-manifest.json`: bounded synthetic state and hashes.
`lab-result.json`: exact source, fixture image identities, constraints and cleanup.

Only read-only state inspection is provided here. The existing checkpoint
recovery procedure and CHK-002 remain separate and unchanged. Do not infer
exactly-once delivery, production alerting on missing IDs, power-loss durability,
long-outage retention sufficiency or genuine provider certification from these
finite synthetic probes.
