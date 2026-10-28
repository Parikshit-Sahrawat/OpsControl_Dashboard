# DEV-05.2A.3D — saturated restart investigation

Experimental verification only. **CHK-001 FAIL; CHK-002 BLOCKED; SECURITY BLOCKED;
RELEASE NO-GO.** No production Agent hook, collector pin/guard change, queue-file
repair, custom binary, automatic replay, or CHK-002 recovery modification.

The inherited disposable lab uses checksum-pinned binaries, the actual TLS and
credential-authorized API, PostgreSQL, non-root processes, unchanged sandbox and
resource constraints, and named-resource cleanup. `run_lab.py` freezes its Python
fixture sources for each run. Product source comes from a separate `git archive`
stage whose `overlay-provenance.json` identifies the commit and selected cases.
The original C harness remains unchanged and first reproduces 267/257/10.

```
backend/.venv/bin/python verification/dev052/queue_restart/run_lab.py \
  --stage /tmp/owned-product-stage --output /path/to/new-evidence-directory \
  --binary /path/to/verified-0.163.2 --guarded-binary /path/to/verified-0.123.0
python -m unittest discover -s verification/dev052/queue_restart -p 'test_*.py' -v
```

`queue_cases` selects explicit names in the stage provenance. Default-size cases
fill the legacy 256-request queue and ten default consumers with individually
checkpointed IDs. The D timing overlay sets filelog polling to 20ms; the original
baseline uses unchanged generated timing. The owned source glob includes replay
files. No capacity increase is used. Direct experimental 0.163.2 starts do not
pass through or bypass a production version guard.

`state_view.py` is a read-only copy of C's committed bbolt observer, augmented with
legacy queue indices. Path-filtered strace delays queue pwrite calls; the collector
is SIGSTOPped before committed-page inspection and remains stopped at the chosen
SIGKILL cut. `queue-at-kill.bin`, syscall logs, metadata snapshots and independent
API/DB receipts preserve the actual boundary. ENOSPC injection targets queue
pwrite only; no shared disk is filled. Corruption affects only the owned stopped
queue, with an untouched hashed backup; no repair claim follows from the probe.

`api_fixture.py` inherits C's actual-app wrapper and writes an independent scoped
PostgreSQL snapshot on a private-file request while the writer is stopped. This
adds no product endpoint. Successful OTLP responses still require the original
application transaction. API response-send completion is not a client ACK.
`postcheck.py` independently queries final PG rows/receipts, checks payload receipt
hashes, reconciles every expected ID and reconstructs phase snapshots by row IDs
and creation times. Native failure remains FAIL after any successful replay.

## Bounded candidate and operator review boundary

`replay.py` is a separate offline **experimental source replay candidate**, not the
CHK-002 recovery utility and not a native queue fix. It supports only the exact
0.123.0 SHA and finite JSON-object lines with unique `event-NNNN` IDs. Bounds are
10,000 IDs, 16 MiB per sealed input, explicit inventory retention deadline,
complete source coverage, and one private, stopped-writer workspace on a local
filesystem. It neither reads nor rewrites collector state. Operator-trusted PG
snapshots must be independently exported from the same collector scope; hashes
provide integrity, not authenticity or human authorization.

Before any real use, an accountable operator/runtime owner must approve source
completeness, retention, quiescence, receipt scope/freshness, downstream duplicate
and ordering effects, filesystem semantics, and replay-marker compatibility.
**Approval is absent. Production integration and general recovery are BLOCKED.**

1. Stop the writer and ensure exclusive ownership; retain source/queue/config and
   exact binary hashes. Do not delete checkpoints or failed queue evidence.
2. Seal the independent producer ID inventory and full JSONL archive before the
   receipt cut. Refuse incomplete/expired archives or unknown source history.
3. Export scoped PostgreSQL rows independently after requests settle. Retain row
   IDs/timestamps, physical counts, API accepted attempts and missing IDs.
4. Review the proposed missing-only set. `prepare_replay` validates private files,
   SHA seals, version, scope, bounds, record completeness and deadline, then fsyncs
   a deterministic hidden pending file and atomically renames it into the already
   approved filelog glob. Original fields/IDs are retained, with a leading reserved
   `_opscontrol_replay_transaction` field to distinguish the file fingerprint.
   A source already containing that reserved field is refused.
5. Restart only the same authorized legacy runtime/config; do not introduce a
   version transition. Independently reconcile actual PG results again. Missing
   IDs remain FAIL; detection alone is not delivery. Repeat restarts and compare
   physical duplicates, not merely distinct counts.
6. If interrupted before publication, an intact pending file can resume. A partial
   pending file, destination tampering, missing source, corrupt queue or ambiguous
   state stops recovery. Preserve artifacts for owner review; there is no automatic
   discard, destructive reset, or repair. After publication, identical sealed
   inputs produce an idempotent no-op. A new/stale receipt cut is a new transaction
   and can replay duplicates. Exactly-once and global ordering are not promised.

No local test establishes power-loss, arbitrary storage-corruption, prolonged
outage, production throughput, genuine-provider, or release certification.
